import json
import math
import os
import re
import secrets
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
PRIMARY_DB_PATH = BASE_DIR / "focusport.db"
LEGACY_DB_PATH = BASE_DIR / "focuscrossing.db"
STATIC_DIR = BASE_DIR / "static"
FRONTEND_DIST = BASE_DIR / "focusport-frontend" / "dist"
FRONTEND_PUBLIC = BASE_DIR / "focusport-frontend" / "public"
CITY_ASSET_ROOT = Path(r"C:\Users\86153\Downloads\asset")
CITY_LAYOUT_PATH = STATIC_DIR / "city_layout_slots.json"
ISOMETRIC_ASSET_ROOT = FRONTEND_PUBLIC / "assets" / "2d"
ISOMETRIC_MANIFEST_PATH = ISOMETRIC_ASSET_ROOT / "manifest.json"
DEFAULT_AVATAR = "👨‍🚀"

DEFAULT_QWEN_MODEL = "qwen-plus"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
BLANK_LOG_FEEDBACK = "警告：未检测到有效算力日志，判定为系统休眠，收益减半。"
FALLBACK_EVALUATION_FEEDBACK = "量子评估通道波动，本次按基础收益结算。"
STUDY_LOG_SYSTEM_PROMPT = (
    "你现在是极点星港的 AI 副官，兼具清华毒舌学长的人设。"
    "你需要根据指挥官（用户）提交的【学习日志】、【任务难度】和【专注时长】进行质量评估。"
    "你必须且只能输出合法的 JSON 格式，绝不能包含任何 Markdown 标记或多余的文字。"
)
TASK_DIFFICULTY_MULTIPLIERS = {"L1": 1.0, "L2": 1.5}
LOCAL_ENV_PATHS = (BASE_DIR / ".env.local", FRONTEND_DIST.parent / ".env.local")


def resolve_db_path() -> Path:
    if PRIMARY_DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return PRIMARY_DB_PATH
    return LEGACY_DB_PATH


DB_PATH = resolve_db_path()


app = FastAPI(title="FocusPort", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def safe_json_loads(raw: Optional[str], fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


@lru_cache(maxsize=1)
def load_local_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in LOCAL_ENV_PATHS:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = raw_value.strip().strip("'").strip('"')
            if value:
                values[key] = value
    return values


def get_env_value(*keys: str) -> str:
    local_env = load_local_env_values()
    for key in keys:
        value = os.environ.get(key) or local_env.get(key)
        if value:
            return value
    return ""


def normalize_task_difficulty(value: Optional[str]) -> str:
    return "L2" if str(value or "L1").strip().upper() == "L2" else "L1"


def task_difficulty_multiplier(value: Optional[str]) -> float:
    return TASK_DIFFICULTY_MULTIPLIERS.get(normalize_task_difficulty(value), 1.0)


def clamp_quality_multiplier(value: Any, fallback: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(0.5, min(1.5, numeric))


def strip_markdown_code_fence(raw_text: str) -> str:
    cleaned = str(raw_text or "").strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_json_object_text(raw_text: str) -> str:
    normalized = strip_markdown_code_fence(raw_text)
    if not normalized:
        return ""
    match = re.search(r"\{[\s\S]*\}", normalized)
    return match.group(0) if match else normalized


def parse_qwen_evaluation_content(
    raw_text: str,
    fallback_multiplier: float = 1.0,
    fallback_feedback: str = FALLBACK_EVALUATION_FEEDBACK,
) -> dict[str, Any]:
    candidate = extract_json_object_text(raw_text)
    try:
        parsed = json.loads(candidate)
        return {
            "quality_multiplier": clamp_quality_multiplier(parsed.get("qualityMultiplier"), fallback_multiplier),
            "feedback": str(parsed.get("feedback") or fallback_feedback).strip() or fallback_feedback,
            "raw_content": raw_text,
            "parse_error": "",
        }
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return {
            "quality_multiplier": clamp_quality_multiplier(fallback_multiplier, 1.0),
            "feedback": fallback_feedback,
            "raw_content": raw_text,
            "parse_error": str(error),
        }


def evaluate_study_log(
    session_log: str,
    task_difficulty: str,
    duration_minutes: int,
    subject: str,
    model: str = DEFAULT_QWEN_MODEL,
) -> dict[str, Any]:
    normalized_log = str(session_log or "").strip()
    normalized_difficulty = normalize_task_difficulty(task_difficulty)
    normalized_model = str(model or DEFAULT_QWEN_MODEL).strip() or DEFAULT_QWEN_MODEL

    if not normalized_log:
        return {
            "success": True,
            "quality_multiplier": 0.5,
            "feedback": BLANK_LOG_FEEDBACK,
            "evaluation_source": "blank_shortcut",
            "model": normalized_model,
            "raw_content": "",
        }

    api_key = get_env_value("QWEN_API_KEY", "DASHSCOPE_API_KEY", "VITE_QWEN_API_KEY")
    if not api_key:
        return {
            "success": False,
            "quality_multiplier": 1.0,
            "feedback": FALLBACK_EVALUATION_FEEDBACK,
            "evaluation_source": "fallback",
            "model": normalized_model,
            "raw_content": "",
            "error": "missing_qwen_api_key",
        }

    prompt_payload = "\n".join([
        f"学习日志：{normalized_log}",
        f"任务难度：{normalized_difficulty}",
        f"专注时长：{max(int(duration_minutes or 0), 0)} 分钟",
        f"任务主题：{subject or '专注任务'}",
        '请严格输出 JSON：{"qualityMultiplier": 1.0, "feedback": "..."}',
    ])

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)
        response = client.chat.completions.create(
            model=normalized_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": STUDY_LOG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_payload},
            ],
        )
        raw_content = response.choices[0].message.content or ""
        parsed = parse_qwen_evaluation_content(raw_content)
        return {
            "success": True,
            "quality_multiplier": parsed["quality_multiplier"],
            "feedback": parsed["feedback"],
            "evaluation_source": "fallback" if parsed["parse_error"] else "qwen",
            "model": normalized_model,
            "raw_content": raw_content,
            "parse_error": parsed["parse_error"],
        }
    except Exception as error:
        return {
            "success": False,
            "quality_multiplier": 1.0,
            "feedback": FALLBACK_EVALUATION_FEEDBACK,
            "evaluation_source": "fallback",
            "model": normalized_model,
            "raw_content": "",
            "error": str(error),
        }


def slug_title(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def rarity_for_grade(grade: str) -> str:
    mapping = {"C": "common", "B": "rare", "A": "epic", "S": "legendary"}
    return mapping.get((grade or "C").upper(), "common")


def normalize_grade(rarity: Optional[str]) -> str:
    mapping = {"common": "C", "rare": "B", "epic": "A", "legendary": "S"}
    if not rarity:
        return "C"
    return mapping.get(str(rarity).lower(), "C")


def placement_type_for_category(category: Optional[str]) -> str:
    if category == "structures":
        return "building"
    if category in {"plants", "trees"}:
        return "greenery"
    if category in {"vehicle", "vehicles"}:
        return "building"
    if category in {"paths", "roads", "platform", "ground"}:
        return "fixed_scene"
    return "unsupported"


def normalize_dimension(value: Optional[str]) -> str:
    return "2D" if str(value or "3D").strip().upper() == "2D" else "3D"


def city_layout() -> dict[str, Any]:
    if not CITY_LAYOUT_PATH.exists():
        return {"map_id": "city", "surface_y": 1.7, "slots": []}
    return safe_json_loads(CITY_LAYOUT_PATH.read_text(encoding="utf-8"), {"map_id": "city", "surface_y": 1.7, "slots": []})


def city_slots() -> list[dict[str, Any]]:
    return city_layout().get("slots", [])


def city_slot_index() -> dict[str, dict[str, Any]]:
    return {slot["slot_id"]: slot for slot in city_slots() if slot.get("slot_id")}


def city_slot_capacities(conn: sqlite3.Connection, username: str, map_id: str = "city") -> dict[str, int]:
    total_by_type = defaultdict(int)
    for slot in city_slots():
        if slot.get("enabled", True):
            total_by_type[slot.get("slot_type", "")] += 1

    used_by_type = defaultdict(int)
    rows = conn.execute(
        """
        SELECT usi.category
        FROM Island_Infrastructure ii
        JOIN Unified_Shop_Items usi ON usi.id = ii.item_id
        WHERE ii.username = ? AND ii.map_id = ? AND COALESCE(ii.dimension, '3D') = '3D'
        """,
        (username, map_id),
    ).fetchall()
    for row in rows:
        used_by_type[placement_type_for_category(row["category"])] += 1

    return {key: max(total_by_type[key] - used_by_type[key], 0) for key in total_by_type}


def preview_path_for_model(model_path: Optional[str]) -> str:
    if not model_path or not model_path.startswith("/city-assets/"):
        return ""
    parts = model_path.split("/")
    if len(parts) < 4:
        return ""
    pack = parts[2]
    return f"/city-assets/{pack}/Previews/{Path(parts[-1]).stem}.png"


def load_isometric_manifest() -> dict[str, Any]:
    if not ISOMETRIC_MANIFEST_PATH.exists():
        return {"grid": {"cols": 12, "rows": 12, "tile_width": 96, "tile_height": 48}, "items": []}
    return safe_json_loads(
        ISOMETRIC_MANIFEST_PATH.read_text(encoding="utf-8"),
        {"grid": {"cols": 12, "rows": 12, "tile_width": 96, "tile_height": 48}, "items": []},
    )


def item_preview_path(item: dict[str, Any]) -> str:
    explicit_preview = item.get("preview_path")
    if explicit_preview:
        return explicit_preview
    return preview_path_for_model(item.get("model_path"))


def sync_isometric_items(conn: sqlite3.Connection) -> None:
    manifest = load_isometric_manifest()
    items = manifest.get("items", [])
    for index, raw_item in enumerate(items):
        item = dict(raw_item)
        item_code = str(item.get("item_code") or "").strip()
        if not item_code:
            continue

        dimension = normalize_dimension(item.get("dimension"))
        category = item.get("category") or "structures"
        name = item.get("name") or slug_title(item_code)
        name_cn = item.get("name_cn") or name
        description = item.get("description") or f"{name_cn} 2D 等距部署单元。"
        preview_path = item.get("preview_path") or item.get("sprite_path") or ""
        sprite_path = item.get("sprite_path") or preview_path
        payload = (
            name,
            name_cn,
            category,
            item.get("subcategory") or "isometric",
            item.get("tags") or "2d,isometric,kenney",
            item.get("model_path") or "",
            item.get("icon") or ("🚗" if item.get("subcategory") == "vehicles" else "🏙️"),
            int(item.get("price_sunshine") or 0),
            item.get("rarity") or "common",
            description,
            int(item.get("is_available", 1)),
            int(item.get("sort_order", index)),
            int(item.get("price_coins") or 0),
            dimension,
            preview_path,
            sprite_path,
            max(1, int(item.get("grid_width") or 1)),
            max(1, int(item.get("grid_height") or 1)),
        )

        existing = conn.execute("SELECT id FROM Unified_Shop_Items WHERE item_code = ?", (item_code,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE Unified_Shop_Items
                SET name = ?, name_cn = ?, category = ?, subcategory = ?, tags = ?, model_path = ?, icon = ?,
                    price_sunshine = ?, rarity = ?, description = ?, is_available = ?, sort_order = ?,
                    price_coins = ?, dimension = ?, preview_path = ?, sprite_path = ?, grid_width = ?, grid_height = ?
                WHERE id = ?
                """,
                (*payload, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO Unified_Shop_Items
                (item_code, name, name_cn, category, subcategory, tags, model_path, icon,
                 price_sunshine, rarity, description, is_available, sort_order, price_coins,
                 dimension, preview_path, sprite_path, grid_width, grid_height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_code, *payload),
            )


def sync_runtime_shop_catalog(conn: sqlite3.Connection) -> None:
    sync_isometric_items(conn)
    conn.commit()


def rectangles_overlap(ax: int, ay: int, aw: int, ah: int, bx: int, by: int, bw: int, bh: int) -> bool:
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def find_2d_placement_conflict(
    conn: sqlite3.Connection,
    username: str,
    map_id: str,
    grid_x: int,
    grid_y: int,
    grid_width: int,
    grid_height: int,
) -> Optional[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT ii.id, ii.grid_x, ii.grid_y, usi.grid_width, usi.grid_height, usi.name, usi.name_cn
        FROM Island_Infrastructure ii
        JOIN Unified_Shop_Items usi ON usi.id = ii.item_id
        WHERE ii.username = ? AND ii.map_id = ? AND COALESCE(ii.dimension, '3D') = '2D'
        """,
        (username, map_id),
    ).fetchall()
    for row in rows:
        placed_x = int(row["grid_x"] or 0)
        placed_y = int(row["grid_y"] or 0)
        placed_w = max(1, int(row["grid_width"] or 1))
        placed_h = max(1, int(row["grid_height"] or 1))
        if rectangles_overlap(grid_x, grid_y, grid_width, grid_height, placed_x, placed_y, placed_w, placed_h):
            return row
    return None


def clean_shop_label(pack_key: str, basename: str, category: str) -> tuple[str, str, str]:
    pack_cn = {"commercial": "商业", "industrial": "工业", "suburban": "郊区", "roads": "道路"}
    pack_name = pack_cn.get(pack_key, pack_key.title())
    if basename == "planter":
        return "Planter", "科幻花坛", "适合城市核心绿化位的花坛单元。"
    if basename == "tree-large":
        return "Large Tree", "大型行道树", "适合城市外围绿化位的高大行道树。"
    if basename == "tree-small":
        return "Small Tree", "小型行道树", "适合城市核心绿化位的小型行道树。"
    if basename.startswith("building-skyscraper-"):
        suffix = basename.split("-")[-1].upper()
        return f"Skyscraper {suffix}", f"{pack_name}塔楼 {suffix}", f"{pack_name}区域的高层建筑单元。"
    if basename.startswith("low-detail-building-wide-"):
        suffix = basename.split("-")[-1].upper()
        return f"Wide Block {suffix}", f"{pack_name}宽体楼群 {suffix}", f"{pack_name}区域的宽体建筑单元。"
    if basename.startswith("low-detail-building-"):
        suffix = basename.split("-")[-1].upper()
        return f"Low Detail Building {suffix}", f"{pack_name}建筑 {suffix}", f"{pack_name}区域的轻量建筑单元。"
    if basename.startswith("building-type-"):
        suffix = basename.split("-")[-1].upper()
        return f"Suburban Block {suffix}", f"{pack_name}住宅 {suffix}", f"{pack_name}区域的住宅建筑单元。"
    if basename.startswith("building-"):
        suffix = basename.split("-")[-1].upper()
        return f"Building {suffix}", f"{pack_name}建筑 {suffix}", f"{pack_name}区域的建筑单元。"
    if category in {"plants", "trees"}:
        return slug_title(basename), f"{pack_name}绿化 {slug_title(basename)}", f"{pack_name}区域的绿化装饰单元。"
    return slug_title(basename), f"{pack_name}{slug_title(basename)}", f"{pack_name}区域的城市单元。"


def city_item_meta(pack_key: str, basename: str) -> Optional[dict[str, Any]]:
    if pack_key == "commercial":
        if basename.startswith("building-skyscraper-"):
            return {"category": "structures", "grade": "S", "price_coins": 0, "price_sunshine": 10}
        if basename.startswith("low-detail-building-wide-"):
            return {"category": "structures", "grade": "B", "price_coins": 280, "price_sunshine": 0}
        if basename.startswith("low-detail-building-"):
            return {"category": "structures", "grade": "C", "price_coins": 220, "price_sunshine": 0}
        if basename.startswith("building-"):
            return {"category": "structures", "grade": "C", "price_coins": 500, "price_sunshine": 0}
        return None
    if pack_key == "industrial":
        if basename.startswith("building-"):
            return {"category": "structures", "grade": "B", "price_coins": 360, "price_sunshine": 0}
        return None
    if pack_key == "suburban":
        if basename.startswith("building-type-"):
            return {"category": "structures", "grade": "A", "price_coins": 0, "price_sunshine": 6}
        if basename == "planter":
            return {"category": "plants", "grade": "B", "price_coins": 0, "price_sunshine": 4}
        if basename in {"tree-large", "tree-small"}:
            return {"category": "trees", "grade": "A", "price_coins": 0, "price_sunshine": 5}
        return None
    if pack_key == "roads":
        if basename.startswith("road-") or basename.startswith("intersection") or basename.startswith("crosswalk"):
            return {"category": "paths", "grade": "C", "price_coins": 0, "price_sunshine": 0, "is_available": 0}
        return None
    return None


def sync_kenney_city_items(conn: sqlite3.Connection) -> None:
    if not CITY_ASSET_ROOT.exists():
        return

    pack_map = {
        "commercial": "kenney_city-kit-commercial_2.1",
        "industrial": "kenney_city-kit-industrial_1.0",
        "suburban": "kenney_city-kit-suburban_20",
        "roads": "kenney_city-kit-roads",
    }

    for pack_key, folder_name in pack_map.items():
        obj_dir = CITY_ASSET_ROOT / folder_name / "Models" / "OBJ format"
        if not obj_dir.exists():
            continue

        for obj_path in sorted(obj_dir.glob("*.obj")):
            basename = obj_path.stem
            meta = city_item_meta(pack_key, basename)
            if not meta:
                continue

            item_code = f"city_{pack_key}_{basename.replace('-', '_')}"
            name, name_cn, description = clean_shop_label(pack_key, basename, meta["category"])
            model_path = f"/city-assets/{folder_name}/Models/OBJ format/{obj_path.name}"
            rarity = rarity_for_grade(meta["grade"])
            icon = "🏙️" if meta["category"] == "structures" else "🌳"
            existing = conn.execute("SELECT id FROM Unified_Shop_Items WHERE item_code = ?", (item_code,)).fetchone()
            payload = (
                name,
                name_cn,
                meta["category"],
                pack_key,
                f"city,{pack_key},{meta['category']}",
                model_path,
                icon,
                meta["price_sunshine"],
                rarity,
                description,
                meta.get("is_available", 1),
                meta["price_coins"],
                "3D",
                preview_path_for_model(model_path),
                "",
                1,
                1,
            )
            if existing:
                conn.execute(
                    """
                    UPDATE Unified_Shop_Items
                    SET name = ?, name_cn = ?, category = ?, subcategory = ?, tags = ?,
                        model_path = ?, icon = ?, price_sunshine = ?, rarity = ?, description = ?,
                        is_available = ?, price_coins = ?, dimension = ?, preview_path = ?, sprite_path = ?,
                        grid_width = ?, grid_height = ?
                    WHERE id = ?
                    """,
                    (*payload, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO Unified_Shop_Items
                    (item_code, name, name_cn, category, subcategory, tags, model_path, icon,
                     price_sunshine, rarity, description, is_available, sort_order, price_coins,
                     dimension, preview_path, sprite_path, grid_width, grid_height)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_code, *payload),
                )


def seed_achievements(conn: sqlite3.Connection) -> None:
    achievements = [
        ("first_focus", "初次升空", "完成第一次专注计时。", "focus", "🚀", 20),
        ("focus_300", "专注三百", "累计专注达到 300 分钟。", "focus", "⏱️", 40),
        ("focus_1000", "千分钟航线", "累计专注达到 1000 分钟。", "focus", "🌌", 80),
        ("streak_3", "连续出勤", "连续 3 天保持学习记录。", "streak", "🔥", 25),
        ("streak_7", "稳态飞行", "连续 7 天保持学习记录。", "streak", "🛰️", 50),
        ("builder_1", "首栋落成", "成功放置第一栋城市建筑。", "special", "🏗️", 30),
    ]
    cols = table_columns(conn, "Achievements")
    for code, name, description, category, icon, exp_reward in achievements:
        key_col = "code" if "code" in cols else "achievement_code"
        existing = conn.execute(f"SELECT id FROM Achievements WHERE {key_col} = ?", (code,)).fetchone()
        if existing:
            assignments = ["name = ?", "description = ?", "category = ?", "icon = ?", "exp_reward = ?"]
            values: list[Any] = [name, description, category, icon, exp_reward]
            if "code" in cols:
                assignments.append("code = ?")
                values.append(code)
            if "achievement_code" in cols:
                assignments.append("achievement_code = ?")
                values.append(code)
            if "requirement_type" in cols:
                assignments.append("requirement_type = ?")
                values.append("manual")
            if "requirement_value" in cols:
                assignments.append("requirement_value = ?")
                values.append(0)
            values.append(existing["id"])
            conn.execute(f"UPDATE Achievements SET {', '.join(assignments)} WHERE id = ?", tuple(values))
        else:
            insert_cols = []
            insert_vals: list[Any] = []
            if "achievement_code" in cols:
                insert_cols.append("achievement_code")
                insert_vals.append(code)
            if "code" in cols:
                insert_cols.append("code")
                insert_vals.append(code)
            insert_cols.extend(["name", "description", "icon", "category", "exp_reward"])
            insert_vals.extend([name, description, icon, category, exp_reward])
            if "requirement_type" in cols:
                insert_cols.append("requirement_type")
                insert_vals.append("manual")
            if "requirement_value" in cols:
                insert_cols.append("requirement_value")
                insert_vals.append(0)
            placeholders = ", ".join("?" for _ in insert_cols)
            conn.execute(f"INSERT INTO Achievements ({', '.join(insert_cols)}) VALUES ({placeholders})", tuple(insert_vals))


def seed_exams(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM Exams").fetchone()["count"]
    if existing > 0:
        return

    exams = [
        {
            "exam_code": "ENG-MOCK-01",
            "title": "语言考核站 01",
            "time_limit": 45,
            "config_json": {
                "sections": [
                    {
                        "name": "词汇选择",
                        "instruction": "选择最合适的答案完成句子。",
                        "questions": [
                            {"id": "q1", "type": "choice", "question": "She usually ___ to school by bus.", "options": {"A": "go", "B": "goes", "C": "going", "D": "gone"}},
                            {"id": "q2", "type": "choice", "question": "We have lived here ___ five years.", "options": {"A": "for", "B": "since", "C": "from", "D": "in"}},
                            {"id": "q3", "type": "choice", "question": "If it rains tomorrow, we ___ at home.", "options": {"A": "stay", "B": "stayed", "C": "will stay", "D": "stays"}},
                        ],
                    },
                    {
                        "name": "填空练习",
                        "instruction": "根据句意填入合适单词。",
                        "questions": [
                            {"id": "q4", "type": "fill", "question": "Learning takes time and ____ ."},
                            {"id": "q5", "type": "fill", "question": "Please turn off your phone and stay ____ during study time."},
                        ],
                    },
                ]
            },
            "answer_key_json": {"q1": "B", "q2": "A", "q3": "C", "q4": "practice", "q5": "focused"},
        },
        {
            "exam_code": "ENG-MOCK-02",
            "title": "语言考核站 02",
            "time_limit": 35,
            "config_json": {
                "sections": [
                    {
                        "name": "基础阅读",
                        "instruction": "选择最合适的答案。",
                        "questions": [
                            {"id": "q1", "type": "choice", "question": "Tom is taller than ___ in his class.", "options": {"A": "any student", "B": "any other student", "C": "other student", "D": "the student"}},
                            {"id": "q2", "type": "choice", "question": "My homework ___ before dinner yesterday.", "options": {"A": "finished", "B": "was finished", "C": "is finished", "D": "finishes"}},
                            {"id": "q3", "type": "fill", "question": "The best way to improve English is to keep ____ every day."},
                        ],
                    }
                ]
            },
            "answer_key_json": {"q1": "B", "q2": "B", "q3": "practicing"},
        },
    ]

    for exam in exams:
        conn.execute(
            """
            INSERT INTO Exams (exam_code, title, config_json, answer_key_json, ai_prompt, audio_file, pdf_file, time_limit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam["exam_code"],
                exam["title"],
                json.dumps(exam["config_json"], ensure_ascii=False),
                json.dumps(exam["answer_key_json"], ensure_ascii=False),
                "给出简洁、鼓励式反馈，并指出最关键的改进方向。",
                "",
                "",
                exam["time_limit"],
            ),
        )


def ensure_user(conn: sqlite3.Connection, username: str, password: str = "123456") -> None:
    if not conn.execute("SELECT username FROM Users WHERE username = ?", (username,)).fetchone():
        conn.execute("INSERT INTO Users (username, password, avatar) VALUES (?, ?, ?)", (username, password, DEFAULT_AVATAR))
    if not conn.execute("SELECT username FROM User_Growth WHERE username = ?", (username,)).fetchone():
        conn.execute(
            """
            INSERT INTO User_Growth
            (username, focus_energy, total_focus_minutes, streak_days, last_active_date, sunshine, coins, diamonds, exp, level, discipline_score, max_streak, total_trees, achievements_count)
            VALUES (?, 60, 0, 0, ?, 120, 1200, 120, 0, 1, 50, 0, 0, 0)
            """,
            (username, str(date.today())),
        )


def build_growth_payload(conn: sqlite3.Connection, username: str) -> dict[str, Any]:
    ensure_user(conn, username)
    row = conn.execute("SELECT * FROM User_Growth WHERE username = ?", (username,)).fetchone()
    exp = int(row["exp"] or 0)
    level = max(int(row["level"] or 1), exp // 100 + 1)
    return {
        "username": username,
        "exp": exp,
        "level": level,
        "discipline_score": round(float(row["discipline_score"] or 50), 1),
        "streak_days": int(row["streak_days"] or 0),
        "max_streak": int(row["max_streak"] or 0),
        "focus_energy": int(row["focus_energy"] or 0),
        "total_focus_minutes": int(row["total_focus_minutes"] or 0),
        "sunshine": int(row["sunshine"] or 0),
        "coins": int(row["coins"] or 0),
        "diamonds": int(row["diamonds"] or 0),
        "achievements_count": int(row["achievements_count"] or 0),
        "total_trees": int(row["total_trees"] or 0),
    }


def sync_growth_level(conn: sqlite3.Connection, username: str) -> None:
    row = conn.execute("SELECT exp FROM User_Growth WHERE username = ?", (username,)).fetchone()
    if row:
        conn.execute("UPDATE User_Growth SET level = ? WHERE username = ?", (max(1, int(row["exp"] or 0) // 100 + 1), username))


def mark_user_active(conn: sqlite3.Connection, username: str) -> None:
    ensure_user(conn, username)
    row = conn.execute("SELECT streak_days, max_streak, last_active_date FROM User_Growth WHERE username = ?", (username,)).fetchone()
    today = date.today()
    last_raw = row["last_active_date"] if row else None
    streak_days = int(row["streak_days"] or 0) if row else 0
    max_streak = int(row["max_streak"] or 0) if row else 0
    if last_raw == str(today):
        return
    if last_raw:
        try:
            last_date = date.fromisoformat(last_raw)
        except ValueError:
            last_date = today
    else:
        last_date = today
    if last_raw and last_date == today - timedelta(days=1):
        streak_days += 1
    else:
        streak_days = 1
    max_streak = max(max_streak, streak_days)
    conn.execute("UPDATE User_Growth SET streak_days = ?, max_streak = ?, last_active_date = ? WHERE username = ?", (streak_days, max_streak, str(today), username))


def add_exp(conn: sqlite3.Connection, username: str, amount: int, source: str = "") -> None:
    ensure_user(conn, username)
    conn.execute("UPDATE User_Growth SET exp = COALESCE(exp, 0) + ? WHERE username = ?", (max(amount, 0), username))
    sync_growth_level(conn, username)
    if source:
        conn.execute(
            "INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description) VALUES (?, ?, 'exp', ?, ?)",
            (username, amount, source, f"EXP from {source}"),
        )


def add_currency(conn: sqlite3.Connection, username: str, coins: int = 0, diamonds: int = 0, source: str = "") -> None:
    ensure_user(conn, username)
    if coins:
        conn.execute("UPDATE User_Growth SET coins = COALESCE(coins, 0) + ? WHERE username = ?", (coins, username))
    if diamonds:
        conn.execute("UPDATE User_Growth SET diamonds = COALESCE(diamonds, 0) + ?, sunshine = COALESCE(sunshine, 0) + ? WHERE username = ?", (diamonds, diamonds, username))
        conn.execute(
            "INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description) VALUES (?, ?, 'gain', ?, ?)",
            (username, diamonds, source or "system", f"Currency gain from {source or 'system'}"),
        )


def spend_currency(conn: sqlite3.Connection, username: str, coins: int = 0, diamonds: int = 0, source: str = "") -> None:
    balance = build_growth_payload(conn, username)
    if coins > balance["coins"]:
        raise HTTPException(status_code=400, detail="金币不足")
    if diamonds > balance["diamonds"]:
        raise HTTPException(status_code=400, detail="钻石不足")
    if coins:
        conn.execute("UPDATE User_Growth SET coins = coins - ? WHERE username = ?", (coins, username))
    if diamonds:
        conn.execute("UPDATE User_Growth SET diamonds = diamonds - ?, sunshine = MAX(sunshine - ?, 0) WHERE username = ?", (diamonds, diamonds, username))
        conn.execute(
            "INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description) VALUES (?, ?, 'spend', ?, ?)",
            (username, -diamonds, source or "shop", f"Currency spend for {source or 'shop'}"),
        )


def record_focus_session(conn: sqlite3.Connection, username: str, duration: int, subject: str, status: str = "completed") -> None:
    conn.execute(
        "INSERT INTO Focus_Sessions (username, subject, duration_minutes, status, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (username, subject, max(duration, 0), status),
    )


def award_focus_completion(conn: sqlite3.Connection, username: str, duration: int, subject: str) -> dict[str, Any]:
    duration = max(int(duration), 0)
    mark_user_active(conn, username)
    record_focus_session(conn, username, duration, subject, "completed")
    exp_gain = max(10, duration)
    coins_gain = max(20, duration * 3)
    diamonds_gain = max(1, duration // 15)
    conn.execute("UPDATE User_Growth SET total_focus_minutes = COALESCE(total_focus_minutes, 0) + ?, focus_energy = COALESCE(focus_energy, 0) + ? WHERE username = ?", (duration, max(5, duration // 2), username))
    add_exp(conn, username, exp_gain, "focus_complete")
    add_currency(conn, username, coins=coins_gain, diamonds=diamonds_gain, source="focus_complete")
    growth = build_growth_payload(conn, username)
    return {"success": True, "message": "专注记录已同步", "exp_gained": exp_gain, "coins_gained": coins_gain, "diamonds_gained": diamonds_gain, "growth": growth}


def record_focus_session_v2(
    conn: sqlite3.Connection,
    username: str,
    duration: int,
    subject: str,
    status: str = "completed",
    session_log: str = "",
    task_difficulty: str = "L1",
    quality_multiplier: float = 1.0,
    task_difficulty_multiplier_value: float = 1.0,
    final_energy: int = 0,
    ai_feedback: str = "",
    evaluation_source: str = "fallback",
) -> None:
    conn.execute(
        """
        INSERT INTO Focus_Sessions (
            username, subject, duration_minutes, status, session_log, task_difficulty,
            quality_multiplier, task_difficulty_multiplier, final_energy, ai_feedback,
            evaluation_source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            username,
            subject,
            max(duration, 0),
            status,
            str(session_log or "").strip(),
            normalize_task_difficulty(task_difficulty),
            clamp_quality_multiplier(quality_multiplier, 1.0),
            float(task_difficulty_multiplier_value or 1.0),
            max(int(final_energy or 0), 0),
            str(ai_feedback or "").strip(),
            str(evaluation_source or "fallback"),
        ),
    )


def award_focus_completion_v2(
    conn: sqlite3.Connection,
    username: str,
    duration: int,
    subject: str,
    session_log: str = "",
    task_difficulty: str = "L1",
) -> dict[str, Any]:
    duration = max(int(duration), 0)
    normalized_difficulty = normalize_task_difficulty(task_difficulty)
    difficulty_multiplier = task_difficulty_multiplier(normalized_difficulty)
    evaluation = evaluate_study_log(session_log, normalized_difficulty, duration, subject)
    quality_multiplier = clamp_quality_multiplier(evaluation.get("quality_multiplier"), 1.0)
    final_energy = max(int(round(duration * 10 * difficulty_multiplier * quality_multiplier)), 0)

    mark_user_active(conn, username)
    record_focus_session_v2(
        conn,
        username,
        duration,
        subject,
        "completed",
        session_log=session_log,
        task_difficulty=normalized_difficulty,
        quality_multiplier=quality_multiplier,
        task_difficulty_multiplier_value=difficulty_multiplier,
        final_energy=final_energy,
        ai_feedback=evaluation.get("feedback", ""),
        evaluation_source=evaluation.get("evaluation_source", "fallback"),
    )

    exp_gain = max(10, duration)
    coins_gain = max(20, duration * 3)
    diamonds_gain = max(1, duration // 15)
    conn.execute(
        "UPDATE User_Growth SET total_focus_minutes = COALESCE(total_focus_minutes, 0) + ?, focus_energy = COALESCE(focus_energy, 0) + ? WHERE username = ?",
        (duration, final_energy, username),
    )
    add_exp(conn, username, exp_gain, "focus_complete")
    add_currency(conn, username, coins=coins_gain, diamonds=diamonds_gain, source="focus_complete")
    growth = build_growth_payload(conn, username)
    return {
        "success": True,
        "message": "专注记录已同步",
        "exp_gained": exp_gain,
        "coins_gained": coins_gain,
        "diamonds_gained": diamonds_gain,
        "final_energy": final_energy,
        "focus_energy_gained": final_energy,
        "quality_multiplier": quality_multiplier,
        "task_difficulty": normalized_difficulty,
        "task_difficulty_multiplier": difficulty_multiplier,
        "feedback": evaluation.get("feedback", FALLBACK_EVALUATION_FEEDBACK),
        "evaluation_source": evaluation.get("evaluation_source", "fallback"),
        "model": evaluation.get("model", DEFAULT_QWEN_MODEL),
        "growth": growth,
    }


def get_user_inventory_summary(conn: sqlite3.Connection, username: str) -> dict[int, dict[str, int]]:
    summary: dict[int, dict[str, int]] = defaultdict(lambda: {"owned_count": 0, "placed_count": 0, "available_to_place_count": 0})
    rows = conn.execute(
        "SELECT item_id, status, COUNT(*) AS count FROM User_Inventory WHERE username = ? GROUP BY item_id, status",
        (username,),
    ).fetchall()
    for row in rows:
        entry = summary[row["item_id"]]
        count = int(row["count"] or 0)
        if row["status"] == "placed":
            entry["placed_count"] += count
        else:
            entry["available_to_place_count"] += count
        entry["owned_count"] += count
    return summary


def enrich_shop_item(conn: sqlite3.Connection, row: sqlite3.Row, username: str = "") -> dict[str, Any]:
    item = dict(row)
    item["dimension"] = normalize_dimension(item.get("dimension"))
    placement_type = placement_type_for_category(item.get("category"))
    item["placement_type"] = placement_type
    item["grade"] = normalize_grade(item.get("rarity"))
    item["preview_path"] = item_preview_path(item)
    item["sprite_path"] = item.get("sprite_path") or ""
    item["grid_width"] = max(1, int(item.get("grid_width") or 1))
    item["grid_height"] = max(1, int(item.get("grid_height") or 1))
    item["icon"] = item.get("icon") or ("🏙️" if placement_type == "building" else "🌳")
    counts = {"owned_count": 0, "placed_count": 0, "available_to_place_count": 0}
    remaining_slots = 0
    if username:
        counts = get_user_inventory_summary(conn, username).get(item["id"], counts)
        if item["dimension"] == "3D":
            remaining_slots = city_slot_capacities(conn, username).get(placement_type, 0)
    item.update(counts)
    item["slot_capacity_remaining"] = remaining_slots
    return item


def pick_nearest_slot(placement_type: str, used_slot_ids: set[str], current_x: float = 0.0, current_z: float = 0.0) -> Optional[dict[str, Any]]:
    candidates = []
    for slot in city_slots():
        if not slot.get("enabled", True) or slot.get("slot_type") != placement_type or slot.get("slot_id") in used_slot_ids:
            continue
        dx = float(slot.get("x", 0)) - current_x
        dz = float(slot.get("z", 0)) - current_z
        candidates.append((math.sqrt(dx * dx + dz * dz), slot))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates else None


def restore_item_to_owned(conn: sqlite3.Connection, username: str, item_id: int) -> None:
    inventory_row = conn.execute("SELECT id FROM User_Inventory WHERE username = ? AND item_id = ? AND status = 'placed' ORDER BY id LIMIT 1", (username, item_id)).fetchone()
    if inventory_row:
        conn.execute("UPDATE User_Inventory SET status = 'owned' WHERE id = ?", (inventory_row["id"],))
    else:
        conn.execute("INSERT INTO User_Inventory (username, item_id, status) VALUES (?, ?, 'owned')", (username, item_id))


def migrate_city_placements(conn: sqlite3.Connection) -> None:
    slots = city_slot_index()
    if not slots:
        return
    users = [row["username"] for row in conn.execute("SELECT DISTINCT username FROM Island_Infrastructure WHERE map_id = 'city'").fetchall()]
    for username in users:
        used = set()
        rows = conn.execute(
            """
            SELECT ii.id AS placed_id, ii.username, ii.item_id, ii.position_x, ii.position_z, ii.slot_id, usi.category
            FROM Island_Infrastructure ii
            JOIN Unified_Shop_Items usi ON usi.id = ii.item_id
            WHERE ii.username = ? AND ii.map_id = 'city'
            ORDER BY ii.id
            """,
            (username,),
        ).fetchall()
        for row in rows:
            placement_type = placement_type_for_category(row["category"])
            slot_id = row["slot_id"]
            slot = None
            if slot_id and slot_id in slots and slot_id not in used and slots[slot_id]["slot_type"] == placement_type:
                slot = slots[slot_id]
            else:
                slot = pick_nearest_slot(placement_type, used, float(row["position_x"] or 0), float(row["position_z"] or 0))
            if not slot:
                conn.execute("DELETE FROM Island_Infrastructure WHERE id = ?", (row["placed_id"],))
                restore_item_to_owned(conn, username, row["item_id"])
                continue
            used.add(slot["slot_id"])
            conn.execute(
                "UPDATE Island_Infrastructure SET slot_id = ?, position_x = ?, position_y = ?, position_z = ?, rotation_y = ?, map_id = 'city' WHERE id = ?",
                (slot["slot_id"], float(slot.get("x", 0)), float(slot.get("y", 1.7)), float(slot.get("z", 0)), float(slot.get("rotation_y", 0)), row["placed_id"]),
            )


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS Users (username TEXT PRIMARY KEY, password TEXT NOT NULL, avatar TEXT DEFAULT '👨‍🚀');
            CREATE TABLE IF NOT EXISTS User_Growth (
                username TEXT PRIMARY KEY, focus_energy INTEGER DEFAULT 0, total_focus_minutes INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0, last_active_date DATE, sunshine INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, coins INTEGER DEFAULT 1000, diamonds INTEGER DEFAULT 50,
                exp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, discipline_score REAL DEFAULT 50,
                max_streak INTEGER DEFAULT 0, total_trees INTEGER DEFAULT 0, achievements_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS Focus_Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, subject TEXT DEFAULT '',
                duration_minutes INTEGER DEFAULT 0, status TEXT DEFAULT 'completed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Todo_Tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, is_completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ai_score REAL DEFAULT 0, proof_url TEXT DEFAULT '',
                score_updated_at TIMESTAMP, ai_feedback TEXT DEFAULT '',
                scheduled_date TEXT DEFAULT '', scheduled_time TEXT DEFAULT '', status TEXT DEFAULT 'todo',
                category TEXT DEFAULT '', accent TEXT DEFAULT '#4880FF'
            );
            CREATE TABLE IF NOT EXISTS Phone_Usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, usage_minutes INTEGER NOT NULL,
                category TEXT DEFAULT '娱乐', notes TEXT, report_date DATE DEFAULT (date('now', 'localtime')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS AI_Chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
                conversation_id TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_username TEXT NOT NULL, friend_username TEXT NOT NULL,
                status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                description TEXT DEFAULT '', category TEXT DEFAULT 'general', icon TEXT DEFAULT '🏆', exp_reward INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS User_Achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Unified_Shop_Items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT NOT NULL, name TEXT NOT NULL, name_cn TEXT,
                category TEXT NOT NULL, subcategory TEXT, tags TEXT, model_path TEXT NOT NULL, icon TEXT,
                price_sunshine INTEGER DEFAULT 50, rarity TEXT DEFAULT 'common', description TEXT,
                is_available BOOLEAN DEFAULT 1, sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price_coins INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS User_Shop_Favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, item_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS User_Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, item_id INTEGER NOT NULL,
                status TEXT DEFAULT 'owned', placed_x REAL, placed_z REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Island_Infrastructure (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, item_id INTEGER NOT NULL,
                position_x REAL NOT NULL, position_z REAL NOT NULL, rotation REAL DEFAULT 0,
                placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, position_y REAL DEFAULT 0, rotation_y REAL DEFAULT 0,
                scale REAL DEFAULT 1.0, map_id TEXT DEFAULT 'main', slot_id TEXT
            );
            CREATE TABLE IF NOT EXISTS Exams (
                exam_code TEXT PRIMARY KEY, title TEXT, config_json TEXT, answer_key_json TEXT,
                ai_prompt TEXT, audio_file TEXT, pdf_file TEXT, time_limit INTEGER
            );
            CREATE TABLE IF NOT EXISTS Exam_Submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, exam_code TEXT, room_id TEXT, username TEXT, objective_score REAL,
                attempted_score REAL, time_used INTEGER, subjective_answers TEXT, mistakes TEXT,
                subjective_score REAL DEFAULT 0, teacher_feedback TEXT DEFAULT '批改中...', submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Greenhouses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, room_code TEXT NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '',
                owner_username TEXT NOT NULL, max_seats INTEGER DEFAULT 8, is_public BOOLEAN DEFAULT 1,
                password TEXT DEFAULT '', theme TEXT DEFAULT 'space', total_sunshine INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Greenhouse_Seats (
                id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER NOT NULL, seat_number INTEGER NOT NULL,
                position_x REAL DEFAULT 0, position_z REAL DEFAULT 0, rotation_y REAL DEFAULT 0,
                is_occupied BOOLEAN DEFAULT 0, current_user TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS Greenhouse_Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER NOT NULL, username TEXT NOT NULL,
                seat_id INTEGER, task_id INTEGER, status TEXT DEFAULT 'growing', start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP, duration_minutes INTEGER DEFAULT 0, sunshine_earned INTEGER DEFAULT 0, ai_score REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS Sunshine_Transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, amount INTEGER NOT NULL,
                transaction_type TEXT NOT NULL, source TEXT DEFAULT '', description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Learning_Plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, title TEXT NOT NULL,
                goal TEXT NOT NULL, description TEXT DEFAULT '', target_date DATE,
                status TEXT DEFAULT 'active', progress_percent INTEGER DEFAULT 0,
                ai_generated BOOLEAN DEFAULT 0, category TEXT DEFAULT 'study',
                priority INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Learning_Stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER NOT NULL, stage_number INTEGER NOT NULL,
                title TEXT NOT NULL, description TEXT DEFAULT '', status TEXT DEFAULT 'pending',
                start_date DATE, end_date DATE, ai_suggested BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES Learning_Plans(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS Stage_Tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, stage_id INTEGER NOT NULL, title TEXT NOT NULL,
                description TEXT DEFAULT '', task_type TEXT DEFAULT 'study',
                estimated_minutes INTEGER DEFAULT 25, actual_minutes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending', sort_order INTEGER DEFAULT 0,
                linked_resource TEXT DEFAULT '', completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES Learning_Stages(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS Learning_Milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER NOT NULL, title TEXT NOT NULL,
                description TEXT DEFAULT '', target_date DATE, achieved_date DATE,
                is_checkpoint BOOLEAN DEFAULT 0, status TEXT DEFAULT 'pending', reward_exp INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES Learning_Plans(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS Posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, content TEXT NOT NULL,
                image_urls TEXT DEFAULT '[]', visibility TEXT DEFAULT 'friends',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS Post_Likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL, username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(post_id, username)
            );
            CREATE TABLE IF NOT EXISTS Post_Comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL, username TEXT NOT NULL,
                content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        ensure_column(conn, "Users", "avatar", "TEXT DEFAULT '👨‍🚀'")
        ensure_column(conn, "Users", "nickname", "TEXT DEFAULT ''")
        ensure_column(conn, "Users", "bio", "TEXT DEFAULT ''")
        ensure_column(conn, "User_Growth", "exp", "INTEGER DEFAULT 0")
        ensure_column(conn, "User_Growth", "level", "INTEGER DEFAULT 1")
        ensure_column(conn, "User_Growth", "discipline_score", "REAL DEFAULT 50")
        ensure_column(conn, "User_Growth", "max_streak", "INTEGER DEFAULT 0")
        ensure_column(conn, "User_Growth", "total_trees", "INTEGER DEFAULT 0")
        ensure_column(conn, "User_Growth", "achievements_count", "INTEGER DEFAULT 0")
        ensure_column(conn, "Achievements", "code", "TEXT")
        ensure_column(conn, "Unified_Shop_Items", "dimension", "TEXT DEFAULT '3D'")
        ensure_column(conn, "Unified_Shop_Items", "preview_path", "TEXT DEFAULT ''")
        ensure_column(conn, "Unified_Shop_Items", "sprite_path", "TEXT DEFAULT ''")
        ensure_column(conn, "Unified_Shop_Items", "grid_width", "INTEGER DEFAULT 1")
        ensure_column(conn, "Unified_Shop_Items", "grid_height", "INTEGER DEFAULT 1")
        ensure_column(conn, "Island_Infrastructure", "position_y", "REAL DEFAULT 0")
        ensure_column(conn, "Island_Infrastructure", "rotation_y", "REAL DEFAULT 0")
        ensure_column(conn, "Island_Infrastructure", "scale", "REAL DEFAULT 1.0")
        ensure_column(conn, "Island_Infrastructure", "map_id", "TEXT DEFAULT 'main'")
        ensure_column(conn, "Island_Infrastructure", "slot_id", "TEXT")
        ensure_column(conn, "Island_Infrastructure", "dimension", "TEXT DEFAULT '3D'")
        ensure_column(conn, "Island_Infrastructure", "grid_x", "INTEGER")
        ensure_column(conn, "Island_Infrastructure", "grid_y", "INTEGER")
        ensure_column(conn, "AI_Chats", "conversation_id", "TEXT DEFAULT ''")
        ensure_column(conn, "Focus_Sessions", "session_log", "TEXT DEFAULT ''")
        ensure_column(conn, "Focus_Sessions", "task_difficulty", "TEXT DEFAULT 'L1'")
        ensure_column(conn, "Focus_Sessions", "quality_multiplier", "REAL DEFAULT 1.0")
        ensure_column(conn, "Focus_Sessions", "task_difficulty_multiplier", "REAL DEFAULT 1.0")
        ensure_column(conn, "Focus_Sessions", "final_energy", "INTEGER DEFAULT 0")
        ensure_column(conn, "Focus_Sessions", "ai_feedback", "TEXT DEFAULT ''")
        ensure_column(conn, "Focus_Sessions", "evaluation_source", "TEXT DEFAULT 'fallback'")
        ensure_column(conn, "Todo_Tasks", "scheduled_date", "TEXT DEFAULT ''")
        ensure_column(conn, "Todo_Tasks", "scheduled_time", "TEXT DEFAULT ''")
        ensure_column(conn, "Todo_Tasks", "status", "TEXT DEFAULT 'todo'")
        ensure_column(conn, "Todo_Tasks", "category", "TEXT DEFAULT ''")
        ensure_column(conn, "Todo_Tasks", "accent", "TEXT DEFAULT '#4880FF'")
        if "achievement_code" in table_columns(conn, "Achievements"):
            conn.execute("UPDATE Achievements SET code = achievement_code WHERE (code IS NULL OR code = '')")
        conn.execute("UPDATE Unified_Shop_Items SET dimension = '3D' WHERE dimension IS NULL OR dimension = ''")
        conn.execute("UPDATE Unified_Shop_Items SET preview_path = '' WHERE preview_path IS NULL")
        conn.execute("UPDATE Unified_Shop_Items SET sprite_path = '' WHERE sprite_path IS NULL")
        conn.execute("UPDATE Unified_Shop_Items SET grid_width = 1 WHERE grid_width IS NULL OR grid_width < 1")
        conn.execute("UPDATE Unified_Shop_Items SET grid_height = 1 WHERE grid_height IS NULL OR grid_height < 1")
        conn.execute("UPDATE Island_Infrastructure SET dimension = '3D' WHERE dimension IS NULL OR dimension = ''")
        conn.execute("UPDATE Focus_Sessions SET session_log = '' WHERE session_log IS NULL")
        conn.execute("UPDATE Focus_Sessions SET task_difficulty = 'L1' WHERE task_difficulty IS NULL OR task_difficulty = ''")
        conn.execute("UPDATE Focus_Sessions SET quality_multiplier = 1.0 WHERE quality_multiplier IS NULL OR quality_multiplier < 0.5")
        conn.execute("UPDATE Focus_Sessions SET task_difficulty_multiplier = 1.0 WHERE task_difficulty_multiplier IS NULL OR task_difficulty_multiplier <= 0")
        conn.execute("UPDATE Focus_Sessions SET final_energy = 0 WHERE final_energy IS NULL OR final_energy < 0")
        conn.execute("UPDATE Focus_Sessions SET ai_feedback = '' WHERE ai_feedback IS NULL")
        conn.execute("UPDATE Focus_Sessions SET evaluation_source = 'fallback' WHERE evaluation_source IS NULL OR evaluation_source = ''")
        conn.execute("UPDATE Todo_Tasks SET scheduled_date = '' WHERE scheduled_date IS NULL")
        conn.execute("UPDATE Todo_Tasks SET scheduled_time = '' WHERE scheduled_time IS NULL")
        conn.execute("UPDATE Todo_Tasks SET category = '' WHERE category IS NULL")
        conn.execute("UPDATE Todo_Tasks SET accent = '#4880FF' WHERE accent IS NULL OR accent = ''")
        conn.execute("UPDATE Todo_Tasks SET status = CASE WHEN is_completed = 1 THEN 'done' ELSE 'todo' END WHERE status IS NULL OR status = ''")
        ensure_user(conn, "guest")
        sync_kenney_city_items(conn)
        sync_isometric_items(conn)
        seed_achievements(conn)
        seed_exams(conn)
        migrate_city_placements(conn)
        counts = conn.execute("SELECT username, COUNT(*) AS count FROM User_Achievements GROUP BY username").fetchall()
        for row in counts:
            conn.execute("UPDATE User_Growth SET achievements_count = ? WHERE username = ?", (row["count"], row["username"]))
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


init_db()


class DockUserAuth(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class AddExpRequest(BaseModel):
    username: str
    exp_amount: int = 0
    source: str = ""


class UpdateDisciplineRequest(BaseModel):
    username: str
    phone_minutes: int = 0


class FocusStartRequest(BaseModel):
    username: str
    subject: str = "专注"
    duration: int = 25
    tree_type: str = ""


class FocusEndRequest(BaseModel):
    session_id: int
    username: str
    status: str = "completed"


class FocusCompleteRequest(BaseModel):
    username: str
    duration: int
    subject: str = "专注"


class TodoAddRequest(BaseModel):
    username: str
    content: str
    scheduled_date: str = ""
    scheduled_time: str = ""
    status: str = "todo"
    category: str = ""
    accent: str = "#4880FF"


class TodoActionRequest(BaseModel):
    task_id: int
    username: str


TODO_STATUS_VALUES = {"todo", "in_progress", "done"}
TODO_ACCENT_FALLBACK = "#4880FF"


def normalize_todo_date(value: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise HTTPException(status_code=422, detail="scheduled_date must use YYYY-MM-DD")
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="scheduled_date must be a valid date") from exc
    return raw


def normalize_todo_time(value: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not re.fullmatch(r"\d{2}:\d{2}", raw):
        raise HTTPException(status_code=422, detail="scheduled_time must use HH:MM")
    hour, minute = (int(part) for part in raw.split(":"))
    if hour > 23 or minute > 59:
        raise HTTPException(status_code=422, detail="scheduled_time must be a valid 24-hour time")
    return raw


def normalize_todo_status(value: str = "todo", completed: bool = False) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if completed:
        return "done"
    return raw if raw in TODO_STATUS_VALUES and raw != "done" else "todo"


def normalize_todo_accent(value: str = "") -> str:
    raw = str(value or "").strip()
    return raw if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw) else TODO_ACCENT_FALLBACK


def todo_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    completed = bool(row["is_completed"])
    status = normalize_todo_status(row["status"], completed)
    return {
        "id": row["id"],
        "content": row["content"] or "",
        "title": row["content"] or "",
        "is_completed": completed,
        "isCompleted": completed,
        "created_at": row["created_at"] or "",
        "createdAt": row["created_at"] or "",
        "ai_score": row["ai_score"] or 0,
        "ai_feedback": row["ai_feedback"] or "",
        "scheduled_date": row["scheduled_date"] or "",
        "scheduledDate": row["scheduled_date"] or "",
        "scheduled_time": row["scheduled_time"] or "",
        "scheduledTime": row["scheduled_time"] or "",
        "status": status,
        "category": row["category"] or "",
        "accent": normalize_todo_accent(row["accent"]),
    }


class PhoneUsageReportRequest(BaseModel):
    username: str
    usage_minutes: int
    category: str = "学习"
    notes: str = ""
    screenshot_data: str = ""


class AIChatRequest(BaseModel):
    username: str
    message: str
    conversation_id: str = ""


class FriendRequestPayload(BaseModel):
    user_username: str
    friend_username: str


class FriendRespondPayload(BaseModel):
    friendship_id: int
    status: str


class FriendDeletePayload(BaseModel):
    user_username: str
    friend_username: str


class AvatarPayload(BaseModel):
    avatar: str = DEFAULT_AVATAR


class UnifiedShopBuyRequest(BaseModel):
    username: str
    item_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class UnifiedShopPlaceRequest(BaseModel):
    username: str
    item_id: int
    slot_id: Optional[str] = None
    position_x: float = 0
    position_y: float = 0
    position_z: float = 0
    rotation_y: float = 0
    scale: float = 1.0
    map_id: str = "city"
    dimension: str = "3D"
    grid_x: Optional[int] = None
    grid_y: Optional[int] = None


class FavoritePayload(BaseModel):
    username: str
    item_id: int


class RemovePlacedPayload(BaseModel):
    username: str


class ExamSubmitRequest(BaseModel):
    exam_code: str
    username: str
    answers: dict[str, Any]
    time_used: int = 0
    room_id: str = "solo"


class ExamAIAnalysisRequest(BaseModel):
    question: str
    user_answer: str = ""
    correct_answer: str = ""
    context: str = ""


class AchievementCheckPayload(BaseModel):
    username: str
    achievement_code: str


# ===== 学习计划相关模型 =====
class PlanCreateRequest(BaseModel):
    username: str
    title: str
    goal: str
    description: str = ""
    target_date: Optional[str] = None
    category: str = "study"
    ai_generate: bool = False
    stages: list[dict[str, Any]] = []


class PlanUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None


class StageUpdateRequest(BaseModel):
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class TaskCreateRequest(BaseModel):
    stage_id: int
    title: str
    description: str = ""
    task_type: str = "study"
    estimated_minutes: int = 25


class TaskCompleteRequest(BaseModel):
    username: str
    actual_minutes: int = 0


class AIGeneratePlanRequest(BaseModel):
    username: str
    goal: str
    duration_days: int = 30
    daily_hours: float = 2.0
    difficulty: str = "intermediate"
    context: dict[str, Any] = {}


class PlanChatRequest(BaseModel):
    username: str = "guest"
    message: str = ""
    plan_id: Optional[int] = None
    conversation_id: str = ""
    # FocusHub decomposition payload (backward-compatible extension)
    goal: str = ""
    style: str = "balanced"
    available_minutes: Optional[int] = None
    weak_points: str = ""
    system_prompt: str = ""
    user_prompt: str = ""


# ===== 学习计划辅助函数 =====
def plan_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "title": row["title"],
        "goal": row["goal"],
        "description": row["description"] or "",
        "target_date": row["target_date"] or "",
        "status": row["status"],
        "progress_percent": int(row["progress_percent"] or 0),
        "ai_generated": bool(row["ai_generated"]),
        "category": row["category"],
        "priority": int(row["priority"] or 1),
        "created_at": row["created_at"] or ""
    }


def stage_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "plan_id": row["plan_id"],
        "stage_number": int(row["stage_number"] or 1),
        "title": row["title"],
        "description": row["description"] or "",
        "status": row["status"],
        "start_date": row["start_date"] or "",
        "end_date": row["end_date"] or "",
        "ai_suggested": bool(row["ai_suggested"])
    }


def task_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "stage_id": row["stage_id"],
        "title": row["title"],
        "description": row["description"] or "",
        "task_type": row["task_type"],
        "estimated_minutes": int(row["estimated_minutes"] or 25),
        "actual_minutes": int(row["actual_minutes"] or 0),
        "status": row["status"],
        "sort_order": int(row["sort_order"] or 0),
        "linked_resource": row["linked_resource"] or ""
    }


def milestone_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "plan_id": row["plan_id"],
        "title": row["title"],
        "description": row["description"] or "",
        "target_date": row["target_date"] or "",
        "achieved_date": row["achieved_date"] or "",
        "is_checkpoint": bool(row["is_checkpoint"]),
        "status": row["status"],
        "reward_exp": int(row["reward_exp"] or 10)
    }


def update_plan_progress(conn: sqlite3.Connection, plan_id: int) -> None:
    """更新计划总进度"""
    stages = conn.execute(
        "SELECT id, status FROM Learning_Stages WHERE plan_id = ?", (plan_id,)
    ).fetchall()
    if not stages:
        return
    total = len(stages)
    completed = sum(1 for s in stages if s["status"] == "completed")
    progress = int((completed / total) * 100) if total > 0 else 0
    new_status = "completed" if completed == total else "active"
    conn.execute(
        "UPDATE Learning_Plans SET progress_percent = ?, status = ? WHERE id = ?",
        (progress, new_status, plan_id)
    )


# ===== 学习计划API端点 =====
@app.post("/api/plans/create")
def create_plan(payload: PlanCreateRequest) -> dict[str, Any]:
    """创建学习计划"""
    with closing(get_conn()) as conn:
        cursor = conn.execute(
            """INSERT INTO Learning_Plans
               (username, title, goal, description, target_date, category, ai_generated)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (payload.username, payload.title, payload.goal, payload.description,
             payload.target_date, payload.category, 0)
        )
        plan_id = cursor.lastrowid

        # 创建阶段和任务
        for idx, stage_data in enumerate(payload.stages):
            stage_cursor = conn.execute(
                """INSERT INTO Learning_Stages
                   (plan_id, stage_number, title, description, status)
                   VALUES (?, ?, ?, ?, 'pending')""",
                (plan_id, idx + 1, stage_data.get("title", f"阶段{idx+1}"),
                 stage_data.get("description", ""))
            )
            stage_id = stage_cursor.lastrowid
            for task in stage_data.get("tasks", []):
                conn.execute(
                    """INSERT INTO Stage_Tasks
                       (stage_id, title, description, task_type, estimated_minutes, status, sort_order)
                       VALUES (?, ?, ?, ?, ?, 'pending', 0)""",
                    (stage_id, task.get("title", ""),
                     task.get("description", ""),
                     task.get("task_type", "study"),
                     task.get("estimated_minutes", 25))
                )

        conn.commit()
        return {"success": True, "plan_id": plan_id}


@app.get("/api/plans/{username}")
def list_plans(username: str, status: str = "") -> dict[str, Any]:
    """获取用户的学习计划列表"""
    with closing(get_conn()) as conn:
        query = "SELECT * FROM Learning_Plans WHERE username = ?"
        params = [username]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY priority DESC, created_at DESC"
        rows = conn.execute(query, params).fetchall()
        plans = [plan_row_to_dict(row) for row in rows]

        # 为每个计划添加阶段摘要
        for plan in plans:
            stages = conn.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as done FROM Learning_Stages WHERE plan_id = ?",
                (plan["id"],)
            ).fetchone()
            plan["stages_total"] = int(stages["total"] or 0)
            plan["stages_completed"] = int(stages["done"] or 0)

        return {"success": True, "plans": plans}


@app.get("/api/plans/detail/{plan_id}")
def get_plan_detail(plan_id: int) -> dict[str, Any]:
    """获取计划详情，包含所有阶段和任务"""
    with closing(get_conn()) as conn:
        plan_row = conn.execute(
            "SELECT * FROM Learning_Plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if not plan_row:
            return {"success": False, "error": "计划不存在"}

        plan = plan_row_to_dict(plan_row)

        # 获取阶段
        stage_rows = conn.execute(
            "SELECT * FROM Learning_Stages WHERE plan_id = ? ORDER BY stage_number",
            (plan_id,)
        ).fetchall()
        stages = []
        for stage_row in stage_rows:
            stage = stage_row_to_dict(stage_row)
            # 获取任务
            task_rows = conn.execute(
                "SELECT * FROM Stage_Tasks WHERE stage_id = ? ORDER BY sort_order",
                (stage["id"],)
            ).fetchall()
            stage["tasks"] = [task_row_to_dict(t) for t in task_rows]
            stages.append(stage)
        plan["stages"] = stages

        # 获取里程碑
        milestone_rows = conn.execute(
            "SELECT * FROM Learning_Milestones WHERE plan_id = ? ORDER BY target_date",
            (plan_id,)
        ).fetchall()
        plan["milestones"] = [milestone_row_to_dict(m) for m in milestone_rows]

        return {"success": True, "plan": plan}


@app.put("/api/plans/{plan_id}")
def update_plan(plan_id: int, payload: PlanUpdateRequest) -> dict[str, Any]:
    """更新计划"""
    with closing(get_conn()) as conn:
        updates = []
        params = []
        if payload.title is not None:
            updates.append("title = ?")
            params.append(payload.title)
        if payload.description is not None:
            updates.append("description = ?")
            params.append(payload.description)
        if payload.status is not None:
            updates.append("status = ?")
            params.append(payload.status)
        if payload.priority is not None:
            updates.append("priority = ?")
            params.append(payload.priority)
        if not updates:
            return {"success": True, "message": "无更新"}
        params.append(plan_id)
        conn.execute(f"UPDATE Learning_Plans SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        return {"success": True}


@app.delete("/api/plans/{plan_id}")
def delete_plan(plan_id: int, username: str) -> dict[str, Any]:
    """删除计划"""
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM Learning_Plans WHERE id = ? AND username = ?", (plan_id, username))
        conn.commit()
        return {"success": True}


@app.put("/api/plans/{plan_id}/stages/{stage_id}")
def update_stage(plan_id: int, stage_id: int, payload: StageUpdateRequest) -> dict[str, Any]:
    """更新阶段状态"""
    with closing(get_conn()) as conn:
        updates = []
        params = []
        if payload.status is not None:
            updates.append("status = ?")
            params.append(payload.status)
        if payload.start_date is not None:
            updates.append("start_date = ?")
            params.append(payload.start_date)
        if payload.end_date is not None:
            updates.append("end_date = ?")
            params.append(payload.end_date)
        if not updates:
            return {"success": True}
        params.extend([stage_id, plan_id])
        conn.execute(
            f"UPDATE Learning_Stages SET {', '.join(updates)} WHERE id = ? AND plan_id = ?",
            params
        )
        update_plan_progress(conn, plan_id)
        conn.commit()
        return {"success": True}


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, payload: TaskCompleteRequest) -> dict[str, Any]:
    """完成任务"""
    with closing(get_conn()) as conn:
        from datetime import datetime
        conn.execute(
            """UPDATE Stage_Tasks SET status = 'completed', actual_minutes = ?, completed_at = ?
               WHERE id = ?""",
            (payload.actual_minutes, datetime.now().isoformat(), task_id)
        )
        # 更新所属阶段的进度
        task = conn.execute("SELECT stage_id FROM Stage_Tasks WHERE id = ?", (task_id,)).fetchone()
        if task:
            stage_id = task["stage_id"]
            stage = conn.execute(
                "SELECT plan_id, id FROM Learning_Stages WHERE id = ?", (stage_id,)
            ).fetchone()
            if stage:
                # 检查阶段是否全部完成
                tasks = conn.execute(
                    "SELECT COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as done FROM Stage_Tasks WHERE stage_id = ?",
                    (stage_id,)
                ).fetchone()
                if tasks["total"] == tasks["done"]:
                    conn.execute("UPDATE Learning_Stages SET status = 'completed' WHERE id = ?", (stage_id,))
                update_plan_progress(conn, stage["plan_id"])
        conn.commit()
        return {"success": True}


@app.get("/api/plans/daily/{username}")
def get_daily_plan(username: str) -> dict[str, Any]:
    """获取今日计划推荐"""
    from datetime import date
    today = date.today().isoformat()
    with closing(get_conn()) as conn:
        # 获取活动计划
        plans = conn.execute(
            "SELECT * FROM Learning_Plans WHERE username = ? AND status = 'active' ORDER BY priority DESC LIMIT 1",
            (username,)
        ).fetchall()
        if not plans:
            return {"success": True, "today_tasks": [], "active_plan": None, "milestone_alerts": []}

        active_plan = plan_row_to_dict(plans[0])
        plan_id = active_plan["id"]

        # 获取进行中或待开始的阶段
        stages = conn.execute(
            """SELECT * FROM Learning_Stages WHERE plan_id = ? AND status IN ('pending', 'in_progress')
               ORDER BY stage_number LIMIT 1""",
            (plan_id,)
        ).fetchall()

        today_tasks = []
        for stage in stages:
            stage_dict = stage_row_to_dict(stage)
            tasks = conn.execute(
                "SELECT * FROM Stage_Tasks WHERE stage_id = ? AND status = 'pending' ORDER BY sort_order LIMIT 5",
                (stage["id"],)
            ).fetchall()
            for t in tasks:
                task = task_row_to_dict(t)
                task["stage_title"] = stage_dict["title"]
                today_tasks.append(task)

        # 获取临近的里程碑
        milestone_alerts = []
        milestones = conn.execute(
            """SELECT * FROM Learning_Milestones WHERE plan_id = ? AND status = 'pending'
               AND target_date <= date(?, '+7 days') ORDER BY target_date""",
            (plan_id, today)
        ).fetchall()
        milestone_alerts = [milestone_row_to_dict(m) for m in milestones]

        return {
            "success": True,
            "today_tasks": today_tasks,
            "active_plan": active_plan,
            "milestone_alerts": milestone_alerts,
            "focus_suggestion": "今天保持专注，完成计划中的任务！" if today_tasks else "暂无待办任务"
        }


@app.post("/api/plans/ai/generate-stages")
def ai_generate_stages(payload: AIGeneratePlanRequest) -> dict[str, Any]:
    """AI生成学习计划"""
    prompt = f"""你是一个学习规划专家。请根据用户的学习目标生成一个结构化的学习计划。

用户目标: {payload.goal}
可用天数: {payload.duration_days}天
每日学习时长: {payload.daily_hours}小时
基础水平: {payload.difficulty}

请严格按照以下JSON格式返回，不要添加其他内容:
{{
    "title": "计划标题",
    "stages": [
        {{
            "title": "阶段标题",
            "description": "阶段描述",
            "estimated_days": 预计天数,
            "tasks": [
                {{"title": "任务标题", "task_type": "study|practice|review|test", "estimated_minutes": 预计分钟}}
            ]
        }}
    ],
    "milestones": [
        {{"title": "里程碑标题", "target_day": 目标天数, "is_checkpoint": true|false}}
    ],
    "suggestions": "学习建议"
}}"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content or ""

        # 解析JSON
        import json
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"title": payload.goal[:50], "stages": [], "milestones": [], "suggestions": content}

        # 保存到数据库
        with closing(get_conn()) as conn:
            cursor = conn.execute(
                """INSERT INTO Learning_Plans
                   (username, title, goal, target_date, category, ai_generated)
                   VALUES (?, ?, ?, date('now', '+' || ? || ' days'), 'ai_generated', 1)""",
                (payload.username, result.get("title", payload.goal[:50]), payload.goal, payload.duration_days)
            )
            plan_id = cursor.lastrowid

            for idx, stage in enumerate(result.get("stages", [])):
                stage_cursor = conn.execute(
                    """INSERT INTO Learning_Stages
                       (plan_id, stage_number, title, description, ai_suggested)
                       VALUES (?, ?, ?, ?, 1)""",
                    (plan_id, idx + 1, stage.get("title", f"阶段{idx+1}"), stage.get("description", ""))
                )
                stage_id = stage_cursor.lastrowid
                for task in stage.get("tasks", []):
                    conn.execute(
                        """INSERT INTO Stage_Tasks
                           (stage_id, title, task_type, estimated_minutes, status)
                           VALUES (?, ?, ?, ?, 'pending')""",
                        (stage_id, task.get("title", ""),
                         task.get("task_type", "study"),
                         task.get("estimated_minutes", 25))
                    )

            for ms in result.get("milestones", []):
                from datetime import date, timedelta
                target_date = (date.today() + timedelta(days=ms.get("target_day", 7))).isoformat()
                conn.execute(
                    """INSERT INTO Learning_Milestones
                       (plan_id, title, target_date, is_checkpoint)
                       VALUES (?, ?, ?, ?)""",
                    (plan_id, ms.get("title", ""), target_date, ms.get("is_checkpoint", False))
                )

            conn.commit()

        return {
            "success": True,
            "plan_id": plan_id,
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e), "fallback": {
            "title": payload.goal[:50],
            "stages": [
                {"title": "基础学习", "tasks": [{"title": "入门学习", "task_type": "study", "estimated_minutes": 30}]},
                {"title": "深入理解", "tasks": [{"title": "核心概念", "task_type": "study", "estimated_minutes": 45}]},
                {"title": "实践练习", "tasks": [{"title": "动手实践", "task_type": "practice", "estimated_minutes": 60}]}
            ],
            "milestones": [{"title": "完成基础", "target_day": payload.duration_days // 3}]
        }}


@app.post("/api/plans/ai/chat")
def plan_ai_chat(payload: PlanChatRequest) -> dict[str, Any]:
    """对话式规划（兼容 FocusHub AI 任务拆解请求）"""

    def extract_steps_from_text(raw_text: str) -> list[dict[str, Any]]:
        text = str(raw_text or "").strip()
        if not text:
            return []

        # 支持 ```json ... ``` 或前后带解释文本的响应
        text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text, flags=re.IGNORECASE)
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []

        try:
            parsed = json.loads(match.group(0))
        except Exception:
            return []

        if not isinstance(parsed, list):
            return []

        steps: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or item.get("task") or "").strip()
            if not title:
                continue

            if item.get("estimatedPomodoros") is not None:
                try:
                    estimated = int(round(float(item.get("estimatedPomodoros"))))
                except Exception:
                    estimated = 1
            elif item.get("minutes") is not None:
                try:
                    estimated = int(round(float(item.get("minutes")) / 25))
                except Exception:
                    estimated = 1
            else:
                estimated = 1
            estimated = max(1, min(3, estimated))

            steps.append({
                "title": title,
                "estimatedPomodoros": estimated,
                "doneDefinition": str(item.get("doneDefinition") or item.get("done_definition") or "").strip(),
                "reason": str(item.get("reason") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "difficulty": str(item.get("difficulty") or "medium").strip() or "medium",
                "category": str(item.get("category") or "").strip()
            })

        return steps

    planning_mode = bool(
        str(payload.goal or "").strip()
        or str(payload.system_prompt or "").strip()
        or str(payload.user_prompt or "").strip()
    )

    context_info = ""
    if payload.plan_id:
        with closing(get_conn()) as conn:
            plan = conn.execute("SELECT * FROM Learning_Plans WHERE id = ?", (payload.plan_id,)).fetchone()
            if plan:
                context_info = f"\n\n当前计划: {plan['title']}\n目标: {plan['goal']}\n进度: {plan['progress_percent']}%"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        if planning_mode:
            system_prompt = (payload.system_prompt or "").strip() or (
                "你是任务拆解助手。请只输出 JSON 数组，不要输出 markdown 或解释。"
                "每个元素至少包含 title、estimatedPomodoros(1-3)、doneDefinition、reason。"
            )
            user_prompt = (payload.user_prompt or "").strip() or (
                f"目标: {payload.goal}\n"
                f"风格: {payload.style}\n"
                f"可用分钟: {payload.available_minutes}\n"
                f"薄弱点: {payload.weak_points}\n"
                "请只返回 JSON 数组。"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        else:
            prompt = f"""你是一个学习规划助手，帮助用户制定和调整学习计划。
{context_info}

用户消息: {payload.message}

请给出有帮助的学习规划建议，保持回复简洁明了。"""
            messages = [{"role": "user", "content": prompt}]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        reply = response.choices[0].message.content or "抱歉，我暂时无法回答。"
        if planning_mode:
            return {"success": True, "reply": reply, "steps": extract_steps_from_text(reply)}
        return {"success": True, "reply": reply}
    except Exception as e:
        if planning_mode:
            return {"success": False, "reply": f"AI服务暂时不可用: {str(e)}", "steps": []}
        return {"success": False, "reply": f"AI服务暂时不可用: {str(e)}"}


# ===== 学习计划结束 =====


class GreenhouseCreatePayload(BaseModel):
    name: str
    description: str = ""
    max_seats: int = Field(default=4, ge=2, le=8)
    is_public: bool = True
    password: str = ""
    theme: str = "space"
    owner_username: str


class GreenhouseJoinPayload(BaseModel):
    room_id: Optional[int] = None
    username: str = "guest"
    password: str = ""
    seat_index: Optional[int] = None


class GreenhouseLeavePayload(BaseModel):
    room_id: int
    username: str = "guest"


class GreenhouseStartPayload(BaseModel):
    room_id: int
    username: str = "guest"
    duration: int = Field(default=25, ge=1, le=240)
    task_id: Optional[int] = None


# ===== 圈子功能 =====
class PostCreatePayload(BaseModel):
    username: str
    content: str = Field(default="", max_length=1000)
    image_urls: list[str] = Field(default_factory=list)
    visibility: str = Field(default="friends", pattern="^(public|friends)$")


class PostCommentPayload(BaseModel):
    post_id: int
    username: str
    content: str = Field(default="", max_length=500)


class PostLikePayload(BaseModel):
    post_id: int
    username: str


# ===== 圈子功能结束 =====


class GreenhouseEndPayload(BaseModel):
    room_id: int
    username: str = "guest"
    status: str = "completed"


class GreenhouseEmojiPayload(BaseModel):
    room_id: int
    username: str = "guest"
    emoji: str


class PKCreatePayload(BaseModel):
    creator: str
    opponent: str
    type: str = "focus"
    duration: int = 24
    target_value: int = 0


class PKDecisionPayload(BaseModel):
    pk_id: int
    username: str


def refresh_user_achievements(conn: sqlite3.Connection, username: str) -> list[dict[str, Any]]:
    growth = build_growth_payload(conn, username)
    placed_count = conn.execute("SELECT COUNT(*) AS count FROM Island_Infrastructure WHERE username = ? AND map_id = 'city'", (username,)).fetchone()["count"]
    unlocked_codes: list[str] = []
    if growth["total_focus_minutes"] >= 1:
        unlocked_codes.append("first_focus")
    if growth["total_focus_minutes"] >= 300:
        unlocked_codes.append("focus_300")
    if growth["total_focus_minutes"] >= 1000:
        unlocked_codes.append("focus_1000")
    if growth["streak_days"] >= 3:
        unlocked_codes.append("streak_3")
    if growth["streak_days"] >= 7:
        unlocked_codes.append("streak_7")
    if placed_count >= 1:
        unlocked_codes.append("builder_1")

    unlocked = []
    for code in unlocked_codes:
        achievement = conn.execute("SELECT id, exp_reward FROM Achievements WHERE code = ?", (code,)).fetchone()
        if not achievement:
            continue
        exists = conn.execute("SELECT 1 FROM User_Achievements WHERE username = ? AND achievement_id = ?", (username, achievement["id"])).fetchone()
        if not exists:
            conn.execute("INSERT INTO User_Achievements (username, achievement_id, unlocked_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (username, achievement["id"]))
            add_exp(conn, username, achievement["exp_reward"], f"achievement:{code}")
        unlocked.append({"achievement_id": achievement["id"], "code": code})
    return unlocked


def generate_ai_reply(conn: sqlite3.Connection, username: str, message: str) -> str:
    growth = build_growth_payload(conn, username)
    pending_tasks = conn.execute("SELECT content FROM Todo_Tasks WHERE username = ? AND is_completed = 0 ORDER BY id DESC LIMIT 3", (username,)).fetchall()
    tasks = [row["content"] for row in pending_tasks]
    lowered = message.lower()
    if "计划" in message or "安排" in message:
        task_line = "、".join(tasks) if tasks else "还没有录入任务"
        return f"建议你先用一个 25 分钟专注段开启今天的节奏。\n当前待办：{task_line}。\n推荐顺序：1. 最难任务先做 25 分钟 2. 休息 5 分钟 3. 处理轻量任务。"
    if "分心" in message or "focus" in lowered:
        return f"你当前累计专注 {growth['total_focus_minutes']} 分钟，已经有基础了。\n下一轮建议：手机静音 + 桌面只留一个任务 + 先做 15 分钟热启动。"
    if "考试" in message or "英语" in message:
        return "先做一套语言考核站，再把错题分成词汇、语法、阅读三类，各写一句复盘。"
    return "副官终端已收到你的请求。\n建议现在先开启一轮短专注，把目标缩成 1 个可执行动作，再回来汇报进展。"


def period_day_count(period: str) -> int:
    return {"day": 1, "daily": 1, "week": 7, "weekly": 7, "month": 30, "monthly": 30, "year": 365}.get(period, 7)


def focus_daily_stats(conn: sqlite3.Connection, username: str, days: int) -> list[dict[str, Any]]:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    rows = conn.execute(
        """
        SELECT DATE(created_at) AS stat_date, SUM(duration_minutes) AS focus_minutes
        FROM Focus_Sessions
        WHERE username = ? AND DATE(created_at) BETWEEN ? AND ? AND status = 'completed'
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
        """,
        (username, str(start_date), str(end_date)),
    ).fetchall()
    by_date = {row["stat_date"]: int(row["focus_minutes"] or 0) for row in rows}
    stats = []
    for offset in range(days):
        current = start_date + timedelta(days=offset)
        stats.append({"stat_date": str(current), "focus_minutes": by_date.get(str(current), 0)})
    return stats


def leaderboard_rows(conn: sqlite3.Connection, metric: str) -> list[dict[str, Any]]:
    if metric == "exp":
        rows = conn.execute("SELECT username, COALESCE(exp, 0) AS score FROM User_Growth ORDER BY score DESC, username ASC LIMIT 50").fetchall()
    elif metric == "streak":
        rows = conn.execute("SELECT username, COALESCE(streak_days, 0) AS score FROM User_Growth ORDER BY score DESC, username ASC LIMIT 50").fetchall()
    else:
        rows = conn.execute("SELECT username, COALESCE(total_focus_minutes, 0) AS score FROM User_Growth ORDER BY score DESC, username ASC LIMIT 50").fetchall()
    return [dict(row) for row in rows]


class GreenhouseSocketManager:
    def __init__(self) -> None:
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms[room_id].add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        room = self.rooms.get(room_id)
        if not room:
            return
        room.discard(websocket)
        if not room:
            self.rooms.pop(room_id, None)

    async def broadcast(self, room_id: int, message: dict[str, Any]) -> None:
        room = list(self.rooms.get(room_id, set()))
        stale = []
        for websocket in room:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(room_id, websocket)


socket_manager = GreenhouseSocketManager()


def ensure_greenhouse_seats(conn: sqlite3.Connection, room_id: int, max_seats: int) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM Greenhouse_Seats WHERE room_id = ?", (room_id,)).fetchone()["count"]
    if existing >= max_seats:
        return
    for seat_number in range(existing + 1, max_seats + 1):
        conn.execute(
            "INSERT INTO Greenhouse_Seats (room_id, seat_number, position_x, position_z, rotation_y, is_occupied, current_user) VALUES (?, ?, 0, 0, 0, 0, '')",
            (room_id, seat_number),
        )


def cleanup_greenhouse_sessions(conn: sqlite3.Connection, room_id: Optional[int] = None) -> None:
    query = "SELECT id, room_id, seat_id, username, duration_minutes, start_time FROM Greenhouse_Sessions WHERE status = 'growing'"
    params: tuple[Any, ...] = ()
    if room_id is not None:
        query += " AND room_id = ?"
        params = (room_id,)
    rows = conn.execute(query, params).fetchall()
    for row in rows:
        try:
            start_time = datetime.fromisoformat(str(row["start_time"]).replace(" ", "T"))
        except ValueError:
            continue
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        limit_seconds = max(int(row["duration_minutes"] or 0), 0) * 60
        if limit_seconds <= 0 or elapsed < limit_seconds:
            continue
        diamonds_earned = max(1, int(row["duration_minutes"] or 0) // 10)
        conn.execute("UPDATE Greenhouse_Sessions SET status = 'completed', end_time = CURRENT_TIMESTAMP, sunshine_earned = ? WHERE id = ?", (diamonds_earned, row["id"]))
        if row["seat_id"]:
            conn.execute("UPDATE Greenhouse_Seats SET is_occupied = 0, current_user = '' WHERE id = ?", (row["seat_id"],))
        add_currency(conn, row["username"], diamonds=diamonds_earned, source="greenhouse_complete")
        add_exp(conn, row["username"], max(10, int(row["duration_minutes"] or 0) // 2), "greenhouse_complete")


def greenhouse_snapshot(conn: sqlite3.Connection, room_id: int) -> dict[str, Any]:
    cleanup_greenhouse_sessions(conn, room_id)
    room = conn.execute("SELECT * FROM Greenhouses WHERE id = ?", (room_id,)).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    ensure_greenhouse_seats(conn, room_id, int(room["max_seats"] or 4))
    seats = []
    for row in conn.execute("SELECT id, seat_number, is_occupied, current_user, position_x, position_z, rotation_y FROM Greenhouse_Seats WHERE room_id = ? ORDER BY seat_number", (room_id,)):
        seats.append(
            {
                "id": row["id"],
                "seat_number": row["seat_number"],
                "seat_index": int(row["seat_number"]) - 1,
                "username": row["current_user"] or "",
                "is_occupied": bool(row["is_occupied"]),
                "position_x": row["position_x"],
                "position_z": row["position_z"],
                "rotation_y": row["rotation_y"],
            }
        )
    growing_users = []
    session_rows = conn.execute("SELECT id, username, duration_minutes, start_time, seat_id FROM Greenhouse_Sessions WHERE room_id = ? AND status = 'growing' ORDER BY id", (room_id,)).fetchall()
    for row in session_rows:
        try:
            start_time = datetime.fromisoformat(str(row["start_time"]).replace(" ", "T"))
        except ValueError:
            start_time = datetime.utcnow()
        remaining_seconds = max(int(row["duration_minutes"] or 0) * 60 - int((datetime.utcnow() - start_time).total_seconds()), 0)
        growing_users.append({"session_id": row["id"], "username": row["username"], "duration": int(row["duration_minutes"] or 0), "remaining_seconds": remaining_seconds, "seat_id": row["seat_id"]})
    occupied = sum(1 for seat in seats if seat["is_occupied"])
    return {"greenhouse": {**dict(room), "current_users": occupied}, "seats": seats, "growing_users": growing_users}


async def broadcast_greenhouse_sync(room_id: int) -> None:
    with closing(get_conn()) as conn:
        snapshot = greenhouse_snapshot(conn, room_id)
    await socket_manager.broadcast(room_id, {"type": "sync", "seats": snapshot["seats"], "growing_users": snapshot["growing_users"]})


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return {"ok": True}


@app.post("/api/register")
def register(payload: DockUserAuth) -> dict[str, Any]:
    username = payload.username.strip()
    password = payload.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    with closing(get_conn()) as conn:
        if conn.execute("SELECT username FROM Users WHERE username = ?", (username,)).fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        ensure_user(conn, username, password)
        conn.execute("UPDATE Users SET password = ? WHERE username = ?", (password, username))
        conn.commit()
    return {"success": True, "message": "注册成功"}


@app.post("/api/login")
def login(payload: DockUserAuth) -> dict[str, Any]:
    username = payload.username.strip()
    password = payload.password.strip()
    with closing(get_conn()) as conn:
        user = conn.execute("SELECT username FROM Users WHERE username = ? AND password = ?", (username, password)).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"success": True, "username": username}


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


@app.post("/api/change-password")
def change_password(payload: ChangePasswordRequest) -> dict[str, Any]:
    """修改用户密码"""
    username = payload.username.strip()
    old_password = payload.old_password.strip()
    new_password = payload.new_password.strip()

    if not username or not old_password or not new_password:
        raise HTTPException(status_code=400, detail="所有字段都不能为空")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少需要6个字符")

    with closing(get_conn()) as conn:
        # 验证旧密码
        user = conn.execute("SELECT username FROM Users WHERE username = ? AND password = ?", (username, old_password)).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="原密码错误")
        # 更新密码
        conn.execute("UPDATE Users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
    return {"success": True, "message": "密码修改成功"}


@app.get("/api/growth/{username}")
def get_growth(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        growth = build_growth_payload(conn, username)
    return {"success": True, "growth": growth, **growth}


@app.post("/api/growth/add-exp")
def growth_add_exp(payload: AddExpRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        add_exp(conn, payload.username, payload.exp_amount, payload.source or "manual")
        conn.commit()
        growth = build_growth_payload(conn, payload.username)
    return {"success": True, "growth": growth}


@app.post("/api/growth/check-streak")
def growth_check_streak(payload: dict[str, str]) -> dict[str, Any]:
    username = payload.get("username", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="缺少用户名")
    with closing(get_conn()) as conn:
        mark_user_active(conn, username)
        conn.commit()
        growth = build_growth_payload(conn, username)
    return {"success": True, "streak_days": growth["streak_days"], "growth": growth}


@app.post("/api/growth/update-stats")
def growth_update_stats(payload: dict[str, Any]) -> dict[str, Any]:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise HTTPException(status_code=400, detail="缺少用户名")
    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        conn.execute(
            "UPDATE User_Growth SET focus_energy = ?, total_focus_minutes = ?, discipline_score = ? WHERE username = ?",
            (int(payload.get("focus_energy", 0)), int(payload.get("total_focus_minutes", 0)), float(payload.get("discipline_score", 50)), username),
        )
        conn.commit()
        growth = build_growth_payload(conn, username)
    return {"success": True, "growth": growth}


@app.post("/api/growth/update-discipline")
def update_discipline(payload: UpdateDisciplineRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        current = build_growth_payload(conn, payload.username)
        penalty = min(max(payload.phone_minutes, 0) / 6.0, 45.0)
        new_score = max(0.0, min(100.0, 100.0 - penalty))
        if current["discipline_score"] > 0:
            new_score = round((current["discipline_score"] * 0.5) + (new_score * 0.5), 1)
        conn.execute("UPDATE User_Growth SET discipline_score = ? WHERE username = ?", (new_score, payload.username))
        conn.commit()
        growth = build_growth_payload(conn, payload.username)
    return {"success": True, "growth": growth, "discipline_score": growth["discipline_score"]}


@app.post("/api/focus/start")
def focus_start(payload: FocusStartRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.username)
        cursor = conn.execute("INSERT INTO Focus_Sessions (username, subject, duration_minutes, status, created_at) VALUES (?, ?, ?, 'ongoing', CURRENT_TIMESTAMP)", (payload.username, payload.subject, payload.duration))
        conn.commit()
    return {"success": True, "session_id": cursor.lastrowid}


@app.post("/api/focus/end")
def focus_end(payload: FocusEndRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        session = conn.execute("SELECT duration_minutes, subject FROM Focus_Sessions WHERE id = ? AND username = ?", (payload.session_id, payload.username)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="专注记录不存在")
        if payload.status == "completed":
            result = award_focus_completion(conn, payload.username, int(session["duration_minutes"] or 0), session["subject"] or "专注")
            conn.execute("DELETE FROM Focus_Sessions WHERE id = ?", (payload.session_id,))
        else:
            conn.execute("UPDATE Focus_Sessions SET status = ? WHERE id = ?", (payload.status, payload.session_id))
            result = {"success": True, "message": "专注记录已结束"}
        conn.commit()
    return result


@app.post("/api/focus/complete")
def focus_complete(payload: FocusCompleteRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        result = award_focus_completion(conn, payload.username, payload.duration, payload.subject)
        refresh_user_achievements(conn, payload.username)
        conn.commit()
    return result


@app.post("/api/ai/evaluate-study-log")
def ai_evaluate_study_log(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    evaluation = evaluate_study_log(
        str(payload.get("session_log", "") or ""),
        str(payload.get("task_difficulty", "L1") or "L1"),
        int(payload.get("duration_minutes") or 0),
        str(payload.get("subject", "专注") or "专注"),
        str(payload.get("model", DEFAULT_QWEN_MODEL) or DEFAULT_QWEN_MODEL),
    )
    return {
        "success": True,
        "qualityMultiplier": evaluation.get("quality_multiplier", 1.0),
        "feedback": evaluation.get("feedback", FALLBACK_EVALUATION_FEEDBACK),
        "source": evaluation.get("evaluation_source", "fallback"),
        "model": evaluation.get("model", DEFAULT_QWEN_MODEL),
        "rawContent": evaluation.get("raw_content", ""),
    }


@app.post("/api/focus/complete-v2")
def focus_complete_v2(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise HTTPException(status_code=400, detail="缺少用户名")

    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        result = award_focus_completion_v2(
            conn,
            username,
            int(payload.get("duration") or 0),
            str(payload.get("subject", "专注") or "专注"),
            session_log=str(payload.get("session_log", "") or ""),
            task_difficulty=str(payload.get("task_difficulty", "L1") or "L1"),
        )
        refresh_user_achievements(conn, username)
        conn.commit()
    return result


@app.get("/api/focus/stats/{username}")
def focus_stats(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        total_sessions = conn.execute("SELECT COUNT(*) AS count FROM Focus_Sessions WHERE username = ? AND status = 'completed'", (username,)).fetchone()["count"]
        total_minutes = conn.execute("SELECT COALESCE(SUM(duration_minutes), 0) AS total FROM Focus_Sessions WHERE username = ? AND status = 'completed'", (username,)).fetchone()["total"]
        dead_trees = conn.execute("SELECT COUNT(*) AS count FROM Focus_Sessions WHERE username = ? AND status = 'failed'", (username,)).fetchone()["count"]
    return {"success": True, "stats": {"total_sessions": total_sessions, "total_minutes": total_minutes, "dead_trees": dead_trees}}


@app.get("/api/focus/history/{username}")
def focus_history(username: str, limit: int = 10) -> dict[str, Any]:
    """获取用户的专注历史记录"""
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT id, subject, duration_minutes, tree_type, status, created_at "
            "FROM Focus_Sessions WHERE username = ? ORDER BY created_at DESC LIMIT ?",
            (username, limit)
        ).fetchall()
        history = []
        for row in rows:
            history.append({
                "id": row["id"],
                "subject": row["subject"] or "未命名任务",
                "duration_minutes": row["duration_minutes"],
                "tree_type": row["tree_type"] or "🌲",
                "status": row["status"],
                "created_at": row["created_at"]
            })
        return {"success": True, "history": history}


@app.post("/api/todo/add")
def add_todo(payload: TodoAddRequest) -> dict[str, Any]:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    scheduled_date = normalize_todo_date(payload.scheduled_date)
    scheduled_time = normalize_todo_time(payload.scheduled_time)
    requested_status = str(payload.status or "todo").strip().lower().replace("-", "_")
    status = "done" if requested_status == "done" else normalize_todo_status(requested_status)
    accent = normalize_todo_accent(payload.accent)
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.username)
        cursor = conn.execute(
            """
            INSERT INTO Todo_Tasks
              (username, content, scheduled_date, scheduled_time, status, category, accent, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.username,
                content,
                scheduled_date,
                scheduled_time,
                status,
                str(payload.category or "").strip(),
                accent,
                1 if status == "done" else 0,
            ),
        )
        task_id = cursor.lastrowid
        row = conn.execute(
            """
            SELECT id, content, is_completed, created_at, ai_score, ai_feedback,
                   scheduled_date, scheduled_time, status, category, accent
            FROM Todo_Tasks WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        conn.commit()
    return {"success": True, "task_id": task_id, "task": todo_row_to_dict(row)}


@app.get("/api/todo/{username}")
def list_todo(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            """
            SELECT id, content, is_completed, created_at, ai_score, ai_feedback,
                   scheduled_date, scheduled_time, status, category, accent
            FROM Todo_Tasks
            WHERE username = ?
            ORDER BY is_completed ASC, COALESCE(NULLIF(scheduled_date, ''), created_at) ASC, id DESC
            """,
            (username,),
        ).fetchall()
    return {"success": True, "tasks": [todo_row_to_dict(row) for row in rows]}


@app.post("/api/todo/toggle")
def toggle_todo(payload: TodoActionRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT is_completed FROM Todo_Tasks WHERE id = ? AND username = ?",
            (payload.task_id, payload.username),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")

        next_completed = 0 if int(row["is_completed"] or 0) == 1 else 1
        conn.execute(
            "UPDATE Todo_Tasks SET is_completed = ?, status = ? WHERE id = ? AND username = ?",
            (next_completed, "done" if next_completed else "todo", payload.task_id, payload.username),
        )
        updated = conn.execute(
            """
            SELECT id, content, is_completed, created_at, ai_score, ai_feedback,
                   scheduled_date, scheduled_time, status, category, accent
            FROM Todo_Tasks WHERE id = ? AND username = ?
            """,
            (payload.task_id, payload.username),
        ).fetchone()
        conn.commit()
    return {"success": True, "task": todo_row_to_dict(updated)}


@app.post("/api/todo/delete")
def delete_todo(payload: TodoActionRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM Todo_Tasks WHERE id = ? AND username = ?", (payload.task_id, payload.username))
        conn.commit()
    return {"success": True}


@app.post("/api/tasks/{task_id}/score")
def score_task(task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    username = payload.get("username", "")
    proof_url = payload.get("proof_url", "")
    with closing(get_conn()) as conn:
        conn.execute("UPDATE Todo_Tasks SET ai_score = 100, proof_url = ?, ai_feedback = '已记录提交凭证。', score_updated_at = CURRENT_TIMESTAMP WHERE id = ? AND username = ?", (proof_url, task_id, username))
        add_exp(conn, username, 15, "task_score")
        conn.commit()
    return {"success": True, "score": 100}


@app.post("/api/phone-usage/analyze-screenshot")
async def analyze_phone_screenshot(file: UploadFile = File(...), username: str = Form("guest")) -> dict[str, Any]:
    _ = await file.read()
    return {"success": True, "username": username, "total_minutes": 0, "top_category": "学习", "apps": [{"name": "等待手动校正", "minutes": 0}], "summary": "当前环境未启用 OCR，已切换到手动校正模式。"}


@app.post("/api/phone-usage/report")
def report_phone_usage(payload: PhoneUsageReportRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.username)
        conn.execute("INSERT INTO Phone_Usage (username, usage_minutes, category, notes, report_date) VALUES (?, ?, ?, ?, date('now', 'localtime'))", (payload.username, payload.usage_minutes, payload.category, payload.notes))
        conn.commit()
    return {"success": True, "message": "终端使用记录已保存"}


@app.get("/api/phone-usage/stats/{username}")
def phone_usage_stats(username: str, days: int = 7) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            """
            SELECT report_date, SUM(usage_minutes) AS usage_minutes
            FROM Phone_Usage
            WHERE username = ? AND report_date >= date('now', ?)
            GROUP BY report_date ORDER BY report_date
            """,
            (username, f"-{max(days - 1, 0)} day"),
        ).fetchall()
    return {"success": True, "daily_stats": [dict(row) for row in rows]}


@app.post("/api/ai/chat")
def ai_chat(payload: AIChatRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.username)
        conn.execute("INSERT INTO AI_Chats (username, role, content, conversation_id) VALUES (?, 'user', ?, ?)", (payload.username, payload.message, payload.conversation_id))
        reply = generate_ai_reply(conn, payload.username, payload.message)
        conn.execute("INSERT INTO AI_Chats (username, role, content, conversation_id) VALUES (?, 'assistant', ?, ?)", (payload.username, reply, payload.conversation_id))
        conn.commit()
    return {"success": True, "reply": reply}


@app.get("/api/ai/history/{username}")
def ai_history(username: str, conversation_id: str = "") -> dict[str, Any]:
    query = "SELECT role, content, created_at FROM AI_Chats WHERE username = ?"
    params: list[Any] = [username]
    if conversation_id:
        query += " AND conversation_id = ?"
        params.append(conversation_id)
    query += " ORDER BY id ASC"
    with closing(get_conn()) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    messages = [dict(row) for row in rows]
    return {"success": True, "messages": messages, "history": messages}


@app.delete("/api/ai/history/{username}")
def clear_ai_history(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM AI_Chats WHERE username = ?", (username,))
        conn.commit()
    return {"success": True}


@app.get("/api/ai/suggestions/{username}")
def ai_suggestions(username: str) -> dict[str, Any]:
    return {"success": True, "suggestions": ["帮我安排今晚 90 分钟学习节奏", "根据最近状态给我一份提分建议", "我容易分心，给我一个 25 分钟执行清单"]}


@app.get("/api/friends/{username}")
def list_friends(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, user_username, friend_username, status, created_at FROM Friendships WHERE user_username = ? OR friend_username = ? ORDER BY id DESC", (username, username)).fetchall()
    normalized = []
    for row in rows:
        other = row["friend_username"] if row["user_username"] == username else row["user_username"]
        normalized.append({"id": row["id"], "user_username": row["user_username"], "friend_username": other, "status": row["status"], "created_at": row["created_at"]})
    return {"success": True, "friends": normalized}


@app.post("/api/friends/request")
def request_friend(payload: FriendRequestPayload) -> dict[str, Any]:
    if payload.user_username == payload.friend_username:
        raise HTTPException(status_code=400, detail="不能添加自己为好友")
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.user_username)
        if not conn.execute("SELECT username FROM Users WHERE username = ?", (payload.friend_username,)).fetchone():
            raise HTTPException(status_code=404, detail="目标用户不存在")
        exists = conn.execute("SELECT id FROM Friendships WHERE (user_username = ? AND friend_username = ?) OR (user_username = ? AND friend_username = ?)", (payload.user_username, payload.friend_username, payload.friend_username, payload.user_username)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="好友关系已存在")
        conn.execute("INSERT INTO Friendships (user_username, friend_username, status) VALUES (?, ?, 'pending')", (payload.user_username, payload.friend_username))
        conn.commit()
    return {"success": True}


@app.post("/api/friends/respond")
def respond_friend(payload: FriendRespondPayload) -> dict[str, Any]:
    status = payload.status if payload.status in {"accepted", "rejected"} else "rejected"
    with closing(get_conn()) as conn:
        conn.execute("UPDATE Friendships SET status = ? WHERE id = ?", (status, payload.friendship_id))
        conn.commit()
    return {"success": True}


@app.delete("/api/friends")
def delete_friend(payload: FriendDeletePayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM Friendships WHERE (user_username = ? AND friend_username = ?) OR (user_username = ? AND friend_username = ?)", (payload.user_username, payload.friend_username, payload.friend_username, payload.user_username))
        conn.commit()
    return {"success": True}


@app.get("/api/user/{username}/avatar")
def get_avatar(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        row = conn.execute("SELECT avatar, nickname FROM Users WHERE username = ?", (username,)).fetchone()
    return {
        "success": True,
        "avatar": row["avatar"] if row and row["avatar"] else DEFAULT_AVATAR,
        "nickname": row["nickname"] if row and row["nickname"] else username
    }


@app.post("/api/user/{username}/avatar")
def set_avatar(username: str, payload: AvatarPayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        conn.execute("UPDATE Users SET avatar = ? WHERE username = ?", (payload.avatar or DEFAULT_AVATAR, username))
        conn.commit()
    return {"success": True, "avatar": payload.avatar or DEFAULT_AVATAR}


class ProfilePayload(BaseModel):
    nickname: str = ""
    bio: str = ""


@app.get("/api/user/{username}/profile")
def get_profile(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        row = conn.execute("SELECT nickname, bio, avatar FROM Users WHERE username = ?", (username,)).fetchone()
    return {
        "success": True,
        "nickname": row["nickname"] or username if row else username,
        "bio": row["bio"] or "" if row else "",
        "avatar": row["avatar"] or DEFAULT_AVATAR if row else DEFAULT_AVATAR
    }


@app.post("/api/user/{username}/profile")
def update_profile(username: str, payload: ProfilePayload) -> dict[str, Any]:
    nickname = (payload.nickname or username).strip()[:20]
    bio = (payload.bio or "").strip()[:200]
    with closing(get_conn()) as conn:
        ensure_user(conn, username)
        conn.execute("UPDATE Users SET nickname = ?, bio = ? WHERE username = ?", (nickname, bio, username))
        conn.commit()
    return {"success": True, "nickname": nickname, "bio": bio}


@app.get("/api/achievements")
def get_achievements() -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT * FROM Achievements ORDER BY id").fetchall()
    return {"success": True, "achievements": [dict(row) for row in rows]}


@app.get("/api/achievements/{username}")
def get_user_achievements(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        refresh_user_achievements(conn, username)
        rows = conn.execute("SELECT * FROM Achievements ORDER BY id").fetchall()
        unlocked_rows = conn.execute("SELECT ua.achievement_id, a.code, ua.unlocked_at FROM User_Achievements ua JOIN Achievements a ON a.id = ua.achievement_id WHERE ua.username = ? ORDER BY ua.id", (username,)).fetchall()
        conn.execute("UPDATE User_Growth SET achievements_count = ? WHERE username = ?", (len(unlocked_rows), username))
        conn.commit()
    unlocked = [dict(row) for row in unlocked_rows]
    unlocked_ids = {row["achievement_id"] for row in unlocked_rows}
    achievements = []
    for row in rows:
        item = dict(row)
        item["unlocked"] = row["id"] in unlocked_ids
        achievements.append(item)
    return {"success": True, "achievements": achievements, "unlocked": unlocked}


@app.post("/api/achievements/check")
def check_achievement(payload: AchievementCheckPayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        refresh_user_achievements(conn, payload.username)
        unlocked = conn.execute("SELECT a.code FROM User_Achievements ua JOIN Achievements a ON a.id = ua.achievement_id WHERE ua.username = ? AND a.code = ?", (payload.username, payload.achievement_code)).fetchone()
        conn.commit()
    return {"success": True, "unlocked": bool(unlocked)}


@app.get("/api/stats/{username}")
def get_stats(username: str, period: str = "week") -> dict[str, Any]:
    days = period_day_count(period)
    with closing(get_conn()) as conn:
        daily_stats = focus_daily_stats(conn, username, days)
        growth = build_growth_payload(conn, username)
        total_tasks = conn.execute("SELECT COUNT(*) AS count FROM Todo_Tasks WHERE username = ? AND is_completed = 1 AND created_at >= datetime('now', ?)", (username, f"-{max(days - 1, 0)} day")).fetchone()["count"]
        avg_usage_row = conn.execute("SELECT AVG(usage_minutes) AS avg_usage FROM Phone_Usage WHERE username = ? AND report_date >= date('now', ?)", (username, f"-{max(days - 1, 0)} day")).fetchone()
        avg_usage = float(avg_usage_row["avg_usage"] or 0)
        summary = {
            "totalFocusHours": round(sum(day["focus_minutes"] for day in daily_stats) / 60.0, 1),
            "totalTasks": int(total_tasks or 0),
            "totalExp": growth["exp"],
            "avgDiscipline": round(max(0.0, min(100.0, 100.0 - avg_usage / 2.5)) if avg_usage else growth["discipline_score"], 1),
            "streakDays": growth["streak_days"],
        }
    return {"success": True, "daily_stats": daily_stats, "summary": summary}


@app.get("/api/stats/{username}/focus-distribution")
def get_focus_distribution(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT COALESCE(subject, '专注') AS subject, SUM(duration_minutes) AS minutes FROM Focus_Sessions WHERE username = ? AND status = 'completed' GROUP BY COALESCE(subject, '专注') ORDER BY minutes DESC", (username,)).fetchall()
    return {"success": True, "distribution": [dict(row) for row in rows]}


@app.get("/api/stats/{username}/growth-curve")
def get_growth_curve(username: str, days: int = 30) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        daily = focus_daily_stats(conn, username, min(max(days, 1), 365))
    running = 0
    points = []
    for day in daily:
        running += int(day["focus_minutes"])
        points.append({"date": day["stat_date"], "value": running})
    return {"success": True, "points": points}


@app.get("/api/leaderboard")
def get_leaderboard(type: str = "focus", category: str = "", period: str = "weekly", username: str = "") -> dict[str, Any]:
    metric = category if category in {"exp", "focus", "streak"} else type
    if metric not in {"exp", "focus", "streak"}:
        metric = "focus"
    with closing(get_conn()) as conn:
        rows = leaderboard_rows(conn, metric)
    rankings = []
    for row in rows:
        rankings.append({"username": row["username"], "score": int(row["score"] or 0), "total_focus_minutes": int(row["score"] or 0) if metric == "focus" else 0})
    user_rank = None
    if username:
        for index, row in enumerate(rankings, start=1):
            if row["username"] == username:
                user_rank = {"rank": index, "score": row["score"]}
                break
    return {"success": True, "rankings": rankings, "leaderboard": rankings, "user_rank": user_rank}


@app.get("/api/exams")
def list_exams() -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT exam_code, title, config_json, audio_file, pdf_file, time_limit FROM Exams ORDER BY exam_code").fetchall()
    exams = []
    for row in rows:
        item = dict(row)
        item["config_json"] = safe_json_loads(item.get("config_json"), {"sections": []})
        exams.append(item)
    return {"success": True, "exams": exams}


@app.post("/api/submit_exam")
def submit_exam(payload: ExamSubmitRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        exam = conn.execute("SELECT title, config_json, answer_key_json, time_limit FROM Exams WHERE exam_code = ?", (payload.exam_code,)).fetchone()
        if not exam:
            raise HTTPException(status_code=404, detail="试卷不存在")
        answer_key = safe_json_loads(exam["answer_key_json"], {})
        config = safe_json_loads(exam["config_json"], {"sections": []})
        mistakes = []
        total_questions = 0
        correct_count = 0
        for section in config.get("sections", []):
            for question in section.get("questions", []):
                qid = question.get("id")
                if not qid:
                    continue
                total_questions += 1
                expected = str(answer_key.get(qid, "")).strip().lower()
                user_answer = str(payload.answers.get(qid, "")).strip().lower()
                if expected and user_answer == expected:
                    correct_count += 1
                else:
                    mistakes.append({"question": question.get("question", qid), "user": payload.answers.get(qid, ""), "correct": answer_key.get(qid, ""), "analysis": "这题主要检查基础语法和词汇搭配，建议把正确答案放回句子里再读一遍。"})
        score = round((correct_count / total_questions) * 100, 1) if total_questions else 0.0
        feedback = "整体基础稳定，建议优先复盘错题中的高频语法点。"
        cursor = conn.execute(
            "INSERT INTO Exam_Submissions (exam_code, room_id, username, objective_score, attempted_score, time_used, subjective_answers, mistakes, subjective_score, teacher_feedback) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (payload.exam_code, payload.room_id, payload.username, score, float(total_questions), payload.time_used, json.dumps(payload.answers, ensure_ascii=False), json.dumps(mistakes, ensure_ascii=False), feedback),
        )
        exp_gained = max(10, int(score // 5))
        add_exp(conn, payload.username, exp_gained, "exam_submit")
        refresh_user_achievements(conn, payload.username)
        conn.commit()
    return {"success": True, "submission_id": cursor.lastrowid, "score": score, "objective_score": score, "total_questions": total_questions, "mistakes": mistakes, "has_subjective": False, "exp_gained": exp_gained}


@app.get("/api/exam/grading_status/{submission_id}")
def exam_grading_status(submission_id: int) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT subjective_score, teacher_feedback FROM Exam_Submissions WHERE id = ?", (submission_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return {"success": True, "status": "completed", "subjective_score": float(row["subjective_score"] or 0), "feedback": row["teacher_feedback"] or ""}


@app.post("/api/exam/ai_analysis")
def exam_ai_analysis(payload: ExamAIAnalysisRequest) -> dict[str, Any]:
    analysis = f"题目：{payload.question}\n你的答案：{payload.user_answer or '未作答'}\n正确答案：{payload.correct_answer}\n建议：先定位关键词，再检查时态、主谓一致和固定搭配。"
    return {"success": True, "analysis": analysis}


@app.get("/api/unified-shop/balance/{username}")
def unified_shop_balance(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        growth = build_growth_payload(conn, username)
    return {"success": True, "coins": growth["coins"], "diamonds": growth["diamonds"], "sunshine": growth["sunshine"]}


@app.get("/api/unified-shop/items")
def unified_shop_items(username: str = "", category: str = "", dimension: str = "") -> dict[str, Any]:
    with closing(get_conn()) as conn:
        sync_runtime_shop_catalog(conn)
        query = "SELECT * FROM Unified_Shop_Items WHERE is_available = 1"
        params: list[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if dimension:
            query += " AND COALESCE(dimension, '3D') = ?"
            params.append(normalize_dimension(dimension))
        query += " ORDER BY sort_order ASC, id ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
        items = [enrich_shop_item(conn, row, username) for row in rows]
    return {"success": True, "items": items}


@app.get("/api/unified-shop/items/{item_id}")
def unified_shop_item_detail(item_id: int, username: str = "") -> dict[str, Any]:
    with closing(get_conn()) as conn:
        sync_runtime_shop_catalog(conn)
        row = conn.execute("SELECT * FROM Unified_Shop_Items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="商品不存在")
        item = enrich_shop_item(conn, row, username)
    return {"success": True, "item": item}


@app.post("/api/unified-shop/buy")
def unified_shop_buy(payload: UnifiedShopBuyRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        sync_runtime_shop_catalog(conn)
        ensure_user(conn, payload.username)
        item = conn.execute("SELECT id, name, name_cn, category, price_sunshine, price_coins, rarity FROM Unified_Shop_Items WHERE id = ? AND is_available = 1", (payload.item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="商品不存在")
        spend_currency(conn, payload.username, coins=int(item["price_coins"] or 0) * payload.quantity, diamonds=int(item["price_sunshine"] or 0) * payload.quantity, source=f"buy:{payload.item_id}")
        for _ in range(payload.quantity):
            conn.execute("INSERT INTO User_Inventory (username, item_id, status) VALUES (?, ?, 'owned')", (payload.username, payload.item_id))
        conn.commit()
    return {"success": True, "message": f"已购买 {item['name_cn'] or item['name']}，现在可以直接放置。"}


@app.get("/api/unified-shop/inventory/{username}")
def unified_shop_inventory(username: str, category: Optional[str] = None, dimension: Optional[str] = None) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        sync_runtime_shop_catalog(conn)
        query = "SELECT usi.*, ui.status, ui.id AS inventory_id FROM User_Inventory ui JOIN Unified_Shop_Items usi ON usi.id = ui.item_id WHERE ui.username = ?"
        params: list[Any] = [username]
        if category:
            query += " AND usi.category = ?"
            params.append(category)
        if dimension:
            query += " AND COALESCE(usi.dimension, '3D') = ?"
            params.append(normalize_dimension(dimension))
        query += " ORDER BY ui.id DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        items = [enrich_shop_item(conn, row, username) | {"status": row["status"], "inventory_id": row["inventory_id"]} for row in rows]
    return {"success": True, "items": items}


@app.get("/api/unified-shop/favorites/{username}")
def unified_shop_favorites(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT usi.* FROM User_Shop_Favorites usf JOIN Unified_Shop_Items usi ON usi.id = usf.item_id WHERE usf.username = ? ORDER BY usf.id DESC", (username,)).fetchall()
        items = [enrich_shop_item(conn, row, username) for row in rows]
    return {"success": True, "items": items}


@app.post("/api/unified-shop/favorites")
def add_favorite(payload: FavoritePayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        exists = conn.execute("SELECT id FROM User_Shop_Favorites WHERE username = ? AND item_id = ?", (payload.username, payload.item_id)).fetchone()
        if not exists:
            conn.execute("INSERT INTO User_Shop_Favorites (username, item_id) VALUES (?, ?)", (payload.username, payload.item_id))
            conn.commit()
    return {"success": True}


@app.delete("/api/unified-shop/favorites")
def remove_favorite(payload: FavoritePayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM User_Shop_Favorites WHERE username = ? AND item_id = ?", (payload.username, payload.item_id))
        conn.commit()
    return {"success": True}


@app.post("/api/unified-shop/place")
def unified_shop_place(payload: UnifiedShopPlaceRequest) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.username)
        item = conn.execute("SELECT * FROM Unified_Shop_Items WHERE id = ?", (payload.item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="商品不存在")
        placement_type = placement_type_for_category(item["category"])
        item_dimension = normalize_dimension(item["dimension"] if "dimension" in item.keys() else "3D")
        target_dimension = normalize_dimension(payload.dimension or item_dimension)
        if placement_type not in {"building", "greenery"}:
            raise HTTPException(status_code=400, detail="该物件当前不支持在城市中放置")
        if target_dimension != item_dimension:
            raise HTTPException(status_code=400, detail="鐗╀欢缁村害涓庡綋鍓嶉儴缃插尯鍩熶笉鍖归厤")
        if target_dimension == "3D" and payload.map_id == "city":
            if not payload.slot_id:
                raise HTTPException(status_code=400, detail="城市放置必须指定槽位")
            slot = city_slot_index().get(payload.slot_id)
            if not slot or slot.get("enabled", True) is False:
                raise HTTPException(status_code=400, detail="槽位不存在")
            if slot.get("slot_type") != placement_type:
                raise HTTPException(status_code=400, detail="物件类型与槽位不匹配")
            occupied = conn.execute("SELECT id FROM Island_Infrastructure WHERE username = ? AND map_id = ? AND slot_id = ?", (payload.username, payload.map_id, payload.slot_id)).fetchone()
            if occupied:
                raise HTTPException(status_code=400, detail="该槽位已被占用")
            pos_x = float(slot.get("x", 0))
            pos_y = float(slot.get("y", 1.7))
            pos_z = float(slot.get("z", 0))
            rotation_y = float(slot.get("rotation_y", 0))
            grid_x = None
            grid_y = None
            map_id = payload.map_id or "city"
            slot_id = payload.slot_id
        elif target_dimension == "2D":
            grid_x = payload.grid_x
            grid_y = payload.grid_y
            if grid_x is None or grid_y is None:
                raise HTTPException(status_code=400, detail="2D 閮ㄧ讲蹇呴』鎻愪緵缃戞牸鍧愭爣")
            map_id = payload.map_id or "isometric-city"
            slot_id = None
            footprint_w = max(1, int(item["grid_width"] or 1))
            footprint_h = max(1, int(item["grid_height"] or 1))
            conflict = find_2d_placement_conflict(conn, payload.username, map_id, int(grid_x), int(grid_y), footprint_w, footprint_h)
            if conflict:
                raise HTTPException(status_code=400, detail=f"{conflict['name_cn'] or conflict['name']} 宸插崰鐢ㄨ繖鐗囩綉鏍?")
            pos_x = float(grid_x)
            pos_y = float(payload.position_y or 0)
            pos_z = float(grid_y)
            rotation_y = float(payload.rotation_y or 0)
        else:
            pos_x = payload.position_x
            pos_y = payload.position_y
            pos_z = payload.position_z
            rotation_y = payload.rotation_y
            grid_x = None
            grid_y = None
            map_id = payload.map_id or "city"
            slot_id = payload.slot_id
        inventory_row = conn.execute("SELECT id FROM User_Inventory WHERE username = ? AND item_id = ? AND status = 'owned' ORDER BY id LIMIT 1", (payload.username, payload.item_id)).fetchone()
        if not inventory_row:
            raise HTTPException(status_code=400, detail="请先购买该单元")
        conn.execute("UPDATE User_Inventory SET status = 'placed', placed_x = ?, placed_z = ? WHERE id = ?", (pos_x, pos_z, inventory_row["id"]))
        cursor = conn.execute(
            """
            INSERT INTO Island_Infrastructure
            (username, item_id, position_x, position_y, position_z, rotation_y, scale, map_id, slot_id, rotation, dimension, grid_x, grid_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (payload.username, payload.item_id, pos_x, pos_y, pos_z, rotation_y, payload.scale, map_id, slot_id, target_dimension, grid_x, grid_y),
        )
        refresh_user_achievements(conn, payload.username)
        conn.commit()
        placed_row = conn.execute(
            """
            SELECT ii.id, ii.username, ii.item_id, ii.position_x, ii.position_y, ii.position_z, ii.rotation_y, ii.scale,
                   ii.map_id, ii.slot_id, ii.dimension, ii.grid_x, ii.grid_y,
                   usi.item_code, usi.name, usi.name_cn, usi.model_path, usi.icon, usi.category,
                   usi.preview_path, usi.sprite_path, usi.grid_width, usi.grid_height
            FROM Island_Infrastructure ii JOIN Unified_Shop_Items usi ON usi.id = ii.item_id WHERE ii.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        placed_item = enrich_shop_item(conn, placed_row, payload.username)
        placed_item.update({
            "id": placed_row["id"],
            "username": placed_row["username"],
            "item_id": placed_row["item_id"],
            "position_x": placed_row["position_x"],
            "position_y": placed_row["position_y"],
            "position_z": placed_row["position_z"],
            "rotation_y": placed_row["rotation_y"],
            "scale": placed_row["scale"],
            "map_id": placed_row["map_id"],
            "slot_id": placed_row["slot_id"],
            "dimension": normalize_dimension(placed_row["dimension"]),
            "grid_x": placed_row["grid_x"],
            "grid_y": placed_row["grid_y"],
        })
    return {"success": True, "placed_item": placed_item}


@app.get("/api/unified-shop/placed/{username}")
def unified_shop_placed(username: str, dimension: str = "") -> dict[str, Any]:
    with closing(get_conn()) as conn:
        query = """
            SELECT ii.id, ii.username, ii.item_id, ii.position_x, ii.position_y, ii.position_z, ii.rotation_y, ii.scale,
                   ii.map_id, ii.slot_id, ii.dimension, ii.grid_x, ii.grid_y,
                   usi.item_code, usi.name, usi.name_cn, usi.model_path, usi.icon, usi.category,
                   usi.preview_path, usi.sprite_path, usi.grid_width, usi.grid_height
            FROM Island_Infrastructure ii JOIN Unified_Shop_Items usi ON usi.id = ii.item_id
            WHERE ii.username = ?
        """
        params: list[Any] = [username]
        if dimension:
            query += " AND COALESCE(ii.dimension, '3D') = ?"
            params.append(normalize_dimension(dimension))
        query += " ORDER BY ii.id ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
    items = []
    with closing(get_conn()) as conn:
        for row in rows:
            item = enrich_shop_item(conn, row, username)
            item.update({
                "id": row["id"],
                "username": row["username"],
                "item_id": row["item_id"],
                "position_x": row["position_x"],
                "position_y": row["position_y"],
                "position_z": row["position_z"],
                "rotation_y": row["rotation_y"],
                "scale": row["scale"],
                "map_id": row["map_id"],
                "slot_id": row["slot_id"],
                "dimension": normalize_dimension(row["dimension"]),
                "grid_x": row["grid_x"],
                "grid_y": row["grid_y"],
            })
            items.append(item)
    return {"success": True, "items": items}


@app.delete("/api/unified-shop/placed/{placed_id}")
def unified_shop_remove_placed(placed_id: int, payload: RemovePlacedPayload = Body(...)) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT username, item_id FROM Island_Infrastructure WHERE id = ? AND username = ?", (placed_id, payload.username)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="摆件不存在")
        restore_item_to_owned(conn, payload.username, row["item_id"])
        conn.execute("DELETE FROM Island_Infrastructure WHERE id = ?", (placed_id,))
        conn.commit()
    return {"success": True}


@app.get("/api/greenhouse/list")
def list_greenhouses(is_public: bool = True) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            """
            SELECT g.*, (SELECT COUNT(*) FROM Greenhouse_Seats s WHERE s.room_id = g.id AND s.is_occupied = 1) AS current_users
            FROM Greenhouses g
            WHERE (? = 0) OR g.is_public = 1
            ORDER BY g.id DESC
            """,
            (1 if is_public else 0,),
        ).fetchall()
    return {"success": True, "greenhouses": [dict(row) for row in rows]}


@app.get("/api/greenhouse/{room_id}")
def get_greenhouse(room_id: int) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        snapshot = greenhouse_snapshot(conn, room_id)
    return {"success": True, **snapshot}


@app.post("/api/greenhouse/create")
def create_greenhouse(payload: GreenhouseCreatePayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        ensure_user(conn, payload.owner_username)
        room_code = secrets.token_hex(4).upper()
        cursor = conn.execute("INSERT INTO Greenhouses (room_code, name, description, owner_username, max_seats, is_public, password, theme) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (room_code, payload.name.strip(), payload.description.strip(), payload.owner_username, payload.max_seats, 1 if payload.is_public else 0, payload.password, payload.theme))
        ensure_greenhouse_seats(conn, cursor.lastrowid, payload.max_seats)
        conn.commit()
    return {"success": True, "room_id": cursor.lastrowid}


@app.get("/api/greenhouse/sunshine/{username}")
@app.get("/api/sunshine/{username}")
def get_greenhouse_sunshine(username: str) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        growth = build_growth_payload(conn, username)
    return {"success": True, "sunshine": growth["diamonds"]}


@app.get("/api/sunshine/history/{username}")
def sunshine_history(username: str, limit: int = 50) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT amount, transaction_type, source, description, created_at FROM Sunshine_Transactions WHERE username = ? ORDER BY id DESC LIMIT ?", (username, max(1, min(limit, 200)))).fetchall()
    return {"success": True, "history": [dict(row) for row in rows]}


@app.post("/api/greenhouse/{room_id}/join")
def join_greenhouse_path(room_id: int, payload: GreenhouseJoinPayload) -> dict[str, Any]:
    payload.room_id = room_id
    if payload.seat_index is None:
        payload.seat_index = 0
    return join_greenhouse(payload)


@app.post("/api/greenhouse/join")
def join_greenhouse(payload: GreenhouseJoinPayload) -> dict[str, Any]:
    if payload.room_id is None:
        raise HTTPException(status_code=400, detail="缺少房间编号")
    if payload.seat_index is None:
        raise HTTPException(status_code=400, detail="缺少座位编号")
    with closing(get_conn()) as conn:
        room = conn.execute("SELECT id, password FROM Greenhouses WHERE id = ?", (payload.room_id,)).fetchone()
        if not room:
            raise HTTPException(status_code=404, detail="房间不存在")
        if room["password"] and room["password"] != payload.password:
            raise HTTPException(status_code=403, detail="房间密码错误")
        ensure_user(conn, payload.username)
        seat_number = payload.seat_index + 1
        seat = conn.execute("SELECT id, is_occupied, current_user FROM Greenhouse_Seats WHERE room_id = ? AND seat_number = ?", (payload.room_id, seat_number)).fetchone()
        if not seat:
            raise HTTPException(status_code=404, detail="座位不存在")
        if seat["is_occupied"] and seat["current_user"] != payload.username:
            raise HTTPException(status_code=400, detail="该座位已被占用")
        conn.execute("UPDATE Greenhouse_Seats SET is_occupied = 0, current_user = '' WHERE room_id = ? AND current_user = ?", (payload.room_id, payload.username))
        conn.execute("UPDATE Greenhouse_Seats SET is_occupied = 1, current_user = ? WHERE id = ?", (payload.username, seat["id"]))
        conn.commit()
        snapshot = greenhouse_snapshot(conn, payload.room_id)
    return {"success": True, **snapshot}


@app.post("/api/greenhouse/leave")
async def leave_greenhouse(payload: GreenhouseLeavePayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        conn.execute("UPDATE Greenhouse_Seats SET is_occupied = 0, current_user = '' WHERE room_id = ? AND current_user = ?", (payload.room_id, payload.username))
        conn.execute("UPDATE Greenhouse_Sessions SET status = 'failed', end_time = CURRENT_TIMESTAMP WHERE room_id = ? AND username = ? AND status = 'growing'", (payload.room_id, payload.username))
        conn.commit()
    await broadcast_greenhouse_sync(payload.room_id)
    return {"success": True}


@app.post("/api/greenhouse/start")
async def start_greenhouse(payload: GreenhouseStartPayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        seat = conn.execute("SELECT id FROM Greenhouse_Seats WHERE room_id = ? AND current_user = ? AND is_occupied = 1", (payload.room_id, payload.username)).fetchone()
        if not seat:
            raise HTTPException(status_code=400, detail="请先入座")
        existing = conn.execute("SELECT id FROM Greenhouse_Sessions WHERE room_id = ? AND username = ? AND status = 'growing'", (payload.room_id, payload.username)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="你已经在专注中了")
        conn.execute("INSERT INTO Greenhouse_Sessions (room_id, username, seat_id, task_id, status, duration_minutes) VALUES (?, ?, ?, ?, 'growing', ?)", (payload.room_id, payload.username, seat["id"], payload.task_id, payload.duration))
        conn.commit()
    await broadcast_greenhouse_sync(payload.room_id)
    return {"success": True}


@app.post("/api/greenhouse/end")
async def end_greenhouse(payload: GreenhouseEndPayload) -> dict[str, Any]:
    with closing(get_conn()) as conn:
        session = conn.execute("SELECT id, seat_id, duration_minutes FROM Greenhouse_Sessions WHERE room_id = ? AND username = ? AND status = 'growing' ORDER BY id DESC LIMIT 1", (payload.room_id, payload.username)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="没有正在进行的协作专注")
        diamonds_earned = 0
        if payload.status == "completed":
            diamonds_earned = max(1, int(session["duration_minutes"] or 0) // 10)
            conn.execute("UPDATE Greenhouse_Sessions SET status = 'completed', end_time = CURRENT_TIMESTAMP, sunshine_earned = ? WHERE id = ?", (diamonds_earned, session["id"]))
            add_currency(conn, payload.username, diamonds=diamonds_earned, source="greenhouse_complete")
            add_exp(conn, payload.username, max(10, int(session["duration_minutes"] or 0) // 2), "greenhouse_complete")
        else:
            conn.execute("UPDATE Greenhouse_Sessions SET status = ?, end_time = CURRENT_TIMESTAMP WHERE id = ?", (payload.status, session["id"]))
        conn.execute("UPDATE Greenhouse_Seats SET is_occupied = 0, current_user = '' WHERE id = ?", (session["seat_id"],))
        conn.commit()
    await broadcast_greenhouse_sync(payload.room_id)
    return {"success": True, "diamonds_earned": diamonds_earned}


@app.post("/api/greenhouse/emoji")
async def greenhouse_emoji(payload: GreenhouseEmojiPayload) -> dict[str, Any]:
    await socket_manager.broadcast(payload.room_id, {"type": "emoji", "emoji": payload.emoji, "username": payload.username})
    return {"success": True}


# ===== 圈子功能 API =====
def get_friends_usernames(conn: sqlite3.Connection, username: str) -> set[str]:
    """获取用户的好友列表（双向已接受的好友关系）"""
    rows = conn.execute(
        """SELECT
            CASE WHEN user_username = ? THEN friend_username ELSE user_username END AS friend_name
        FROM Friendships
        WHERE (user_username = ? OR friend_username = ?) AND status = 'accepted'""",
        (username, username, username)
    ).fetchall()
    return {row["friend_name"] for row in rows}


@app.get("/api/circle/posts")
def get_circle_posts(username: str, filter_type: str = "all", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """获取圈子动态列表"""
    offset = max(0, (page - 1) * page_size)
    with closing(get_conn()) as conn:
        # 获取好友列表
        friends = get_friends_usernames(conn, username)

        # 构建查询条件
        if filter_type == "friends":
            # 只看好友动态
            if not friends:
                return {"success": True, "posts": [], "total": 0, "has_more": False}
            placeholders = ",".join(["?" for _ in friends])
            query = f"""
                SELECT p.*, u.avatar, (SELECT COUNT(*) FROM Post_Likes WHERE post_id = p.id) AS likes_count,
                       (SELECT COUNT(*) FROM Post_Comments WHERE post_id = p.id) AS comments_count,
                       EXISTS(SELECT 1 FROM Post_Likes WHERE post_id = p.id AND username = ?) AS is_liked
                FROM Posts p
                LEFT JOIN Users u ON p.username = u.username
                WHERE p.username IN ({placeholders}) OR p.visibility = 'public'
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, [username] + list(friends) + [page_size, offset]).fetchall()
        else:
            # 全部动态（好友 + 公开）
            query = """
                SELECT p.*, u.avatar, (SELECT COUNT(*) FROM Post_Likes WHERE post_id = p.id) AS likes_count,
                       (SELECT COUNT(*) FROM Post_Comments WHERE post_id = p.id) AS comments_count,
                       EXISTS(SELECT 1 FROM Post_Likes WHERE post_id = p.id AND username = ?) AS is_liked
                FROM Posts p
                LEFT JOIN Users u ON p.username = u.username
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, [username, page_size, offset]).fetchall()

        posts = []
        for row in rows:
            posts.append({
                "id": row["id"],
                "username": row["username"],
                "avatar": row["avatar"] or "👨‍🚀",
                "content": row["content"],
                "image_urls": json.loads(row["image_urls"] or "[]"),
                "visibility": row["visibility"],
                "likes_count": row["likes_count"],
                "comments_count": row["comments_count"],
                "is_liked": bool(row["is_liked"]),
                "created_at": row["created_at"]
            })

        return {"success": True, "posts": posts, "has_more": len(posts) == page_size}


@app.post("/api/circle/posts")
def create_circle_post(payload: PostCreatePayload) -> dict[str, Any]:
    """发布新动态"""
    content = payload.content.strip()
    if not content and not payload.image_urls:
        raise HTTPException(status_code=400, detail="动态内容不能为空")

    with closing(get_conn()) as conn:
        cursor = conn.execute(
            "INSERT INTO Posts (username, content, image_urls, visibility) VALUES (?, ?, ?, ?)",
            (payload.username, content, json.dumps(payload.image_urls), payload.visibility)
        )
        conn.commit()
        post_id = cursor.lastrowid

    return {"success": True, "post_id": post_id, "message": "动态发布成功"}


@app.delete("/api/circle/posts/{post_id}")
def delete_circle_post(post_id: int, username: str) -> dict[str, Any]:
    """删除动态"""
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT username FROM Posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="动态不存在")
        if row["username"] != username:
            raise HTTPException(status_code=403, detail="无权删除此动态")

        conn.execute("DELETE FROM Post_Likes WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM Post_Comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM Posts WHERE id = ?", (post_id,))
        conn.commit()

    return {"success": True, "message": "动态已删除"}


@app.post("/api/circle/posts/{post_id}/like")
def toggle_post_like(post_id: int, payload: PostLikePayload) -> dict[str, Any]:
    """点赞/取消点赞"""
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT id FROM Posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="动态不存在")

        existing = conn.execute(
            "SELECT id FROM Post_Likes WHERE post_id = ? AND username = ?",
            (post_id, payload.username)
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM Post_Likes WHERE id = ?", (existing["id"],))
            conn.commit()
            return {"success": True, "liked": False, "message": "已取消点赞"}
        else:
            conn.execute(
                "INSERT INTO Post_Likes (post_id, username) VALUES (?, ?)",
                (post_id, payload.username)
            )
            conn.commit()
            return {"success": True, "liked": True, "message": "点赞成功"}


@app.get("/api/circle/posts/{post_id}/comments")
def get_post_comments(post_id: int, page: int = 1, page_size: int = 50) -> dict[str, Any]:
    """获取评论列表"""
    offset = max(0, (page - 1) * page_size)
    with closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT pc.*, u.avatar FROM Post_Comments pc
               LEFT JOIN Users u ON pc.username = u.username
               WHERE pc.post_id = ?
               ORDER BY pc.created_at ASC
               LIMIT ? OFFSET ?""",
            (post_id, page_size, offset)
        ).fetchall()

        comments = [{
            "id": row["id"],
            "username": row["username"],
            "avatar": row["avatar"] or "👨‍🚀",
            "content": row["content"],
            "created_at": row["created_at"]
        } for row in rows]

    return {"success": True, "comments": comments}


@app.post("/api/circle/posts/{post_id}/comments")
def create_post_comment(post_id: int, payload: PostCommentPayload) -> dict[str, Any]:
    """发表评论"""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")

    with closing(get_conn()) as conn:
        row = conn.execute("SELECT id FROM Posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="动态不存在")

        cursor = conn.execute(
            "INSERT INTO Post_Comments (post_id, username, content) VALUES (?, ?, ?)",
            (post_id, payload.username, content)
        )
        conn.commit()
        comment_id = cursor.lastrowid

    return {"success": True, "comment_id": comment_id, "message": "评论发表成功"}


# ===== 圈子功能 API 结束 =====


@app.get("/api/pk/active/{username}")
def pk_active(username: str) -> dict[str, Any]:
    return {"success": True, "active": [], "pending": [], "history": []}


@app.post("/api/pk/create")
def pk_create(payload: PKCreatePayload) -> dict[str, Any]:
    return {"success": True, "message": f"已向 {payload.opponent} 发起 PK 挑战"}


@app.post("/api/pk/accept")
def pk_accept(payload: PKDecisionPayload) -> dict[str, Any]:
    return {"success": True}


@app.post("/api/pk/decline")
def pk_decline(payload: PKDecisionPayload) -> dict[str, Any]:
    return {"success": True}


# ── Arcade / Gomoku Backend ──────────────────────────────────────────
import asyncio
import random
import string

_arcade_rooms: dict[str, dict[str, Any]] = {}  # room_code -> room state
_arcade_ws_connections: dict[str, set[WebSocket]] = defaultdict(set)
_gomoku_games: dict[str, dict[str, Any]] = {}
_gomoku_ws_connections: dict[str, set[WebSocket]] = defaultdict(set)


def _generate_room_code(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class ArcadePlayPayload(BaseModel):
    username: str
    game: str


class ArcadeJoinPayload(BaseModel):
    room_code: str
    username: str


class GomokuCreatePayload(BaseModel):
    username: str


class GomokuJoinPayload(BaseModel):
    room_code: str
    username: str


class GomokuMovePayload(BaseModel):
    game_id: str
    username: str
    row: int
    col: int


class GomokuSurrenderPayload(BaseModel):
    game_id: str
    username: str


@app.post("/api/arcade/play")
def arcade_play(payload: ArcadePlayPayload) -> dict[str, Any]:
    code = _generate_room_code()
    _arcade_rooms[code] = {
        "room_code": code,
        "game": payload.game,
        "status": "waiting",
        "player_host": payload.username,
        "player_guest": None,
        "moves": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    return {"room_code": code, "status": "waiting"}


@app.post("/api/arcade/join")
def arcade_join(payload: ArcadeJoinPayload) -> dict[str, Any]:
    room = _arcade_rooms.get(payload.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room["status"] == "playing":
        raise HTTPException(status_code=400, detail="房间已满")
    room["player_guest"] = payload.username
    room["status"] = "playing"
    return {"room_code": payload.room_code, "status": "playing", "game": room["game"]}


@app.get("/api/arcade/room/{room_code}")
def arcade_room(room_code: str) -> dict[str, Any]:
    room = _arcade_rooms.get(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    return room


@app.websocket("/ws/arcade/{room_code}")
async def arcade_ws(websocket: WebSocket, room_code: str) -> None:
    await websocket.accept()
    room = _arcade_rooms.get(room_code)
    if not room:
        await websocket.send_json({"type": "error", "detail": "房间不存在"})
        await websocket.close()
        return

    _arcade_ws_connections[room_code].add(websocket)
    try:
        # Send initial sync
        await websocket.send_json({
            "type": "sync",
            "player_host": room["player_host"],
            "player_guest": room.get("player_guest"),
            "status": room["status"],
            "moves": room.get("moves", []),
        })
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type == "move":
                move_record = {"row": msg["row"], "col": msg["col"], "color": msg["color"], "username": msg.get("username", "")}
                room.setdefault("moves", []).append(move_record)
                # Broadcast move to all connections in room
                for ws_conn in list(_arcade_ws_connections.get(room_code, set())):
                    if ws_conn != websocket:
                        try:
                            await ws_conn.send_json({"type": "move", **move_record})
                        except Exception:
                            _arcade_ws_connections[room_code].discard(ws_conn)

            elif msg_type == "game_over":
                room["status"] = "finished"
                for ws_conn in list(_arcade_ws_connections.get(room_code, set())):
                    try:
                        await ws_conn.send_json({
                            "type": "game_over",
                            "winner_color": msg.get("winner_color"),
                            "winner_name": msg.get("winner_name"),
                        })
                    except Exception:
                        _arcade_ws_connections[room_code].discard(ws_conn)

    except WebSocketDisconnect:
        _arcade_ws_connections[room_code].discard(websocket)
    except Exception:
        _arcade_ws_connections[room_code].discard(websocket)


@app.post("/api/gomoku/create")
def gomoku_create(payload: GomokuCreatePayload) -> dict[str, Any]:
    game_id = _generate_room_code(8)
    _gomoku_games[game_id] = {
        "game_id": game_id,
        "room_code": game_id,
        "player_black": payload.username,
        "player_white": None,
        "status": "waiting",
        "moves": [],
        "winner": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    return {"game_id": game_id, "room_code": game_id}


@app.post("/api/gomoku/join")
def gomoku_join(payload: GomokuJoinPayload) -> dict[str, Any]:
    game = _gomoku_games.get(payload.room_code)
    if not game:
        raise HTTPException(status_code=404, detail="房间不存在")
    game["player_white"] = payload.username
    game["status"] = "playing"
    return {"game_id": game["game_id"], "room_code": game["room_code"]}


@app.get("/api/gomoku/{game_id}")
def gomoku_get(game_id: str) -> dict[str, Any]:
    game = _gomoku_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")
    return game


@app.post("/api/gomoku/move")
def gomoku_move(payload: GomokuMovePayload) -> dict[str, Any]:
    game = _gomoku_games.get(payload.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")
    game["moves"].append({"row": payload.row, "col": payload.col, "username": payload.username})
    return {"success": True}


@app.post("/api/gomoku/surrender")
def gomoku_surrender(payload: GomokuSurrenderPayload) -> dict[str, Any]:
    game = _gomoku_games.get(payload.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")
    game["status"] = "finished"
    return {"success": True}


@app.get("/api/gomoku/list")
def gomoku_list() -> list[dict[str, Any]]:
    return list(_gomoku_games.values())


@app.websocket("/ws/gomoku/{game_id}")
async def gomoku_ws(websocket: WebSocket, game_id: str) -> None:
    await websocket.accept()
    game = _gomoku_games.get(game_id)
    if not game:
        await websocket.send_json({"type": "error", "detail": "对局不存在"})
        await websocket.close()
        return

    _gomoku_ws_connections[game_id].add(websocket)
    try:
        await websocket.send_json({"type": "sync", **game})
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type == "move":
                move_record = {"row": msg["row"], "col": msg["col"], "color": msg.get("color", 1), "username": msg.get("username", "")}
                game["moves"].append(move_record)
                for ws_conn in list(_gomoku_ws_connections.get(game_id, set())):
                    if ws_conn != websocket:
                        try:
                            await ws_conn.send_json({"type": "move", **move_record})
                        except Exception:
                            _gomoku_ws_connections[game_id].discard(ws_conn)

            elif msg_type == "game_over":
                game["status"] = "finished"
                for ws_conn in list(_gomoku_ws_connections.get(game_id, set())):
                    try:
                        await ws_conn.send_json({
                            "type": "game_over",
                            "winner": msg.get("winner_color"),
                        })
                    except Exception:
                        _gomoku_ws_connections[game_id].discard(ws_conn)

    except WebSocketDisconnect:
        _gomoku_ws_connections[game_id].discard(websocket)
    except Exception:
        _gomoku_ws_connections[game_id].discard(websocket)


@app.websocket("/ws/greenhouse/{room_id}")
async def greenhouse_ws(websocket: WebSocket, room_id: int) -> None:
    await socket_manager.connect(room_id, websocket)
    try:
        with closing(get_conn()) as conn:
            snapshot = greenhouse_snapshot(conn, room_id)
        await websocket.send_json({"type": "sync", "seats": snapshot["seats"], "growing_users": snapshot["growing_users"]})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        socket_manager.disconnect(room_id, websocket)
    except Exception:
        socket_manager.disconnect(room_id, websocket)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if CITY_ASSET_ROOT.exists():
    app.mount("/city-assets", StaticFiles(directory=CITY_ASSET_ROOT), name="city-assets")
dist_assets = FRONTEND_DIST / "assets"
if dist_assets.exists():
    app.mount("/assets", StaticFiles(directory=dist_assets), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> Any:
    requested = FRONTEND_DIST / full_path
    if full_path and requested.exists() and requested.is_file():
        if requested.suffix.lower() == ".html":
            return FileResponse(requested, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            })
        return FileResponse(requested)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        })
    return JSONResponse({"detail": "Frontend build not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
