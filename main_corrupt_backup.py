
import os, sqlite3, json, shutil, random, time, subprocess, sys, socket
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
import fitz
import docx

DB_PATH = os.path.join(BASE_DIR, "focusport.db")
DB_PATH = os.path.join(BASE_DIR, DB_PATH)
FRONTEND_DIR = os.path.join(BASE_DIR, "focusport-frontend", "dist")  # Vue 鏋勫缓鐩綍
CITY_ASSET_ROOT = r"C:\Users\86153\Downloads\asset"
CITY_KIT_OBJ_DIRS = {
    "commercial": os.path.join(CITY_ASSET_ROOT, "kenney_city-kit-commercial_2.1", "Models", "OBJ format"),
    "industrial": os.path.join(CITY_ASSET_ROOT, "kenney_city-kit-industrial_1.0", "Models", "OBJ format"),
    "roads": os.path.join(CITY_ASSET_ROOT, "kenney_city-kit-roads", "Models", "OBJ format"),
    "suburban": os.path.join(CITY_ASSET_ROOT, "kenney_city-kit-suburban_20", "Models", "OBJ format"),
}
CITY_SURFACE_Y = 1.7
CITY_LAYOUT_FILE = os.path.join(BASE_DIR, "static", "city_layout_slots.json")
GRADE_BY_RARITY = {
    "common": "C",
    "rare": "B",
    "epic": "A",
    "legendary": "S",
}
GRADE_ORDER = {"C": 1, "B": 2, "A": 3, "S": 4}

app = FastAPI()
PYGAME_CITY_PROCESSES = {}

# ----------------- CORS 閰嶇疆 -----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- 闈欐€佹枃浠?-----------------
static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
if os.path.exists(CITY_ASSET_ROOT):
    app.mount("/city-assets", StaticFiles(directory=CITY_ASSET_ROOT), name="city-assets")


def load_city_layout_slots():
    """Internal helper docstring."""
    if not os.path.exists(CITY_LAYOUT_FILE):
        return []
    try:
        with open(CITY_LAYOUT_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            return payload.get("slots", [])
        if isinstance(payload, list):
            return payload
    except Exception as exc:
        print(f"Failed to load city layout: {exc}")
    return []


def city_slot_index():
    return {slot.get("slot_id"): slot for slot in load_city_layout_slots() if slot.get("slot_id")}


def normalize_grade(rarity: str) -> str:
    return GRADE_BY_RARITY.get((rarity or "").lower(), "C")


def grade_order_value(grade: str) -> int:
    return GRADE_ORDER.get(grade or "", 0)


def rarity_for_grade(grade: str) -> str:
    normalized = (grade or "").upper()
    for rarity, mapped_grade in GRADE_BY_RARITY.items():
        if mapped_grade == normalized:
            return rarity
    return ""


def placement_type_for_category(category: str) -> str:
    category = (category or "").lower()
    if category == "structures":
        return "building"
    if category in {"plants", "trees"}:
        return "greenery"
    return "unsupported"


def city_slot_capacities():
    capacities = {"building": 0, "greenery": 0}
    for slot in load_city_layout_slots():
        slot_type = slot.get("slot_type")
        if slot.get("enabled", True) and slot_type in capacities:
            capacities[slot_type] += 1
    return capacities


def pick_nearest_slot(candidates, pos_x: float, pos_z: float):
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda slot: ((slot.get("x", 0) - pos_x) ** 2) + ((slot.get("z", 0) - pos_z) ** 2)
    )


def restore_item_to_owned(conn, username: str, item_id: int):
    c = conn.cursor()
    c.execute("""
        SELECT id FROM User_Inventory
        WHERE username = ? AND item_id = ? AND status = 'placed'
        ORDER BY id ASC
        LIMIT 1
    """Internal helper docstring."""
    inventory_row = c.fetchone()
    if inventory_row:
        c.execute("UPDATE User_Inventory SET status = 'owned' WHERE id = ?", (inventory_row[0],))


def migrate_city_placements(conn, username: str = None):
    """Internal helper docstring."""
    slots = load_city_layout_slots()
    if not slots:
        return

    slot_lookup = city_slot_index()
    c = conn.cursor()
    params = []
    query = """
        SELECT ii.id, ii.username, ii.item_id, ii.position_x, ii.position_z, ii.rotation_y, ii.slot_id,
               usi.category
        FROM Island_Infrastructure ii
        JOIN Unified_Shop_Items usi ON ii.item_id = usi.id
        WHERE ii.map_id = 'city'
    """
    if username:
        query += " AND ii.username = ?"
        params.append(username)
    query += " ORDER BY ii.username ASC, ii.placed_at ASC, ii.id ASC"

    c.execute(query, params)
    rows = c.fetchall()
    rows_by_user = {}
    for row in rows:
        rows_by_user.setdefault(row[1], []).append(row)

    for current_user, user_rows in rows_by_user.items():
        occupied_slots = set()
        deferred_rows = []

        for row in user_rows:
            placed_id, _, item_id, pos_x, pos_z, _, slot_id, category = row
            placement_type = placement_type_for_category(category)
            slot = slot_lookup.get(slot_id)

            if (
                placement_type in {"building", "greenery"}
                and slot
                and slot.get("enabled", True)
                and slot.get("slot_type") == placement_type
                and slot_id not in occupied_slots
            ):
                occupied_slots.add(slot_id)
                c.execute("""
                    UPDATE Island_Infrastructure
                    SET position_x = ?, position_y = ?, position_z = ?, rotation_y = ?
                    WHERE id = ?
                """Internal helper docstring."""
                    slot.get("x", 0),
                    slot.get("y", CITY_SURFACE_Y),
                    slot.get("z", 0),
                    slot.get("rotation_y", 0),
                    placed_id,
                ))
            else:
                deferred_rows.append({
                    "placed_id": placed_id,
                    "username": current_user,
                    "item_id": item_id,
                    "position_x": pos_x or 0,
                    "position_z": pos_z or 0,
                    "placement_type": placement_type,
                })

        for row in deferred_rows:
            placement_type = row["placement_type"]
            if placement_type not in {"building", "greenery"}:
                c.execute("DELETE FROM Island_Infrastructure WHERE id = ?", (row["placed_id"],))
                restore_item_to_owned(conn, row["username"], row["item_id"])
                continue

            available_slots = [
                slot for slot in slots
                if slot.get("enabled", True)
                and slot.get("slot_type") == placement_type
                and slot.get("slot_id") not in occupied_slots
            ]
            chosen_slot = pick_nearest_slot(available_slots, row["position_x"], row["position_z"])

            if not chosen_slot:
                c.execute("DELETE FROM Island_Infrastructure WHERE id = ?", (row["placed_id"],))
                restore_item_to_owned(conn, row["username"], row["item_id"])
                continue

            occupied_slots.add(chosen_slot["slot_id"])
            c.execute("""
                UPDATE Island_Infrastructure
                SET slot_id = ?, position_x = ?, position_y = ?, position_z = ?, rotation_y = ?
                WHERE id = ?
            """Internal helper docstring."""
                chosen_slot["slot_id"],
                chosen_slot.get("x", 0),
                chosen_slot.get("y", CITY_SURFACE_Y),
                chosen_slot.get("z", 0),
                chosen_slot.get("rotation_y", 0),
                row["placed_id"],
            ))


def get_user_inventory_summary(conn, username: str):
    c = conn.cursor()
    c.execute("""
        SELECT item_id, status, COUNT(*)
        FROM User_Inventory
        WHERE username = ?
        GROUP BY item_id, status
    """Internal helper docstring."""
    item_counts = {}
    for item_id, status, count in c.fetchall():
        bucket = item_counts.setdefault(item_id, {"owned": 0, "placed": 0})
        if status == "placed":
            bucket["placed"] = count
        else:
            bucket["owned"] += count

    placed_by_type = {"building": 0, "greenery": 0}
    c.execute("""
        SELECT usi.category, COUNT(*)
        FROM Island_Infrastructure ii
        JOIN Unified_Shop_Items usi ON ii.item_id = usi.id
        WHERE ii.username = ? AND ii.map_id = 'city'
        GROUP BY usi.category
    """Internal helper docstring."""
    for category, count in c.fetchall():
        placement_type = placement_type_for_category(category)
        if placement_type in placed_by_type:
            placed_by_type[placement_type] += count

    return item_counts, placed_by_type


def enrich_shop_item(item: dict, item_counts=None, placed_by_type=None, slot_capacities=None):
    placement_type = placement_type_for_category(item.get("category"))
    grade = normalize_grade(item.get("rarity"))
    item["grade"] = grade
    item["grade_order"] = grade_order_value(grade)
    item["placement_type"] = placement_type

    if item_counts is not None:
        counts = item_counts.get(item.get("id"), {"owned": 0, "placed": 0})
        total_owned = counts.get("owned", 0) + counts.get("placed", 0)
        item["owned_count"] = total_owned
        item["placed_count"] = counts.get("placed", 0)
        item["available_to_place_count"] = counts.get("owned", 0)
    else:
        item["owned_count"] = 0
        item["placed_count"] = 0
        item["available_to_place_count"] = 0

    if slot_capacities is None:
        slot_capacities = city_slot_capacities()
    if placed_by_type is None:
        placed_by_type = {"building": 0, "greenery": 0}

    if placement_type in slot_capacities:
        item["slot_capacity_total"] = slot_capacities[placement_type]
        item["slot_capacity_remaining"] = max(
            slot_capacities[placement_type] - placed_by_type.get(placement_type, 0),
            0,
        )
    else:
        item["slot_capacity_total"] = 0
        item["slot_capacity_remaining"] = 0

    return item


def apply_preview_path(item: dict):
    model_path = (item.get("model_path") or "").lower()
    if model_path.endswith(".obj"):
        item["preview_path"] = ""
        return item

    code = item.get("item_code") or ""
    if not code:
        item["preview_path"] = ""
        return item

    if any(code.startswith(p) for p in ['bed', 'bathroom', 'chair', 'couch', 'desk', 'lamp', 'rug', 'shelf', 'tv', 'table', 'canoe', 'sign', 'bear', 'bedroom']):
        kit = 'furniture-kit'
        preview_code = ''.join(word.capitalize() for word in code.split('_'))
        item['preview_path'] = f"/previews/{kit}/{preview_code}_SE.png"
    elif any(code.startswith(p) for p in ['barrel', 'bottle', 'box', 'crate', 'suitcase', 'chest', 'cooler', 'pallet', 'raft', 'trash']):
        kit = 'survival-kit'
        item['preview_path'] = f"/previews/{kit}/{code.replace('_', '-')}.png"
    else:
        kit = 'nature-kit'
        item['preview_path'] = f"/previews/{kit}/{code}_SE.png"

    return item

# ----------------- 鍓嶇椤甸潰璺敱 -----------------
def serve_frontend_entry(file_path: str) -> FileResponse:
    """Internal helper docstring."""
    response = FileResponse(file_path)
    response.headers["Cache-Control"] = "no-store"
    return response


# Vue 鍓嶇棣栭〉
@app.get("/")
async def serve_vue_app():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    # Debug output removed to avoid encoding issues on Windows
    if os.path.exists(index_path):
        return serve_frontend_entry(index_path)
    return serve_frontend_entry(os.path.join(BASE_DIR, "index.html"))

# 鏃х増 admin 椤甸潰锛堜繚鐣欏吋瀹癸級
@app.get("/admin")
async def serve_admin():
    admin_path = os.path.join(BASE_DIR, "admin.html")
    if os.path.exists(admin_path):
        return serve_frontend_entry(admin_path)
    return serve_frontend_entry(os.path.join(FRONTEND_DIR, "index.html"))

# 娉ㄦ剰锛歏ue 鍓嶇璧勬簮鐨?catch-all 璺敱鏀惧湪鏂囦欢鏈熬锛岀‘淇?API 璺敱浼樺厛鍖归厤


def categorize_item(item_code):
    """Internal helper docstring."""
    item = (item_code or "").lower()

    def has_any(*parts):
        return any(part in item for part in parts)

    if item.startswith("tree"):
        rarity = "rare" if has_any("large", "tall", "oak", "palm") else "common"
        price = 100 if rarity == "rare" else 50
        return "trees", "tree", rarity, price, "??", item_code.replace("_", " ").title()

    if item.startswith(("flower", "bush", "mushroom", "plant")):
        return "plants", "plant", "common", 40, "??", item_code.replace("_", " ").title()

    if item.startswith(("crop", "wheat", "corn", "carrot")):
        return "crops", "crop", "common", 35, "??", item_code.replace("_", " ").title()

    if item.startswith(("rock", "stone")):
        rarity = "rare" if has_any("large", "tall") else "common"
        price = 80 if rarity == "rare" else 30
        return "rocks", "rock", rarity, price, "??", item_code.replace("_", " ").title()

    if item.startswith("cliff"):
        rarity = "rare" if has_any("waterfall", "cave", "large") else "common"
        price = 180 if rarity == "rare" else 75
        return "cliffs", "cliff", rarity, price, "??", item_code.replace("_", " ").title()

    if item.startswith("platform"):
        rarity = "rare" if has_any("large", "bridge", "island") else "common"
        price = 160 if rarity == "rare" else 75
        return "platforms", "platform", rarity, price, "??", item_code.replace("_", " ").title()

    if item.startswith("ground"):
        return "ground", "ground", "common", 60, "??", item_code.replace("_", " ").title()

    if item.startswith("path"):
        return "paths", "path", "common", 60, "???", item_code.replace("_", " ").title()

    if item.startswith(("house", "building", "fence")):
        rarity = "rare" if has_any("large", "tower", "castle", "gate") else "common"
        price = 180 if rarity == "rare" else 120
        return "structures", "structure", rarity, price, "??", item_code.replace("_", " ").title()

    if item.startswith(("bed", "chair", "table", "bench", "lamp", "desk")):
        return "furniture", "indoor", "common", 60, "??", item_code.replace("_", " ").title()

    return "decorations", "misc", "common", 25, "??", item_code.replace("_", " ").title()


def init_db():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS Users (username TEXT PRIMARY KEY, password TEXT)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS User_Growth (
            username TEXT PRIMARY KEY,
            exp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            discipline_score INTEGER DEFAULT 50,
            streak_days INTEGER DEFAULT 0,
            total_focus_minutes INTEGER DEFAULT 0,
            focus_energy INTEGER DEFAULT 0,
            sunshine INTEGER DEFAULT 0,
            diamonds INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Todo_Tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_score REAL DEFAULT 0,
            proof_url TEXT DEFAULT '',
            score_updated_at TIMESTAMP,
            ai_feedback TEXT DEFAULT ''
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS AI_Chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            conversation_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_username TEXT NOT NULL,
            friend_username TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            category TEXT,
            requirement TEXT,
            exp_reward INTEGER DEFAULT 10
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS User_Achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            achievement_id INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            rarity TEXT DEFAULT 'common',
            effect_type TEXT,
            effect_value REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS StudyRoom_Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            icon TEXT,
            model_path TEXT,
            price INTEGER DEFAULT 50,
            rarity TEXT DEFAULT 'common',
            description TEXT,
            effect TEXT,
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Sunshine_Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            source TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Unified_Shop_Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT UNIQUE,
            name TEXT NOT NULL,
            name_cn TEXT,
            category TEXT,
            subcategory TEXT,
            tags TEXT,
            model_path TEXT,
            icon TEXT,
            price_sunshine INTEGER DEFAULT 0,
            price_coins INTEGER DEFAULT 0,
            rarity TEXT DEFAULT 'common',
            description TEXT,
            is_available INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS User_Shop_Favorites (
            username TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (username, item_id)
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS User_Inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            status TEXT DEFAULT 'owned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS Island_Infrastructure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            position_x REAL DEFAULT 0,
            position_z REAL DEFAULT 0,
            rotation REAL DEFAULT 0,
            position_y REAL DEFAULT 0,
            rotation_y REAL DEFAULT 0,
            scale REAL DEFAULT 1.0,
            map_id TEXT DEFAULT 'city',
            slot_id TEXT,
            placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """Internal helper docstring."""

    c.execute("PRAGMA table_info(Island_Infrastructure)")
    infra_cols = [col[1] for col in c.fetchall()]
    if 'position_y' not in infra_cols:
        c.execute("ALTER TABLE Island_Infrastructure ADD COLUMN position_y REAL DEFAULT 0")
    if 'rotation_y' not in infra_cols:
        c.execute("ALTER TABLE Island_Infrastructure ADD COLUMN rotation_y REAL DEFAULT 0")
    if 'scale' not in infra_cols:
        c.execute("ALTER TABLE Island_Infrastructure ADD COLUMN scale REAL DEFAULT 1.0")
    if 'map_id' not in infra_cols:
        c.execute("ALTER TABLE Island_Infrastructure ADD COLUMN map_id TEXT DEFAULT 'city'")
    if 'slot_id' not in infra_cols:
        c.execute("ALTER TABLE Island_Infrastructure ADD COLUMN slot_id TEXT")

    c.execute("PRAGMA table_info(User_Growth)")
    growth_cols = [col[1] for col in c.fetchall()]
    growth_alters = {
        'focus_energy': "ALTER TABLE User_Growth ADD COLUMN focus_energy INTEGER DEFAULT 0",
        'sunshine': "ALTER TABLE User_Growth ADD COLUMN sunshine INTEGER DEFAULT 0",
        'diamonds': "ALTER TABLE User_Growth ADD COLUMN diamonds INTEGER DEFAULT 0",
        'coins': "ALTER TABLE User_Growth ADD COLUMN coins INTEGER DEFAULT 0",
        'discipline_score': "ALTER TABLE User_Growth ADD COLUMN discipline_score INTEGER DEFAULT 50",
        'streak_days': "ALTER TABLE User_Growth ADD COLUMN streak_days INTEGER DEFAULT 0",
        'total_focus_minutes': "ALTER TABLE User_Growth ADD COLUMN total_focus_minutes INTEGER DEFAULT 0",
        'level': "ALTER TABLE User_Growth ADD COLUMN level INTEGER DEFAULT 1",
        'exp': "ALTER TABLE User_Growth ADD COLUMN exp INTEGER DEFAULT 0",
    }
    for col, sql in growth_alters.items():
        if col not in growth_cols:
            c.execute(sql)

    conn.commit()
    conn.close()


init_db()


def import_kenney_nature_kit():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    models_dir = os.path.join(BASE_DIR, "focusport-frontend", "public", "models", "GLTF format")
    if not os.path.exists(models_dir):
        conn.close()
        return

    glb_files = [f for f in os.listdir(models_dir) if f.endswith('.glb')]
    new_items = 0

    for glb_file in glb_files:
        item_code = glb_file.replace('.glb', '')

        # 妫€鏌ユ槸鍚﹀凡瀛樺湪
        c.execute("SELECT id FROM Unified_Shop_Items WHERE item_code = ?", (item_code,))
        if c.fetchone():
            continue

        category, subcategory, rarity, price, icon, name_cn = categorize_item(item_code)
        c.execute('''INSERT INTO Unified_Shop_Items
            (item_code, name, name_cn, category, subcategory, tags, model_path, icon, price_sunshine, rarity, description, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (item_code, item_code.replace('_', ' ').title(), name_cn, category, subcategory,
             json.dumps([]), f"/models/GLTF format/{glb_file}", icon, price, rarity,
             f"{name_cn} - {category}", True))
        new_items += 1

    conn.commit()
    conn.close()
    if new_items > 0:
        print(f"宸插鍏?{new_items} 涓?Kenney Nature Kit 妯″瀷")


import_kenney_nature_kit()


def get_city_kit_item_meta(pack_name: str, model_name: str):
    """Internal helper docstring."""
    if pack_name == "roads":
        return {
            "category": "paths",
            "subcategory": "road",
            "rarity": "common",
            "price_sunshine": 0,
            "price_coins": 50,
            "icon": "馃洠锔?,
            "name_cn": f"閬撹矾 {model_name}",
            "description": "鍩庡競閬撹矾锛岀帺瀹跺彲鑷閾鸿",
        }

    if pack_name == "suburban" and (
        model_name.startswith("tree") or "planter" in model_name or model_name.startswith("hedge")
    ):
        return {
            "category": "plants",
            "subcategory": "plant",
            "rarity": "common",
            "price_sunshine": 0,
            "price_coins": 100,
            "icon": "馃尶",
            "name_cn": f"妞嶇墿 {model_name}",
            "description": "鍩庡競缁垮寲妞嶇墿",
        }

    if pack_name == "suburban" and model_name.startswith("building-type"):
        return {
            "category": "structures",
            "subcategory": "building_c",
            "rarity": "common",
            "price_sunshine": 0,
            "price_coins": 220,
            "icon": "馃彉锔?,
            "name_cn": f"C绾т綇瀹?{model_name}",
            "description": "閮婂尯浣忓畢寤虹瓚锛屽彲鐩存帴鐢ㄤ簬鍩庡競寤洪€?,
        }

    if pack_name == "industrial" and model_name.startswith("building"):
        return {
            "category": "structures",
            "subcategory": "building_b",
            "rarity": "common",
            "price_sunshine": 0,
            "price_coins": 300,
            "icon": "馃彮",
            "name_cn": f"B绾у缓绛?{model_name}",
            "description": "宸ヤ笟椋?B 绾у缓绛?,
        }

    if pack_name == "commercial" and model_name.startswith("building-skyscraper"):
        return {
            "category": "structures",
            "subcategory": "building_s",
            "rarity": "legendary",
            "price_sunshine": 10,
            "price_coins": 0,
            "icon": "馃拵",
            "name_cn": f"S绾у缓绛?{model_name}",
            "description": "楂樼█鏈夊害鎽╁ぉ妤煎缓绛?,
        }

    if pack_name == "commercial" and model_name.startswith("low-detail-building"):
        return {
            "category": "structures",
            "subcategory": "building_a",
            "rarity": "rare",
            "price_sunshine": 4,
            "price_coins": 0,
            "icon": "馃彚",
            "name_cn": f"A绾фゼ浣?{model_name}",
            "description": "鍟嗕笟鍖烘ゼ浣撳彉浣擄紝鍙洿鎺ョ敤浜庡煄甯傚缓閫?,
        }

    if pack_name == "commercial" and model_name.startswith("building"):
        return {
            "category": "structures",
            "subcategory": "building_a",
            "rarity": "common",
            "price_sunshine": 0,
            "price_coins": 500,
            "icon": "馃彚",
            "name_cn": f"A绾у缓绛?{model_name}",
            "description": "鍟嗕笟鍖?A 绾у缓绛?,
        }

    return None


def import_kenney_city_kit():
    """Internal helper docstring."""
    if not os.path.exists(CITY_ASSET_ROOT):
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_items = 0

    for pack_name, obj_dir in CITY_KIT_OBJ_DIRS.items():
        if not os.path.isdir(obj_dir):
            continue

        for obj_file in os.listdir(obj_dir):
            if not obj_file.lower().endswith(".obj"):
                continue

            model_name = obj_file[:-4]
            meta = get_city_kit_item_meta(pack_name, model_name)
            if not meta:
                continue

            item_code = f"city_{pack_name}_{model_name}".replace("-", "_")
            model_path = "/city-assets/" + os.path.relpath(
                os.path.join(obj_dir, obj_file), CITY_ASSET_ROOT
            ).replace(os.sep, "/")

            c.execute("SELECT id FROM Unified_Shop_Items WHERE item_code = ?", (item_code,))
            existing = c.fetchone()
            item_payload = (
                model_name.replace("-", " ").title(),
                meta["name_cn"],
                meta["category"],
                meta["subcategory"],
                json.dumps(["city-kit", pack_name], ensure_ascii=False),
                model_path,
                meta["icon"],
                meta["price_sunshine"],
                meta["price_coins"],
                meta["rarity"],
                meta["description"],
            )

            if existing:
                c.execute(
                    """Internal helper docstring."""
                       SET name = ?, name_cn = ?, category = ?, subcategory = ?, tags = ?,
                           model_path = ?, icon = ?, price_sunshine = ?, price_coins = ?,
                           rarity = ?, description = ?, is_available = 1
                       WHERE id = ?""",
                    item_payload + (existing[0],),
                )
            else:
                c.execute(
                    """Internal helper docstring."""
                       (item_code, name, name_cn, category, subcategory, tags, model_path,
                        icon, price_sunshine, price_coins, rarity, description, is_available, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)""",
                    (item_code,) + item_payload,
                )
                new_items += 1

    conn.commit()
    conn.close()
    if new_items > 0:
        print(f"宸插鍏?{new_items} 涓?Kenney City Kit OBJ 鍟嗗搧")


import_kenney_city_kit()


def keep_city_shop_only():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        DELETE FROM Island_Infrastructure
        WHERE map_id != 'city'
           OR item_id IN (
               SELECT id FROM Unified_Shop_Items
               WHERE item_code NOT LIKE 'city_%'
           )
    """Internal helper docstring."""

    c.execute("""
        DELETE FROM User_Inventory
        WHERE item_id IN (
            SELECT id FROM Unified_Shop_Items
            WHERE item_code NOT LIKE 'city_%'
        )
    """Internal helper docstring."""

    c.execute("""
        DELETE FROM User_Shop_Favorites
        WHERE item_id IN (
            SELECT id FROM Unified_Shop_Items
            WHERE item_code NOT LIKE 'city_%'
        )
    """Internal helper docstring."""

    c.execute("DELETE FROM Unified_Shop_Items WHERE item_code NOT LIKE 'city_%'")
    conn.commit()
    conn.close()
    print("宸叉竻绌烘棫鍟嗗簵鍐呭锛屼粎淇濈暀鍩庡競寤虹瓚/閬撹矾/妞嶇墿鍟嗗搧")


    keep_city_shop_only()


# --- 鏁版嵁妯″瀷 ---
class UserAuth(BaseModel): username: str; password: str


class ExamData(BaseModel): exam_code: str; room_id: str; username: str; time_used: int; answers: dict


class ExamDef(
    BaseModel): exam_code: str; title: str; config_json: str; answer_key_json: str; ai_prompt: str; audio_file: str; pdf_file: str; time_limit: int


class ParseRequest(BaseModel): api_key: str; pdf_filename: str; target_exam: str


class PostData(BaseModel): username: str; content: str; image_url: str = ""


class CommentData(BaseModel): post_id: int; username: str; content: str


class LikeData(BaseModel): post_id: int; username: str


# 鏂板妯″瀷
class TodoAdd(BaseModel): username: str; content: str


class TodoAction(BaseModel): task_id: int; username: str


class FocusStart(BaseModel): username: str; subject: str; duration: int; tree_type: str = "灏忔澗鏍?


class FocusEnd(BaseModel): session_id: int; username: str; status: str


# === 馃尡 鎵嬫満浣跨敤涓婃姤妯″瀷 ===
class PhoneUsageReport(BaseModel):
    username: str
    usage_minutes: int
    category: str = "濞变箰"
    notes: str = ""


# === 馃幆 浠诲姟AI璇勫垎妯″瀷 ===
class TaskScoreRequest(BaseModel):
    username: str
    proof_url: str = ""


# === 馃巵 閬撳叿浣跨敤妯″瀷 ===
class ItemUseRequest(BaseModel):
    username: str
    item_id: int


# === 馃尡 宀涘笨鎴愰暱绯荤粺妯″瀷 ===
class GrowthAddExp(BaseModel):
    username: str
    exp_amount: int
    source: str = "focus"  # focus, task, report


class GrowthCheckStreak(BaseModel):
    username: str


class CityLaunchRequest(BaseModel):
    username: str


# --- 涓婁紶鎺ュ彛 ---
@app.post("/api/admin/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(static_dir, file.filename)
    with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    return {"message": "涓婁紶鎴愬姛锛?, "url": file.filename}


# ============================================
# 馃巵 琛屼负濂栧姳閰嶇疆
# ============================================
REWARD_RULES = {
    'focus_complete': {
        'coins_base': 10,           # 鍩虹閲戝竵
        'coins_per_minute': 2,      # 姣忓垎閽熼澶栭噾甯?        'sunshine_base': 0,         # 鍩虹闃冲厜
        'sunshine_bonus_25min': 5,  # 25鍒嗛挓浠ヤ笂棰濆闃冲厜
        'sunshine_bonus_50min': 10, # 50鍒嗛挓浠ヤ笂棰濆闃冲厜
    },
    'focus_streak_3': {'coins': 20, 'sunshine': 10},      # 杩炵画3澶?    'focus_streak_7': {'coins': 50, 'sunshine': 30},      # 杩炵画7澶?    'focus_streak_14': {'coins': 100, 'sunshine': 50},    # 杩炵画14澶?    'focus_streak_30': {'coins': 200, 'sunshine': 100},   # 杩炵画30澶?    'task_complete': {'coins': 20, 'sunshine': 0},
    'task_high_score': {'coins': 30, 'sunshine': 15},     # AI璇勫垎85+
    'exam_pass': {'coins': 30, 'sunshine': 10},           # 妯¤€冨強鏍?    'exam_high_score': {'coins': 50, 'sunshine': 25},     # 妯¤€冮珮鍒?90+)
    'collab_focus': {'coins': 25, 'diamonds': 10},        # 鍗忎綔鐣寗閽?    'daily_goal_complete': {'coins': 15, 'sunshine': 5},  # 瀹屾垚姣忔棩鐩爣
}


def calculate_focus_rewards(duration: int):
    """Internal helper docstring."""
    rule = REWARD_RULES['focus_complete']
    coins_gained = rule['coins_base'] + duration * rule['coins_per_minute']
    diamond_gained = rule['sunshine_base']
    if duration >= 50:
        diamond_gained += rule['sunshine_bonus_50min']
    elif duration >= 25:
        diamond_gained += rule['sunshine_bonus_25min']
    return coins_gained, diamond_gained


def sync_growth_wallet(c, username: str, coins_delta: int = 0, diamonds_delta: int = 0):
    """Internal helper docstring."""
    c.execute(
        """
        INSERT OR IGNORE INTO User_Growth
            (username, focus_energy, total_focus_minutes, streak_days, diamonds, sunshine, coins)
        VALUES (?, 0, 0, 0, 50, 50, 200)
        """Internal helper docstring."""
        (username,)
    )
    c.execute(
        """
        SELECT COALESCE(coins, 0), COALESCE(diamonds, 0), COALESCE(sunshine, 0)
        FROM User_Growth
        WHERE username = ?
        """Internal helper docstring."""
        (username,)
    )
    row = c.fetchone() or (0, 0, 0)
    current_coins = row[0] or 0
    current_diamonds = max(row[1] or 0, row[2] or 0)
    new_coins = current_coins + coins_delta
    new_diamonds = current_diamonds + diamonds_delta
    c.execute(
        """
        UPDATE User_Growth
        SET coins = ?, diamonds = ?, sunshine = ?
        WHERE username = ?
        """Internal helper docstring."""
        (new_coins, new_diamonds, new_diamonds, username)
    )
    return new_coins, new_diamonds


# ============================================
# 馃幆 妯¤€冪鐞?API (Admin)
# ============================================

# 閫氫箟鍗冮棶瀹㈡埛绔?qwen_client = OpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY", "sk-xxx"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


class AdminExamSave(BaseModel):
    exam_code: str
    title: str
    config_json: str
    answer_key_json: str = "{}"
    ai_prompt: str = ""
    audio_file: str = ""
    pdf_file: str = ""
    time_limit: int = 120


class AdminParseAnswers(BaseModel):
    pdf_filename: str
    target_exam: str


@app.post("/api/admin/save_exam")
async def admin_save_exam(data: AdminExamSave):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO Exams
        (exam_code, title, config_json, answer_key_json, ai_prompt, audio_file, pdf_file, time_limit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data.exam_code, data.title, data.config_json, data.answer_key_json,
               data.ai_prompt, data.audio_file, data.pdf_file, data.time_limit))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"鑰冭瘯 {data.exam_code} 淇濆瓨鎴愬姛锛?}


@app.post("/api/admin/parse_answers")
async def admin_parse_answers(data: AdminParseAnswers):
    """Internal helper docstring."""
    pdf_path = os.path.join(static_dir, data.pdf_filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF鏂囦欢涓嶅瓨鍦?)

    try:
        doc = fitz.open(pdf_path)
        text_content = ""
        for page in doc:
            text_content += page.get_text()
        doc.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"璇诲彇PDF澶辫触: {str(e)}")

    prompt = f"""
    浣犳槸涓€浣嶈嫳璇€冭瘯鍑洪涓撳銆傝浠庝互涓媨data.target_exam}鑰冭瘯鍐呭涓彁鍙栫瓟妗堛€?
    鑰冭瘯鍐呭锛?    {text_content[:8000]}

    璇疯繑鍥濲SON鏍煎紡锛?    {{
        "answers": {{
            "1": {{"ans": "A", "weight": 1}},
            "2": {{"ans": "B", "weight": 1}}
        }},
        "ai_prompt": "涓昏棰樿瘎鍒嗘爣鍑?.."
    }}
    """

    try:
        response = qwen_client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "浣犳槸鑻辫鑰冭瘯鍑洪涓撳锛屽繀椤昏繑鍥炴湁鏁堢殑JSON鏍煎紡銆?},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI瑙ｆ瀽澶辫触: {str(e)}")


@app.get("/api/admin/exams")
async def admin_get_exams():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT exam_code, title, time_limit, pdf_file, audio_file FROM Exams ORDER BY exam_code")
    rows = c.fetchall()
    exams = [{"exam_code": r[0], "title": r[1], "time_limit": r[2],
              "pdf_file": r[3], "audio_file": r[4]} for r in rows]
    conn.close()
    return {"exams": exams}


@app.delete("/api/admin/exam/{exam_code}")
async def admin_delete_exam(exam_code: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM Exams WHERE exam_code = ?", (exam_code,))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"鑰冭瘯 {exam_code} 宸插垹闄?}


@app.get("/api/admin/submissions")
async def admin_get_submissions(exam_code: str = None):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if exam_code:
        c.execute('''SELECT s.id, s.exam_code, s.username, s.objective_score, s.subjective_score,
                            s.time_used, s.submit_time, e.title
                     FROM Exam_Submissions s JOIN Exams e ON s.exam_code = e.exam_code
                     WHERE s.exam_code = ? ORDER BY s.submit_time DESC''', (exam_code,))
    else:
        c.execute('''SELECT s.id, s.exam_code, s.username, s.objective_score, s.subjective_score,
                            s.time_used, s.submit_time, e.title
                     FROM Exam_Submissions s JOIN Exams e ON s.exam_code = e.exam_code
                     ORDER BY s.submit_time DESC''')
    rows = c.fetchall()
    submissions = [{"id": r[0], "exam_code": r[1], "username": r[2], "obj_score": r[3],
                    "subj_score": r[4], "time_used": r[5], "submit_time": r[6], "exam_title": r[7]} for r in rows]
    conn.close()
    return {"submissions": submissions}


@app.post("/api/admin/batch_grade")
async def admin_batch_grade(exam_code: str = None):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = '''SELECT s.id, s.subjective_answers, e.ai_prompt
               FROM Exam_Submissions s JOIN Exams e ON s.exam_code = e.exam_code
               WHERE s.subjective_score = 0'''
    params = []
    if exam_code:
        query += " AND s.exam_code = ?"
        params.append(exam_code)

    c.execute(query, params)
    pending = c.fetchall()

    graded_count = 0
    for submission_id, answers_raw, ai_prompt in pending:
        try:
            answers = json.loads(answers_raw) if answers_raw else {}
            if not answers or all(not str(v).strip() for v in answers.values()):
                score, feedback = 0, "浜や簡鐧藉嵎銆備笅娆″媷鏁㈠姩绗斿摝锛?
            else:
                score, feedback = await ai_grade_with_qwen(ai_prompt, answers)

            c.execute('UPDATE Exam_Submissions SET subjective_score = ?, teacher_feedback = ? WHERE id = ?',
                      (score, "馃 閫氫箟鍗冮棶鎵归槄\n\n" + feedback, submission_id))
            conn.commit()
            graded_count += 1
        except Exception as e:
            print(f"鎵规敼澶辫触 ID={submission_id}: {e}")

    conn.close()
    return {"success": True, "graded_count": graded_count, "message": f"宸叉壒鏀?{graded_count} 浠借瘯鍗?}


# ============================================
# 馃幆 鍙屾牳鏅鸿兘鍒ゅ垎寮曟搸
# ============================================

def grade_objective(user_ans: str, correct_ans, weight: float) -> tuple:
    """
    閫氶亾A锛氬瑙傞鏈湴姣绾у垽鍒?    鏀寔澶氱瓟妗堛€佹ā绯婂尮閰嶏紙澶у皬鍐?绌烘牸瀹归敊锛?    杩斿洖: (寰楀垎, 鏄惁姝ｇ‘, 閿欒鍘熷洜)
    """
    user_ans = str(user_ans).strip()

    # 鏀寔澶氱瓟妗堬紙濡傚～绌洪鍚屼箟璇嶏級
    if isinstance(correct_ans, list):
        correct_list = [str(a).strip() for a in correct_ans]
    else:
        correct_list = [str(correct_ans).strip()]

    # 绮剧‘鍖归厤锛堜笉鍖哄垎澶у皬鍐欙級
    user_lower = user_ans.lower()
    for corr in correct_list:
        if user_lower == corr.lower():
            return weight, True, None

    # 妯＄硦鍖归厤锛堝拷鐣ョ┖鏍硷級
    user_no_space = user_lower.replace(" ", "")
    for corr in correct_list:
        if user_no_space == corr.lower().replace(" ", ""):
            return weight, True, None

    # 閿欒鎯呭喌
    return 0, False, f"姝ｇ‘绛旀: {correct_list[0]}"


# 涓昏棰楢I鎵规敼缁撴瀯鍖朠rompt妯℃澘
SUBJECTIVE_GRADING_PROMPT = """
浣犳槸涓€浣嶄弗璋ㄧ殑澶у鑻辫闃呭嵎鏁欐巿銆傝鏍规嵁浠ヤ笅淇℃伅鎵规敼瀛︾敓绛旀銆?
銆愰鐩紪鍙枫€憑question_id}

銆愭爣鍑嗙瓟妗堜笌璇勫垎鏍囧噯銆?{rubric}

銆愭弧鍒嗐€憑max_score}鍒?
銆愬鐢熺瓟妗堛€?{student_answer}

銆愭壒鏀硅姹傘€?1. 閫愮偣瀵圭収璇勫垎鏍囧噯锛岀粰鍑哄叿浣撳緱鍒?2. 鎸囧嚭璇硶閿欒銆佽瘝姹囦娇鐢ㄩ棶棰樸€佷腑寮忚嫳璇?3. 鎻愪緵閽堝鎬х殑鏀硅繘寤鸿
4. 闄勪笂鍙傝€冭寖鏂?璇戞枃

銆愯繑鍥炴牸寮忋€戝繀椤昏緭鍑烘湁鏁圝SON锛?{{
  "score": 鍒嗘暟(鏁板瓧,涓嶈秴杩囨弧鍒?,
  "breakdown": {{"鍐呭": 寰楀垎, "璇硶": 寰楀垎, "琛ㄨ揪": 寰楀垎}},
  "errors": ["閿欒1", "閿欒2"],
  "feedback": "璇︾粏鐨勪腑鏂囪瘎璇紙鍖呭惈鎬讳綋璇勪环銆佸叿浣撶籂閿欙級",
  "suggestion": "鏀硅繘寤鸿锛?-3鏉★級",
  "reference": "鍙傝€冭寖鏂囨垨鍙傝€冭瘧鏂?
}}
"""


async def ai_grade_subjective_single(question_id: str, student_answer: str, rubric: str, max_score: float) -> dict:
    """
    閫氶亾B锛氬崟閬撲富瑙傞AI娣卞害鎵规敼
    娉ㄥ叆瀹屾暣涓婁笅鏂囷細鏍囧噯绛旀+璇勫垎鏍囧噯+瑙ｆ瀽
    """
    prompt = SUBJECTIVE_GRADING_PROMPT.format(
        question_id=question_id,
        rubric=rubric or "璇锋牴鎹瓟妗堣川閲忚瘎鍒?,
        max_score=max_score,
        student_answer=student_answer
    )

    try:
        response = qwen_client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "浣犳槸澶у鑻辫闃呭嵎鏁欐巿锛屽繀椤昏緭鍑烘湁鏁堢殑JSON鏍煎紡锛屼笉瑕佸寘鍚换浣昺arkdown鏍囪銆?},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "score": min(float(result.get("score", 0)), max_score),  # 涓嶈秴杩囨弧鍒?            "breakdown": result.get("breakdown", {}),
            "errors": result.get("errors", []),
            "feedback": result.get("feedback", "璇勮鐢熸垚澶辫触"),
            "suggestion": result.get("suggestion", ""),
            "reference": result.get("reference", "")
        }
    except Exception as e:
        print(f"AI鎵规敼鍑洪敊 [{question_id}]: {e}")
        return {
            "score": 0,
            "breakdown": {},
            "errors": [],
            "feedback": f"AI鎵规敼鏆傛椂涓嶅彲鐢? {str(e)}",
            "suggestion": "",
            "reference": ""
        }


async def ai_grade_with_qwen(ai_prompt: str, answers: dict) -> tuple:
    """Internal helper docstring."""
    prompt = f"""
    銆愰槄鍗锋爣鍑嗗強婊″垎銆戯細
    {ai_prompt}

    銆愬鐢熶綔绛斿唴瀹广€戯紙JSON鏍煎紡锛夛細
    {json.dumps(answers, ensure_ascii=False)}

    銆愭壒鏀硅姹傘€戯細
    1. 鎸囧嚭璇硶閿欒銆佹嫾鍐欓敊璇強涓紡鑻辫
    2. 鏍规嵁婊″垎鏍囧噯缁欏嚭鍚堢悊鎬诲垎锛堟暟瀛楃被鍨嬶級
    3. 鍐欎竴娈佃缁嗙殑涓枃璇勮
    4. 鍦ㄨ瘎璇渶鍚庨檮涓娿€愯寖鏂?鍙傝€冭瘧鏂囥€?
    杩斿洖JSON鏍煎紡锛?    {{ "score": 12.5, "feedback": "銆愭€讳綋璇勪环銆?..\\n銆愮籂閿欍€?..\\n\\n銆愬弬鑰冭寖鏂囥€戯細\\n..." }}
    """

    try:
        response = qwen_client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "浣犳槸澶у鑻辫闃呭嵎鏁欐巿锛屽繀椤昏緭鍑烘湁鏁堢殑JSON鏍煎紡銆?},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("score", 0), result.get("feedback", "璇勮鐢熸垚澶辫触")
    except Exception as e:
        print(f"AI鎵规敼鍑洪敊: {e}")
        return 0, f"AI鎵规敼鏆傛椂涓嶅彲鐢? {str(e)}"


# ============================================
# 馃摑 瀛︾敓鑰冭瘯 API 澧炲己
# ============================================

@app.get("/api/exam/grading_status/{submission_id}")
async def get_grading_status(submission_id: int):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT subjective_score, teacher_feedback FROM Exam_Submissions WHERE id = ?", (submission_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="鎻愪氦璁板綍涓嶅瓨鍦?)
    return {
        "status": "completed" if row[0] > 0 else "pending",
        "subjective_score": row[0],
        "feedback": row[1]
    }


class AIAnalysisRequest(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    context: str = ""


@app.post("/api/exam/ai_analysis")
async def ai_analyze_mistake(data: AIAnalysisRequest):
    """Internal helper docstring."""
    prompt = f"""
    瀛︾敓鍦ㄨ嫳璇€冭瘯涓瓟閿欎簡杩欓亾棰橈細

    銆愰鐩€憑data.question}
    銆愬鐢熺瓟妗堛€憑data.user_answer}
    銆愭纭瓟妗堛€憑data.correct_answer}
    銆愪笂涓嬫枃銆憑data.context or "鏃?}

    璇峰垎鏋愶細
    1. 瀛︾敓涓轰粈涔堢瓟閿欎簡锛燂紙鐭ヨ瘑鐐圭洸鐐广€佺悊瑙ｅ亸宸瓑锛?    2. 鐩稿叧璇硶/璇嶆眹鐭ヨ瘑鐐硅瑙?    3. 涓句竴鍙嶄笁鐨勭被浼间緥棰?    4. 瀛︿範寤鸿

    璇风敤涓枃鍥炵瓟锛屾牸寮忓弸濂姐€?    """

    try:
        response = qwen_client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "浣犳槸涓€浣嶈€愬績鐨勮嫳璇緟瀵艰€佸笀锛屽杽浜庡垎鏋愬鐢熼敊璇苟鎻愪緵鏈夐拡瀵规€х殑寤鸿銆?},
                {"role": "user", "content": prompt}
            ]
        )
        return {"success": True, "analysis": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI鍒嗘瀽澶辫触: {str(e)}")


# --- 馃専 To-Do 鍒楄〃鎺ュ彛 ---
@app.post("/api/todo/add")
async def add_todo(data: TodoAdd):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Todo_Tasks (username, content) VALUES (?, ?)", (data.username, data.content))
    conn.commit();
    conn.close()
    return {"message": "娣诲姞鎴愬姛"}


@app.get("/api/todo/{username}")
async def get_todos(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, content, is_completed FROM Todo_Tasks WHERE username = ? ORDER BY is_completed ASC, id DESC",
              (username,))
    tasks = [{"id": r[0], "content": r[1], "is_completed": bool(r[2])} for r in c.fetchall()]
    conn.close()
    return {"tasks": tasks}


@app.post("/api/todo/toggle")
async def toggle_todo(data: TodoAction):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE Todo_Tasks SET is_completed = NOT is_completed WHERE id = ? AND username = ?",
              (data.task_id, data.username))
    conn.commit();
    conn.close()
    return {"message": "鐘舵€佸凡鏇存柊"}


@app.post("/api/todo/delete")
async def delete_todo(data: TodoAction):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM Todo_Tasks WHERE id = ? AND username = ?", (data.task_id, data.username))
    conn.commit();
    conn.close()
    return {"message": "宸插垹闄?}


# --- 馃専 Forest 涓撴敞妫灄鎺ュ彛 ---
@app.post("/api/focus/start")
async def start_focus(data: FocusStart):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO Study_Sessions (username, subject, duration, tree_type, status) VALUES (?, ?, ?, ?, 'ongoing')",
        (data.username, data.subject, data.duration, data.tree_type))
    session_id = c.lastrowid
    conn.commit();
    conn.close()
    return {"message": "寮€濮嬩笓娉?, "session_id": session_id}


@app.post("/api/focus/end")
async def end_focus(data: FocusEnd):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM Study_Sessions WHERE id = ? AND username = ?", (data.session_id, data.username))
    old_status_row = c.fetchone()
    old_status = old_status_row[0] if old_status_row else None
    c.execute("UPDATE Study_Sessions SET status = ?, end_time = CURRENT_TIMESTAMP WHERE id = ? AND username = ?",
              (data.status, data.session_id, data.username))
    reward_payload = None

    # 濡傛灉涓撴敞鎴愬姛锛岃嚜鍔ㄥ彂鏈嬪弸鍦堬紒
    if data.status == 'completed':
        c.execute("SELECT subject, duration, tree_type FROM Study_Sessions WHERE id = ?", (data.session_id,))
        row = c.fetchone()
        if row:
            if old_status != 'completed':
                coins_gained, diamonds_gained = calculate_focus_rewards(row[1] or 0)
                new_coins, new_diamonds = sync_growth_wallet(
                    c,
                    data.username,
                    coins_delta=coins_gained,
                    diamonds_delta=diamonds_gained,
                )
                reward_payload = {
                    "coins_gained": coins_gained,
                    "diamonds_gained": diamonds_gained,
                    "new_coins": new_coins,
                    "new_diamonds": new_diamonds,
                }
            content = f"馃崊 涓撴敞鎵撳崱鎴愬姛锛乗n鎴戝垰鍒氱垎鑲濅簡 {row[1]} 鍒嗛挓鐨勩€妠row[0]}銆嬶紝鎴愬姛绉嶄笅浜嗕竴妫点€恵row[2]}銆戯紒馃尦 澶у涓€璧峰嵎璧锋潵锛?
            c.execute("INSERT INTO Posts (username, content, image_url) VALUES (?, ?, ?)", (data.username, content, ""))

    conn.commit();
    conn.close()
    return {"message": "缁撶畻瀹屾垚", "status": data.status}


@app.get("/api/focus/stats/{username}")
async def get_focus_stats(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(duration), COUNT(id) FROM Study_Sessions WHERE username = ? AND status = 'completed'",
              (username,))
    row = c.fetchone()
    total_minutes = row[0] or 0
    total_trees = row[1] or 0
    c.execute("SELECT COUNT(id) FROM Study_Sessions WHERE username = ? AND status = 'failed'", (username,))
    dead_trees = c.fetchone()[0] or 0
    conn.close()
    return {"total_minutes": total_minutes, "total_trees": total_trees, "dead_trees": dead_trees}


class FocusComplete(BaseModel):
    username: str
    duration: int
    subject: str = "瀛︿範"


@app.post("/api/focus/complete")
async def complete_focus(data: FocusComplete):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. 璁＄畻涓撴敞鑳介噺 (1鍒嗛挓 = 2鑳介噺锛屾渶浣?0)
    energy_gained = max(10, data.duration * 2)

    # 2. 璁＄畻閲戝竵鍜岄槼鍏夊鍔?    coins_gained, sunshine_gained = calculate_focus_rewards(data.duration)

    # 3. 鏇存柊鎴愰暱鏁版嵁
    get_or_create_growth(data.username)
    c.execute("SELECT focus_energy, coins, sunshine, diamonds FROM User_Growth WHERE username = ?", (data.username,))
    row = c.fetchone()
    current_energy = row[0] or 0
    current_coins = row[1] or 0
    current_sunshine = row[2] or 0
    current_diamonds = max(row[2] or 0, row[3] or 0)

    new_energy = current_energy + energy_gained
    new_coins = current_coins + coins_gained
    new_diamonds = current_diamonds + sunshine_gained
    new_sunshine = new_diamonds

    c.execute('''UPDATE User_Growth
                SET focus_energy = ?,
                    coins = ?,
                    diamonds = ?,
                    sunshine = ?,
                    total_focus_minutes = total_focus_minutes + ?
                WHERE username = ?''',
              (new_energy, new_coins, new_diamonds, new_diamonds, data.duration, data.username))

    # 4. 妫€鏌ヨ繛缁ぉ鏁板苟缁欎簣杩炵画濂栧姳
    from datetime import datetime as dt
    c.execute("SELECT last_active_date, streak_days FROM User_Growth WHERE username = ?",
              (data.username,))
    streak_row = c.fetchone()
    last_active, streak = streak_row[0], streak_row[1]

    today = dt.now().date()
    new_streak = streak
    streak_bonus = {'coins': 0, 'sunshine': 0}

    if last_active:
        last_date = dt.strptime(last_active, "%Y-%m-%d").date()
        days_diff = (today - last_date).days
        if days_diff == 1:
            new_streak = streak + 1
        elif days_diff > 1:
            new_streak = 1
    else:
        new_streak = 1

    # 杩炵画澶╂暟濂栧姳
    if new_streak >= 30:
        streak_bonus = REWARD_RULES['focus_streak_30']
    elif new_streak >= 14:
        streak_bonus = REWARD_RULES['focus_streak_14']
    elif new_streak >= 7:
        streak_bonus = REWARD_RULES['focus_streak_7']
    elif new_streak >= 3:
        streak_bonus = REWARD_RULES['focus_streak_3']

    # 鍙戞斁杩炵画濂栧姳锛堜粎鍦ㄨ揪鍒伴噷绋嬬鏃讹級
    if streak_bonus['coins'] > 0 or streak_bonus['sunshine'] > 0:
        # 妫€鏌ヤ粖澶╂槸鍚﹀凡鑾峰緱杩炵画濂栧姳
        c.execute("SELECT 1 FROM Streak_Rewards_Claimed WHERE username = ? AND streak_days = ? AND claim_date = ?",
                  (data.username, new_streak, today.strftime("%Y-%m-%d")))
        if not c.fetchone() and new_streak in [3, 7, 14, 30, 60, 100]:
            new_coins += streak_bonus['coins']
            new_sunshine += streak_bonus['sunshine']
            new_diamonds += streak_bonus['sunshine']
            new_sunshine = new_diamonds
            c.execute('''UPDATE User_Growth SET coins = ?, diamonds = ?, sunshine = ? WHERE username = ?''',
                      (new_coins, new_diamonds, new_diamonds, data.username))
            c.execute("INSERT OR IGNORE INTO Streak_Rewards_Claimed (username, streak_days, claim_date) VALUES (?, ?, ?)",
                      (data.username, new_streak, today.strftime("%Y-%m-%d")))

    c.execute('''UPDATE User_Growth SET streak_days = ?, last_active_date = ?
                WHERE username = ?''',
              (new_streak, today.strftime("%Y-%m-%d"), data.username))

    # 5. 鑷姩鍙戝笘
    reward_text = f"馃攱+{energy_gained}"
    if coins_gained > 0:
        reward_text += f" 馃挵+{coins_gained}"
    if sunshine_gained > 0:
        reward_text += f" 鈽€锔?{sunshine_gained}"
    content = f"馃崊 涓撴敞鎵撳崱锛乗n鎴戝垰涓撴敞浜?{data.duration} 鍒嗛挓銆妠data.subject}銆媨reward_text}"
    c.execute("INSERT INTO Posts (username, content, image_url) VALUES (?, ?, ?)",
              (data.username, content, ""))

    conn.commit()
    conn.close()

    return {
        "message": "涓撴敞瀹屾垚锛?,
        "energy_gained": energy_gained,
        "coins_gained": coins_gained,
        "sunshine_gained": sunshine_gained,
        "diamonds_gained": sunshine_gained,
        "streak_bonus": streak_bonus if streak_bonus['coins'] > 0 or streak_bonus['sunshine'] > 0 else None,
        "new_energy": new_energy,
        "new_coins": new_coins,
        "new_sunshine": new_sunshine,
        "new_diamonds": new_diamonds,
        "streak_days": new_streak
    }


# --- 绀惧尯鍦堝瓙鎺ュ彛 ---
def cleanup_city_processes():
    """Internal helper docstring."""
    for username, proc in list(PYGAME_CITY_PROCESSES.items()):
        if proc.poll() is not None:
            PYGAME_CITY_PROCESSES.pop(username, None)


@app.post("/api/city/launch")
async def launch_pygame_city(data: CityLaunchRequest):
    """Internal helper docstring."""
    cleanup_city_processes()

    if not data.username:
        raise HTTPException(status_code=400, detail="username required")

    existing = PYGAME_CITY_PROCESSES.get(data.username)
    if existing and existing.poll() is None:
        return {
            "success": True,
            "message": "Pygame 鍩庡競绐楀彛宸茬粡鍦ㄨ繍琛屼腑",
            "pid": existing.pid,
            "already_running": True
        }

    city_script = os.path.join(BASE_DIR, "city_builder_pygame.py")
    if not os.path.exists(city_script):
        raise HTTPException(status_code=404, detail="city_builder_pygame.py not found")

    proc = subprocess.Popen(
        [sys.executable, city_script, data.username],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True
    )
    PYGAME_CITY_PROCESSES[data.username] = proc
    return {
        "success": True,
        "message": "Pygame 鍩庡競宸插惎鍔?,
        "pid": proc.pid,
        "already_running": False
    }


@app.post("/api/posts/create")
async def create_post(post: PostData):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Posts (username, content, image_url) VALUES (?, ?, ?)",
              (post.username, post.content, post.image_url))
    conn.commit();
    conn.close()
    return {"message": "鍙戝竷鎴愬姛锛?}


@app.get("/api/posts")
async def get_posts(username: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, content, image_url, likes, datetime(timestamp, 'localtime') FROM Posts ORDER BY id DESC")
    posts = c.fetchall()
    feed = []
    for p in posts:
        post_id = p[0]
        c.execute(
            "SELECT username, content, datetime(timestamp, 'localtime') FROM Comments WHERE post_id = ? ORDER BY id ASC",
            (post_id,))
        comments = [{"username": row[0], "content": row[1], "time": row[2]} for row in c.fetchall()]
        has_liked = False
        if username:
            c.execute("SELECT 1 FROM Post_Likes WHERE post_id = ? AND username = ?", (post_id, username))
            if c.fetchone(): has_liked = True
        feed.append({"id": post_id, "author": p[1], "content": p[2], "image_url": p[3], "likes": p[4], "time": p[5],
                     "comments": comments, "has_liked": has_liked})
    conn.close()
    return {"feed": feed}


@app.post("/api/posts/like")
async def toggle_like(data: LikeData):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM Post_Likes WHERE post_id = ? AND username = ?", (data.post_id, data.username))
    if c.fetchone():
        c.execute("DELETE FROM Post_Likes WHERE post_id = ? AND username = ?", (data.post_id, data.username))
        c.execute("UPDATE Posts SET likes = likes - 1 WHERE id = ?", (data.post_id,))
    else:
        c.execute("INSERT INTO Post_Likes (post_id, username) VALUES (?, ?)", (data.post_id, data.username))
        c.execute("UPDATE Posts SET likes = likes + 1 WHERE id = ?", (data.post_id,))
    conn.commit();
    conn.close()
    return {"message": "鎿嶄綔鎴愬姛"}


@app.post("/api/posts/comment")
async def add_comment(data: CommentData):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Comments (post_id, username, content) VALUES (?, ?, ?)",
              (data.post_id, data.username, data.content))
    conn.commit();
    conn.close()
    return {"message": "璇勮鎴愬姛"}


# --- 鑰冨満涓庡巻鍙叉帴鍙?(淇濈暀) ---
@app.get("/api/exams")
async def get_exams():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT exam_code, title, config_json, audio_file, pdf_file, time_limit FROM Exams")
    rows = c.fetchall()
    conn.close()
    return {"exams": [{"exam_code": r[0], "title": r[1], "config_json": json.loads(r[2]), "time_limit": r[5]} for r in
                      rows]}

@app.post("/api/submit_exam")
async def grade_exam(data: ExamData):
    """
    鍙屾牳鍒ゅ垎寮曟搸鍏ュ彛
    - 閫氶亾A锛氬瑙傞鏈湴姣绾у垽鍒?    - 閫氶亾B锛氫富瑙傞寮傛AI娣卞害鎵规敼
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇鑰冭瘯閰嶇疆
    c.execute("SELECT answer_key_json, ai_prompt, config_json FROM Exams WHERE exam_code = ?", (data.exam_code,))
    row = c.fetchone()
    ans_db = json.loads(row[0]) if row and row[0] else {}
    ai_prompt = row[1] if row and row[1] else "璇锋牴鎹瓟妗堣川閲忚瘎鍒?
    config_json = json.loads(row[2]) if row and row[2] else []

    # 鏋勫缓棰樺瀷閰嶇疆鏄犲皠
    q_type_map = {}
    for section in config_json:
        for q in section.get('questions', []):
            q_type_map[q['id']] = section.get('type', 'choice')

    obj_score = 0.0
    attempted_score = 0.0
    subj_answers = {}
    mistakes = []

    for q_key, user_ans in data.answers.items():
        if not user_ans:
            continue

        # 鍒ゆ柇棰樼洰绫诲瀷
        q_type = q_type_map.get(q_key, 'choice')

        if q_key in ans_db and q_type in ['choice', 'blank', 'fill']:
            # 馃幆 閫氶亾A锛氬瑙傞鏈湴鍒ゅ垎
            correct_ans = ans_db[q_key].get("ans")
            weight = float(ans_db[q_key].get("weight", 1.0))
            analysis = ans_db[q_key].get("analysis", "鏆傛棤瑙ｆ瀽")

            attempted_score += weight
            score, is_correct, error_reason = grade_objective(user_ans, correct_ans, weight)
            obj_score += score

            if not is_correct:
                mistakes.append({
                    "question": q_key,
                    "user": user_ans,
                    "correct": correct_ans if not isinstance(correct_ans, list) else correct_ans[0],
                    "analysis": analysis
                })
        else:
            # 馃 閫氶亾B锛氫富瑙傞鏀堕泦锛岀◢鍚嶢I鎵规敼
            subj_answers[q_key] = user_ans

    # 淇濆瓨鎻愪氦璁板綍
    c.execute('''INSERT INTO Exam_Submissions (exam_code, room_id, username, objective_score, attempted_score, time_used, subjective_answers, mistakes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data.exam_code, data.room_id, data.username, obj_score, attempted_score, data.time_used,
               json.dumps(subj_answers), json.dumps(mistakes)))
    submission_id = c.lastrowid
    conn.commit()
    conn.close()

    # 濡傛灉鏈変富瑙傞锛屽紓姝ヨЕ鍙慉I鎵规敼
    if subj_answers:
        import asyncio
        asyncio.create_task(auto_grade_subjective_enhanced(submission_id, ai_prompt, subj_answers))

    return {
        "message": "浜ゅ嵎鎴愬姛",
        "submission_id": submission_id,
        "objective_score": obj_score,
        "attempted_score": attempted_score,
        "has_subjective": bool(subj_answers),
        "mistakes": mistakes  # 杩斿洖閿欓淇℃伅渚涘墠绔睍绀?    }


async def auto_grade_subjective(submission_id: int, ai_prompt: str, answers: dict):
    """Internal helper docstring."""
    try:
        score, feedback = await ai_grade_with_qwen(ai_prompt, answers)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE Exam_Submissions SET subjective_score = ?, teacher_feedback = ? WHERE id = ?',
                  (score, "馃 閫氫箟鍗冮棶鑷姩鎵归槄\n\n" + feedback, submission_id))
        conn.commit()
        conn.close()
        print(f"[OK] AI鎵规敼瀹屾垚: submission_id={submission_id}, score={score}")
    except Exception as e:
        print(f"[ERR] AI鎵规敼澶辫触: {e}")


async def auto_grade_subjective_enhanced(submission_id: int, ai_prompt: str, answers: dict):
    """
    澧炲己鐗堜富瑙傞AI鎵规敼
    - 鍒嗛鎵规敼锛屾瘡棰樼嫭绔嬭瘎鍒?    - 杩斿洖缁撴瀯鍖栫粨鏋滐紙鍒嗘暟銆侀敊璇€佸缓璁€佽寖鏂囷級
    - 鏀寔鍒嗙淮搴﹁瘎鍒?    """
    try:
        # 瑙ｆ瀽璇勫垎鏍囧噯锛堜粠ai_prompt涓彁鍙栧悇棰樻爣鍑嗭級
        rubrics = parse_rubrics_from_prompt(ai_prompt)
        total_score = 0
        all_results = {}

        for q_key, student_ans in answers.items():
            rubric = rubrics.get(q_key, ai_prompt)  # 鑾峰彇璇ラ璇勫垎鏍囧噯
            max_score = extract_max_score(rubric) or 15  # 浠庢爣鍑嗕腑鎻愬彇婊″垎

            # 璋冪敤鍗曢AI鎵规敼
            result = await ai_grade_subjective_single(q_key, student_ans, rubric, max_score)
            all_results[q_key] = result
            total_score += result["score"]

        # 鏋勫缓缁煎悎鍙嶉
        feedback_parts = ["馃 閫氫箟鍗冮棶鏅鸿兘鎵归槄\n"]
        for q_key, res in all_results.items():
            feedback_parts.append(f"\n銆恵q_key}銆戝緱鍒? {res['score']}")
            if res['errors']:
                feedback_parts.append(f"  鉂?閿欒: {', '.join(res['errors'])}")
            if res['feedback']:
                feedback_parts.append(f"  馃摑 璇勮: {res['feedback'][:100]}...")
            if res['reference']:
                feedback_parts.append(f"  馃摉 鍙傝€? {res['reference'][:80]}...")

        combined_feedback = "\n".join(feedback_parts)

        # 鏇存柊鏁版嵁搴?
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''UPDATE Exam_Submissions
                     SET subjective_score = ?, teacher_feedback = ?
                     WHERE id = ?''',
                  (total_score, combined_feedback, submission_id))
        conn.commit()
        conn.close()

        print(f"[OK] 澧炲己AI鎵规敼瀹屾垚: submission_id={submission_id}, total_score={total_score}")

    except Exception as e:
        print(f"[ERR] 澧炲己AI鎵规敼澶辫触: {e}")
        # 闄嶇骇鍒版棫鐗堟壒鏀?        await auto_grade_subjective(submission_id, ai_prompt, answers)


def parse_rubrics_from_prompt(ai_prompt: str) -> dict:
    """
    浠巃i_prompt涓В鏋愬悇棰樼殑璇勫垎鏍囧噯
    鏀寔鏍煎紡锛氥€愰鐩甉57銆?.. 鎴?銆愮炕璇戦銆?..
    """
    rubrics = {}
    import re

    # 鍖归厤銆愰鐩甉57銆戞垨銆愮炕璇戦Q57銆戠瓑鏍煎紡
    pattern = r'銆怺^銆慮*?Q?(\d+)[^銆慮*銆?[^銆怾*?)(?=銆恷$)'
    matches = re.findall(pattern, ai_prompt, re.DOTALL)

    for q_num, content in matches:
        rubrics[f'q{q_num}'] = content.strip()

    # 濡傛灉娌℃湁鍖归厤鍒板垎棰樻牸寮忥紝鏁翠綋浣滀负涓€涓爣鍑?    if not rubrics:
        rubrics['default'] = ai_prompt

    return rubrics


def extract_max_score(rubric: str) -> float:
    """Internal helper docstring."""
    import re
    # 鍖归厤 "婊″垎15鍒? 鎴?"(15鍒?" 绛夋牸寮?    match = re.search(r'(?:婊″垎|鎬诲垎|鍏?[锛?]?\s*(\d+(?:\.\d+)?)\s*鍒?, rubric)
    if match:
        return float(match.group(1))
    match = re.search(r'\((\d+(?:\.\d+)?)\s*鍒哱)', rubric)
    if match:
        return float(match.group(1))
    return 15.0  # 榛樿15鍒?

@app.get("/api/history/{username}")
async def get_history(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT s.room_id, s.objective_score, s.attempted_score, s.teacher_feedback, e.title 
        FROM Exam_Submissions s JOIN Exams e ON s.exam_code = e.exam_code WHERE s.username = ? ORDER BY s.id DESC''',
              (username,))
    rows = c.fetchall()
    conn.close()
    return {
        "history": [{"room_id": r[0], "obj_score": r[1], "attempted": r[2], "feedback": r[3], "exam_title": r[4]} for r
                    in rows]}


@app.post("/api/register")
async def register(user: UserAuth):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶅拰瀵嗙爜涓嶈兘涓虹┖锛?)

    if len(user.username) < 2:
        raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶈嚦灏戦渶瑕?涓瓧绗︼紒")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鍏堟鏌ョ敤鎴峰悕鏄惁宸插瓨鍦?
    c.execute("SELECT username FROM Users WHERE username=?", (user.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶅凡琚敞鍐岋紒")

    try:
        c.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (user.username, user.password))
        conn.commit()

        # 鍚屾椂鍒涘缓鐢ㄦ埛鎴愰暱鏁版嵁
        c.execute("INSERT OR IGNORE INTO User_Growth (username) VALUES (?)", (user.username,))
        conn.commit()

        conn.close()
        return {"success": True, "message": "娉ㄥ唽鎴愬姛锛?}
    except Exception as e:
        conn.close()
        print(f"娉ㄥ唽閿欒: {e}")
        raise HTTPException(status_code=500, detail=f"娉ㄥ唽澶辫触: {str(e)}")


@app.post("/api/login")
async def login(user: UserAuth):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="璇疯緭鍏ョ敤鎴峰悕鍜屽瘑鐮侊紒")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM Users WHERE username=? AND password=?", (user.username, user.password))
    u = c.fetchone()
    conn.close()

    if not u:
        raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒锛?)

    return {"success": True, "message": "鐧诲綍鎴愬姛锛?, "username": user.username}


# ===== 鐢ㄦ埛澶村儚 API =====

class AvatarUpdate(BaseModel):
    avatar: str


@app.get("/api/user/{username}/avatar")
async def get_user_avatar(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚avatar鍒楀瓨鍦?    try:
        c.execute("SELECT avatar FROM Users WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            avatar = row[0] or '馃懆鈥嶐煔€'
        else:
            avatar = '馃懆鈥嶐煔€'
    except sqlite3.OperationalError:
        # 濡傛灉avatar鍒椾笉瀛樺湪锛屾坊鍔犲畠
        try:
            c.execute("ALTER TABLE Users ADD COLUMN avatar TEXT DEFAULT '馃懆鈥嶐煔€'")
            conn.commit()
        except:
            pass
        avatar = '馃懆鈥嶐煔€'

    conn.close()
    return {"avatar": avatar, "username": username}


@app.post("/api/user/{username}/avatar")
async def update_user_avatar(username: str, data: AvatarUpdate):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚avatar鍒楀瓨鍦?    try:
        c.execute("SELECT avatar FROM Users WHERE username = ? LIMIT 1", (username,))
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE Users ADD COLUMN avatar TEXT DEFAULT '馃懆鈥嶐煔€'")
        conn.commit()

    # 鏇存柊澶村儚
    c.execute("UPDATE Users SET avatar = ? WHERE username = ?", (data.avatar, username))

    # 濡傛灉鐢ㄦ埛涓嶅瓨鍦紝鍒涘缓涓€涓紙鍙€夛級
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="鐢ㄦ埛涓嶅瓨鍦?)

    conn.commit()
    conn.close()

    return {"success": True, "avatar": data.avatar, "message": "澶村儚鏇存柊鎴愬姛"}


@app.get("/api/user/{username}/profile")
async def get_user_profile(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚avatar鍒楀瓨鍦?    try:
        c.execute("SELECT username, avatar FROM Users WHERE username = ?", (username,))
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE Users ADD COLUMN avatar TEXT DEFAULT '馃懆鈥嶐煔€'")
        conn.commit()
        c.execute("SELECT username, avatar FROM Users WHERE username = ?", (username,))

    user_row = c.fetchone()

    # 鑾峰彇鎴愰暱鏁版嵁
    c.execute('''SELECT focus_energy, total_focus_minutes, streak_days, diamonds, level, exp
                FROM User_Growth WHERE username = ?''', (username,))
    growth_row = c.fetchone()

    conn.close()

    if not user_row:
        raise HTTPException(status_code=404, detail="鐢ㄦ埛涓嶅瓨鍦?)

    return {
        "username": user_row[0],
        "avatar": user_row[1] or '馃懆鈥嶐煔€',
        "growth": {
            "focus_energy": growth_row[0] if growth_row else 0,
            "total_focus_minutes": growth_row[1] if growth_row else 0,
            "streak_days": growth_row[2] if growth_row else 0,
            "diamonds": growth_row[3] if growth_row else 0,
            "level": growth_row[4] if growth_row else 1,
            "exp": growth_row[5] if growth_row else 0
        }
    }


# ================= 鏂板锛氭暟鐢?鐢垫皵涓撲笟 AI 鍔╂暀妯″潡 =================
class EEQuery(BaseModel):
    api_key: str
    query: str
    mode: str  # 'simplify' (鍖栫畝閫昏緫) 鎴?'translate' (缈昏瘧鎵嬪唽)


@app.post("/api/ee_assistant")
async def ee_assistant_api(req: EEQuery):
    try:
        # 杩欓噷缁х画浣跨敤浣犵敵璇风殑闃块噷浜戦€氫箟鍗冮棶澶фā鍨?        client = OpenAI(api_key=req.api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

        # 馃 鏍稿績榄旀硶锛氶拡瀵圭數姘斾笓涓氱殑寮哄姏 Prompt (鎻愮ず璇?
        if req.mode == "simplify":
            sys_prompt = """浣犳槸涓€涓《绾х殑銆婃暟瀛楃數瀛愭妧鏈€嬩笓瀹躲€?            瀛︾敓浼氱粰浣犺緭鍏ヤ竴娈甸€昏緫浠ｆ暟琛ㄨ揪寮忥紙甯冨皵浠ｆ暟锛夋垨鑰呯數璺棶棰樸€?            璇蜂綘锛?. 缁欏嚭璇︾粏鐨勫寲绠€姝ラ锛堝鎸囧嚭鍝噷鐢ㄤ簡鍚告敹寰嬨€佹懇鏍瑰畾寰嬬瓑锛夈€?            2. 缁欏嚭鏈€绠€鐨勨€滀笌鎴栧紡鈥濄€?            3. 濡傛灉鍙兘锛岀敤鏂囧瓧鎻忚堪涓€涓嬭繖涓數璺彲浠ョ敤鏈€灏戝嚑涓笌闈為棬鎼嚭鏉ャ€?""
        else:
            sys_prompt = """浣犳槸涓€涓祫娣辩殑鐢垫皵宸ョ▼甯堝吋涓撲笟缈昏瘧銆?            璇风簿鍑嗙炕璇戝鐢熸彁渚涚殑鑺墖鏁版嵁鎵嬪唽锛圖atasheet锛夋钀姐€?            鈿狅笍銆愭渶楂樻寚浠ゃ€戯細鍔″繀淇濊瘉涓撲笟璇嶆眹鐨勭粷瀵瑰噯纭紒渚嬪锛?            - Flip-flop 蹇呴』缈昏瘧涓衡€滆Е鍙戝櫒鈥濓紙缁濅笉鑳芥槸浜哄瓧鎷栵級
            - Logic Gate 蹇呴』缈昏瘧涓衡€滈€昏緫闂ㄢ€?            - Register 蹇呴』缈昏瘧涓衡€滃瘎瀛樺櫒鈥?            - Multiplexer 蹇呴』缈昏瘧涓衡€滄暟鎹€夋嫨鍣ㄢ€?            """

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": req.query}]
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 鍔╂暀寮€灏忓樊浜嗭細{str(e)}")


# ================= 馃尡 鎵嬫満浣跨敤涓婃姤妯″潡 =================
@app.post("/api/phone-usage/report")
async def report_phone_usage(data: PhoneUsageReport):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO Phone_Usage (username, usage_minutes, category, notes)
                VALUES (?, ?, ?, ?)''',
              (data.username, data.usage_minutes, data.category, data.notes))
    conn.commit()
    conn.close()
    return {"message": "涓婃姤鎴愬姛", "reported_minutes": data.usage_minutes}


from fastapi import UploadFile, File, Form

@app.post("/api/phone-usage/analyze-screenshot")
async def analyze_screenshot(
    file: UploadFile = File(...),
    username: str = Form(...)
):
    """Internal helper docstring."""
    import base64
    import json
    from openai import OpenAI

    # 璇诲彇鍥剧墖
    image_data = await file.read()
    base64_image = base64.b64encode(image_data).decode('utf-8')

    # 浣跨敤閫氫箟鍗冮棶瑙嗚妯″瀷 (qwen-vl-plus)
    DASHSCOPE_API_KEY = "sk-10dee7815be045a4a871e396adc6219d"  # 鐢ㄦ埛鍙互鏇挎崲鎴愯嚜宸辩殑閫氫箟API Key
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        response = client.chat.completions.create(
            model="qwen-vl-plus",  # 閫氫箟鍗冮棶瑙嗚妯″瀷
            messages=[
                {
                    "role": "system",
                    "content": """浣犳槸涓€涓墜鏈哄睆骞曚娇鐢ㄦ椂闂存埅鍥捐瘑鍒姪鎵嬨€?鍒嗘瀽鐢ㄦ埛涓婁紶鐨勫睆骞曚娇鐢ㄦ椂闂存埅鍥撅紙iOS鎴朅ndroid鐨勫睆骞曚娇鐢ㄦ椂闂?鏁板瓧鍋ュ悍鎴浘锛夈€?
鎻愬彇浠ヤ笅淇℃伅骞惰繑鍥炰弗鏍糐SON鏍煎紡锛?{
    "total_minutes": 鏁板瓧锛堟€讳娇鐢ㄦ椂闀匡紝鍗曚綅鍒嗛挓锛?
    "top_category": "涓昏绫诲埆锛堝ū涔?绀句氦/宸ヤ綔/瀛︿範/娓告垙锛?,
    "apps": [
        {"name": "搴旂敤鍚嶇О", "minutes": 浣跨敤鍒嗛挓鏁皚
    ],
    "summary": "绠€鐭€荤粨"
}

娉ㄦ剰锛?1. iOS鎴浘閫氬父鏄剧ず"灞忓箷浣跨敤鏃堕棿"锛屾湁灏忔椂鍜屽垎閽?2. Android鎴浘閫氬父鏄剧ず"鏁板瓧鍋ュ悍"鎴?灞忓箷浣跨敤鏃堕棿"
3. 璇峰皢鎵€鏈夋椂闂存崲绠楁垚鍒嗛挓鏁?4. 濡傛灉鐪嬩笉娓呮垨鏃犳硶璇嗗埆锛岃繑鍥?total_minutes: 0"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "璇疯瘑鍒繖涓墜鏈哄睆骞曚娇鐢ㄦ椂闂存埅鍥撅紝鎻愬彇浣跨敤鏃堕暱淇℃伅锛岃繑鍥濲SON鏍煎紡"
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        result_text = response.choices[0].message.content
        print(f"AI璇嗗埆缁撴灉: {result_text}")

        # 灏濊瘯鎻愬彇JSON
        try:
            if '```json' in result_text:
                json_str = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                json_str = result_text.split('```')[1].split('```')[0].strip()
            elif '{' in result_text:
                start = result_text.index('{')
                end = result_text.rindex('}') + 1
                json_str = result_text[start:end]
            else:
                json_str = result_text

            result = json.loads(json_str)

            # 纭繚蹇呰瀛楁
            if 'total_minutes' not in result:
                result['total_minutes'] = 0
            if 'apps' not in result:
                result['apps'] = []

            return result

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON瑙ｆ瀽澶辫触: {e}")
            return {
                "total_minutes": 0,
                "error": "璇嗗埆缁撴灉瑙ｆ瀽澶辫触锛岃鎵嬪姩杈撳叆",
                "raw_text": result_text[:200] if result_text else ""
            }

    except Exception as e:
        print(f"AI璇嗗埆寮傚父: {e}")
        return {
            "total_minutes": 0,
            "error": f"璇嗗埆鏈嶅姟鏆傛椂涓嶅彲鐢? {str(e)[:50]}"
        }


@app.get("/api/phone-usage/stats/{username}")
async def get_phone_usage_stats(username: str, days: int = 7):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 鎸夊垎绫荤粺璁?
    c.execute('''SELECT category, SUM(usage_minutes), COUNT(id)
                FROM Phone_Usage WHERE username = ?
                AND report_date >= date('now', ?)
                GROUP BY category''',
              (username, f'-{days} days'))
    stats = [{"category": r[0], "total_minutes": r[1] or 0, "count": r[2]} for r in c.fetchall()]
    # 鎬昏
    c.execute('''SELECT SUM(usage_minutes) FROM Phone_Usage
                WHERE username = ? AND report_date >= date('now', ?)''',
              (username, f'-{days} days'))
    total = c.fetchone()[0] or 0
    conn.close()
    return {"stats": stats, "total_minutes": total, "period_days": days}


# ================= 馃幆 浠诲姟AI璇勫垎妯″潡 =================

def ai_score_task(task_content: str, proof_url: str = "") -> tuple:
    """Internal helper docstring."""
    DASHSCOPE_API_KEY = "sk-10dee7815be045a4a871e396adc6219d"
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    prompt = f"""
    銆愪换鍔″唴瀹广€戯細
    {task_content}

    銆愬畬鎴愯瘉鏄庛€戯紙濡傛湁鍥剧墖/閾炬帴锛夛細
    {proof_url if proof_url else "鏃犻澶栬瘉鏄庢潗鏂?}

    銆愯瘎鍒嗘爣鍑嗐€戯細
    璇锋牴鎹换鍔＄殑鎻忚堪鍚堢悊绋嬪害銆佸畬鎴愰毦搴﹂浼帮紝缁欏嚭涓€涓?0-100 鐨勫畬鎴愯川閲忓垎鏁般€?    鍚屾椂缁欏嚭绠€鐭殑榧撳姳鎬ц瘎璇紙1-2鍙ヨ瘽锛夈€?
    蹇呴』涓ユ牸杩斿洖濡備笅 JSON 鏍煎紡锛?    {{ "score": 85.0, "feedback": "瀹屾垚寰楀緢妫掞紒缁х画淇濇寔锛? }}
    """

    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "浣犳槸涓€浣嶆俯鍜岀殑瀛︿範鏁欑粌锛岃礋璐ｈ瘎浠峰鐢熺殑浠诲姟瀹屾垚鎯呭喌銆傚繀椤昏緭鍑?JSON銆?},
                {"role": "user", "content": prompt}
            ]
        )
        res = json.loads(response.choices[0].message.content)
        return res.get("score", 50), res.get("feedback", "璇勪环鐢熸垚涓?..")
    except Exception as e:
        print(f"AI璇勫垎鍑洪敊: {e}")
        return 50, "AI鏆傛椂鏃犳硶璇勪环锛岄粯璁ょ粰50鍒嗛紦鍔卞垎"


def check_and_trigger_drop(username: str, event_type: str, score: float = 0) -> dict:
    """Internal helper docstring."""
    # 鎺夎惤姒傜巼閰嶇疆
    DROP_RATES = {
        "focus_complete": {"common": 0.80, "rare": 0.18, "epic": 0.02},
        "task_score": {"common": 0.60, "rare": 0.35, "epic": 0.05}
    }

    # 鏍规嵁浜嬩欢绫诲瀷鍐冲畾鏄惁鎺夎惤
    drop_chance = 0.3 if event_type == "focus_complete" else 0.5 if event_type == "task_score" else 0
    if event_type == "task_score" and score < 80:
        return None  # 璇勫垎浣庝簬80涓嶆帀钀?
    if random.random() > drop_chance:
        return None

    # 鍐冲畾绋€鏈夊害
    rates = DROP_RATES.get(event_type, DROP_RATES["focus_complete"])
    roll = random.random()
    cumulative = 0
    selected_rarity = "common"

    for rarity, rate in rates.items():
        cumulative += rate
        if roll < cumulative:
            selected_rarity = rarity
            break

    # 浠庡搴旂█鏈夊害涓殢鏈洪€夋嫨閬撳叿
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, item_code, name, rarity FROM Items WHERE rarity = ? ORDER BY RANDOM() LIMIT 1",
              (selected_rarity,))
    item = c.fetchone()

    if not item:
        conn.close()
        return None

    item_id, item_code, name, rarity = item

    # 娣诲姞鍒扮敤鎴疯儗鍖?
    c.execute('''SELECT id, quantity FROM User_Items WHERE username = ? AND item_id = ?''',
              (username, item_id))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE User_Items SET quantity = quantity + 1 WHERE id = ?", (existing[0],))
    else:
        c.execute('''INSERT INTO User_Items (username, item_id, quantity, source)
                    VALUES (?, ?, 1, ?)''', (username, item_id, event_type))

    conn.commit()
    conn.close()

    return {"item_id": item_id, "item_code": item_code, "name": name, "rarity": rarity}


@app.post("/api/tasks/{task_id}/score")
async def score_task_with_ai(task_id: int, data: TaskScoreRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇浠诲姟鍐呭
    c.execute("SELECT content, is_completed FROM Todo_Tasks WHERE id = ? AND username = ?",
              (task_id, data.username))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="浠诲姟涓嶅瓨鍦?)

    task_content, is_completed = row
    if not is_completed:
        raise HTTPException(status_code=400, detail="浠诲姟灏氭湭瀹屾垚锛屾棤娉曡瘎鍒?)

    # 璋冪敤 AI 璇勫垎
    ai_score, ai_feedback = ai_score_task(task_content, data.proof_url)

    # 鏇存柊浠诲姟璇勫垎
    c.execute('''UPDATE Todo_Tasks
                SET ai_score = ?, proof_url = ?, score_updated_at = CURRENT_TIMESTAMP, ai_feedback = ?
                WHERE id = ?''',
              (ai_score, data.proof_url, ai_feedback, task_id))

    # 妫€鏌ユ槸鍚﹁Е鍙戦亾鍏锋帀钀?    bonus_item = check_and_trigger_drop(data.username, 'task_score', ai_score)

    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "ai_score": ai_score,
        "ai_feedback": ai_feedback,
        "bonus_item": bonus_item
    }


# ================= 馃巵 閬撳叿绯荤粺妯″潡 =================
@app.get("/api/items/inventory/{username}")
async def get_user_inventory(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT ui.item_id, i.item_code, i.name, i.description, i.rarity, ui.quantity, i.effect_type
                FROM User_Items ui
                JOIN Items i ON ui.item_id = i.id
                WHERE ui.username = ? AND ui.quantity > 0''',
              (username,))
    items = [{
        "item_id": r[0],
        "item_code": r[1],
        "name": r[2],
        "description": r[3],
        "rarity": r[4],
        "quantity": r[5],
        "effect_type": r[6]
    } for r in c.fetchall()]
    conn.close()
    return {"items": items, "total_types": len(items)}


@app.post("/api/items/use")
async def use_item(data: ItemUseRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ラ亾鍏锋暟閲?
    c.execute("SELECT ui.id, ui.quantity, i.name, i.effect_type, i.effect_value FROM User_Items ui JOIN Items i ON ui.item_id = i.id WHERE ui.username = ? AND ui.item_id = ?",
              (data.username, data.item_id))
    row = c.fetchone()
    if not row or row[1] < 1:
        raise HTTPException(status_code=400, detail="閬撳叿鏁伴噺涓嶈冻")

    effect_type = row[3]
    effect_value = row[4]

    # 鎵ｅ噺閬撳叿
    c.execute("UPDATE User_Items SET quantity = quantity - 1 WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()

    return {
        "message": "閬撳叿浣跨敤鎴愬姛",
        "effect_type": effect_type,
        "effect_value": effect_value
    }


@app.get("/api/items/definitions")
async def get_item_definitions():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT item_code, name, description, rarity, effect_type FROM Items")
    items = [{
        "item_code": r[0],
        "name": r[1],
        "description": r[2],
        "rarity": r[3],
        "effect_type": r[4]
    } for r in c.fetchall()]
    conn.close()
    return {"items": items}


# ================= 馃尡 宀涘笨鎴愰暱绯荤粺妯″潡 =================

def get_or_create_growth(username: str) -> dict:
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT username, focus_energy, total_focus_minutes, streak_days, last_active_date, diamonds, sunshine, coins FROM User_Growth WHERE username = ?",
              (username,))
    row = c.fetchone()

    if not row:
        # 鍒涘缓鏂扮敤鎴锋垚闀胯褰?
        c.execute('''INSERT INTO User_Growth (username, focus_energy, total_focus_minutes, streak_days, diamonds, sunshine, coins)
                    VALUES (?, 0, 0, 0, 50, 50, 200)''', (username,))
        conn.commit()
        result = {
            "username": username,
            "focus_energy": 0,
            "total_focus_minutes": 0,
            "streak_days": 0,
            "last_active_date": None,
            "diamonds": 50,
            "sunshine": 50,
            "coins": 200
        }
    else:
        result = {
            "username": row[0],
            "focus_energy": row[1],
            "total_focus_minutes": row[2],
            "streak_days": row[3],
            "last_active_date": row[4],
            "diamonds": max(row[5] or 0, row[6] or 0),
            "sunshine": row[6] or 0,
            "coins": row[7] or 0
        }

    conn.close()
    return result


@app.get("/api/growth/{username}")
async def get_user_growth(username: str):
    """Internal helper docstring."""
    growth = get_or_create_growth(username)
    # 绛夌骇鐢变笓娉ㄦ椂闀胯绠楋細姣?0鍒嗛挓鍗囦竴绾?    level = max(1, growth["total_focus_minutes"] // 60)
    return {
        "growth": growth,
        "level": level
    }


@app.post("/api/growth/add-energy")
async def add_focus_energy(data: GrowthAddExp):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛瀛樺湪
    get_or_create_growth(data.username)

    # 娣诲姞鑳介噺
    c.execute('''UPDATE User_Growth
                SET focus_energy = focus_energy + ?
                WHERE username = ?''',
              (data.exp_amount, data.username))

    # 鑾峰彇鏂扮殑鑳介噺鍊?
    c.execute("SELECT focus_energy FROM User_Growth WHERE username = ?", (data.username,))
    new_energy = c.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "energy_gained": data.exp_amount,
        "new_energy": new_energy
    }


@app.post("/api/growth/check-streak")
async def check_streak(data: GrowthCheckStreak):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛瀛樺湪
    get_or_create_growth(data.username)

    # 鑾峰彇涓婃娲昏穬鏃ユ湡
    c.execute("SELECT last_active_date, streak_days FROM User_Growth WHERE username = ?",
              (data.username,))
    row = c.fetchone()
    last_active, streak = row[0], row[1]

    from datetime import datetime

    today = datetime.now().date()
    new_streak = streak

    if last_active:
        last_date = datetime.strptime(last_active, "%Y-%m-%d").date()
        days_diff = (today - last_date).days

        if days_diff == 0:
            # 浠婂ぉ宸茬粡绛惧埌杩?            pass
        elif days_diff == 1:
            # 杩炵画绛惧埌
            new_streak = streak + 1
        else:
            # 涓柇浜?            new_streak = 1
    else:
        # 棣栨绛惧埌
        new_streak = 1

    # 鏇存柊鏁版嵁
    c.execute('''UPDATE User_Growth
                SET streak_days = ?, last_active_date = ?
                WHERE username = ?''',
              (new_streak, today.strftime("%Y-%m-%d"), data.username))

    conn.commit()
    conn.close()

    return {
        "streak_days": new_streak,
        "streak_increased": new_streak > streak
    }


@app.post("/api/growth/update-stats")
async def update_growth_stats(data: dict):
    """Internal helper docstring."""
    username = data.get("username")
    focus_minutes = data.get("focus_minutes", 0)

    if not username:
        raise HTTPException(status_code=400, detail="username required")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛瀛樺湪
    get_or_create_growth(username)

    c.execute('''UPDATE User_Growth
                SET total_focus_minutes = total_focus_minutes + ?
                WHERE username = ?''',
              (focus_minutes, username))

    conn.commit()
    conn.close()

    return {"message": "缁熻宸叉洿鏂?}


@app.post("/api/growth/update-discipline")
async def update_discipline_score(data: dict):
    """Internal helper docstring."""
    username = data.get("username")
    phone_minutes = data.get("phone_minutes", 0)

    if not username:
        raise HTTPException(status_code=400, detail="username required")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛瀛樺湪
    get_or_create_growth(username)

    # 鑷緥鎸囨暟璁＄畻锛氭墜鏈轰娇鐢ㄨ秺灏戝垎鏁拌秺楂?    # 鍩哄噯锛氭瘡澶?0鍒嗛挓浠ヤ笅鏄弧鍒嗚秼鍔匡紝瓒呰繃240鍒嗛挓鍒欐墸鍒?    base_score = 100 - (phone_minutes / 60 * 15)  # 姣忓皬鏃舵墸15鍒?    base_score = max(0, min(100, base_score))  # 闄愬埗鍦?-100

    c.execute('''UPDATE User_Growth
                SET discipline_score = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = ?''',
              (base_score, username))

    conn.commit()
    conn.close()

    return {"discipline_score": base_score}


# ================= 馃搳 缁熻涓庢帓琛屾妯″潡 =================

@app.get("/api/stats/{username}")
async def get_user_stats(username: str, period: int = 7):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇姣忔棩缁熻
    c.execute('''SELECT stat_date, focus_minutes, tasks_completed, exp_gained, phone_minutes
                FROM User_Daily_Stats
                WHERE username = ? AND stat_date >= date('now', ?)
                ORDER BY stat_date ASC''',
              (username, f'-{period} days'))
    daily_stats = [{
        "stat_date": row[0],
        "focus_minutes": row[1],
        "tasks_completed": row[2],
        "exp_gained": row[3],
        "phone_minutes": row[4]
    } for row in c.fetchall()]

    # 鑾峰彇姹囨€绘暟鎹?
    c.execute('''SELECT
                COALESCE(SUM(focus_minutes), 0),
                COALESCE(SUM(tasks_completed), 0),
                COALESCE(SUM(exp_gained), 0),
                COALESCE(AVG(phone_minutes), 50)
                FROM User_Daily_Stats
                WHERE username = ? AND stat_date >= date('now', ?)''',
              (username, f'-{period} days'))
    summary_row = c.fetchone()

    # 鑾峰彇杩炵画澶╂暟
    c.execute("SELECT streak_days FROM User_Growth WHERE username = ?", (username,))
    streak_row = c.fetchone()

    conn.close()

    return {
        "daily_stats": daily_stats,
        "summary": {
            "total_focus_minutes": summary_row[0] or 0,
            "total_tasks": summary_row[1] or 0,
            "total_exp": summary_row[2] or 0,
            "avg_discipline": 100 - (summary_row[3] or 50) / 60 * 15,
            "streak_days": streak_row[0] if streak_row else 0
        }
    }


@app.get("/api/leaderboard")
async def get_leaderboard(type: str = 'global', category: str = 'exp', period: str = 'weekly'):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鏍规嵁鍒嗙被閫夋嫨鎺掑悕瀛楁
    order_field = {
        'exp': 'exp DESC',
        'focus': 'total_focus_minutes DESC',
        'streak': 'streak_days DESC'
    }.get(category, 'exp DESC')

    c.execute(f'''SELECT username, exp, level, total_focus_minutes, streak_days
                  FROM User_Growth
                  ORDER BY {order_field}
                  LIMIT 100''')

    rankings = []
    for index, row in enumerate(c.fetchall()):
        score = {
            'exp': row[1],
            'focus': row[3],
            'streak': row[4]
        }.get(category, row[1])

        rankings.append({
            "rank": index + 1,
            "username": row[0],
            "level": row[2],
            "score": score
        })

    conn.close()

    return {
        "rankings": rankings,
        "user_rank": None,  # TODO: 鏍规嵁褰撳墠鐢ㄦ埛璁＄畻
        "type": type,
        "category": category,
        "period": period
    }


# ================= 馃弳 鎴愬氨绯荤粺妯″潡 =================

@app.get("/api/achievements")
async def get_all_achievements():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, achievement_code, name, description, icon, category,
                        requirement_type, requirement_value, exp_reward
                 FROM Achievements ORDER BY category, requirement_value''')
    achievements = [{
        "id": row[0],
        "achievement_code": row[1],
        "name": row[2],
        "description": row[3],
        "icon": row[4],
        "category": row[5],
        "requirement_type": row[6],
        "requirement_value": row[7],
        "exp_reward": row[8]
    } for row in c.fetchall()]
    conn.close()
    return {"achievements": achievements}


@app.get("/api/achievements/{username}")
async def get_user_achievements(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT ua.achievement_id, a.achievement_code, a.name, a.icon, a.exp_reward, ua.unlocked_at
                 FROM User_Achievements ua
                 JOIN Achievements a ON ua.achievement_id = a.id
                 WHERE ua.username = ?
                 ORDER BY ua.unlocked_at DESC''', (username,))
    unlocked = [{
        "achievement_id": row[0],
        "achievement_code": row[1],
        "name": row[2],
        "icon": row[3],
        "exp_reward": row[4],
        "unlocked_at": row[5]
    } for row in c.fetchall()]
    conn.close()
    return {"unlocked": unlocked}


# ================= 馃彎锔?宀涘笨瑁呴グ妯″潡 =================

@app.get("/api/island/decorations")
async def get_island_decorations():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, decoration_code, name, type, model_data, rarity, cost
                 FROM Island_Decorations ORDER BY cost ASC''')
    decorations = [{
        "id": row[0],
        "decoration_code": row[1],
        "name": row[2],
        "type": row[3],
        "model_data": row[4],
        "rarity": row[5],
        "cost": row[6]
    } for row in c.fetchall()]
    conn.close()
    return {"decorations": decorations}


@app.post("/api/island/decorations/buy")
async def buy_decoration(data: dict):
    """Internal helper docstring."""
    username = data.get("username")
    decoration_id = data.get("decoration_id")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇瑁呴グ浠锋牸
    c.execute("SELECT cost, name FROM Island_Decorations WHERE id = ?", (decoration_id,))
    decor_row = c.fetchone()
    if not decor_row:
        conn.close()
        raise HTTPException(status_code=404, detail="瑁呴グ鍝佷笉瀛樺湪")

    cost, name = decor_row

    # 妫€鏌ョ敤鎴风粡楠屽€?
    c.execute("SELECT exp FROM User_Growth WHERE username = ?", (username,))
    user_row = c.fetchone()
    if not user_row or user_row[0] < cost:
        conn.close()
        raise HTTPException(status_code=400, detail="缁忛獙鍊间笉瓒?)

    # 鎵ｅ噺缁忛獙
    c.execute("UPDATE User_Growth SET exp = exp - ? WHERE username = ?", (cost, username))

    # 娣诲姞鍒扮敤鎴疯楗?
    c.execute('''INSERT OR IGNORE INTO User_Decorations (username, decoration_id)
                VALUES (?, ?)''', (username, decoration_id))

    conn.commit()
    conn.close()

    return {"success": True, "message": f"鎴愬姛璐拱 {name}"}


@app.get("/api/island/skins")
async def get_island_skins():
    """Internal helper docstring."""
    # 鏆傛椂杩斿洖妯℃嫙鏁版嵁
    return {
        "skins": [
            {"id": 1, "skin_code": "spring", "name": "鏄ユ棩鑺卞洯", "description": "绮夎壊妯辫姳涓婚", "rarity": "rare", "cost": 500},
            {"id": 2, "skin_code": "summer", "name": "澶忔棩娴锋哗", "description": "鐑甫娴峰矝涓婚", "rarity": "epic", "cost": 800},
            {"id": 3, "skin_code": "autumn", "name": "绉嬫棩鏋灄", "description": "閲戦粍鏋彾涓婚", "rarity": "rare", "cost": 500},
            {"id": 4, "skin_code": "winter", "name": "鍐棩闆櫙", "description": "鍐伴洩绔ヨ瘽涓婚", "rarity": "legendary", "cost": 1500},
        ]
    }


@app.post("/api/island/skins/buy")
async def buy_skin(data: dict):
    """Internal helper docstring."""
    username = data.get("username")
    skin_id = data.get("skin_id")

    # 鐨偆浠锋牸琛?    skins = {
        1: {"name": "鏄ユ棩鑺卞洯", "cost": 500},
        2: {"name": "澶忔棩娴锋哗", "cost": 800},
        3: {"name": "绉嬫棩鏋灄", "cost": 500},
        4: {"name": "鍐棩闆櫙", "cost": 1500}
    }

    if skin_id not in skins:
        raise HTTPException(status_code=404, detail="鐨偆涓嶅瓨鍦?)

    skin = skins[skin_id]
    cost = skin["cost"]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鍒涘缓鐨偆琛紙濡傛灉涓嶅瓨鍦級
    c.execute('''CREATE TABLE IF NOT EXISTS User_Skins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        skin_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 0,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (username, skin_id)
    )''')

    # 妫€鏌ユ槸鍚﹀凡鎷ユ湁
    c.execute("SELECT id FROM User_Skins WHERE username = ? AND skin_id = ?", (username, skin_id))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="宸叉嫢鏈夎鐨偆")

    # 妫€鏌ョ粡楠屽€?
    c.execute("SELECT exp FROM User_Growth WHERE username = ?", (username,))
    user_row = c.fetchone()
    if not user_row or user_row[0] < cost:
        conn.close()
        raise HTTPException(status_code=400, detail="缁忛獙鍊间笉瓒?)

    # 鎵ｅ噺缁忛獙
    c.execute("UPDATE User_Growth SET exp = exp - ? WHERE username = ?", (cost, username))

    # 娣诲姞鐨偆
    c.execute("INSERT INTO User_Skins (username, skin_id) VALUES (?, ?)", (username, skin_id))

    # 鑾峰彇鏇存柊鍚庣殑缁忛獙鍊?
    c.execute("SELECT exp FROM User_Growth WHERE username = ?", (username,))
    new_exp = c.fetchone()[0]

    conn.commit()
    conn.close()

    return {"success": True, "message": f"鎴愬姛璐拱 {skin['name']}锛?, "new_exp": new_exp}


@app.get("/api/island/skins/{username}")
async def get_user_skins(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鍒涘缓鐨偆琛紙濡傛灉涓嶅瓨鍦級
    c.execute('''CREATE TABLE IF NOT EXISTS User_Skins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        skin_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 0,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (username, skin_id)
    )''')

    c.execute("SELECT skin_id FROM User_Skins WHERE username = ?", (username,))
    owned_skins = [row[0] for row in c.fetchall()]
    conn.close()

    return {"owned_skins": owned_skins}


# ================= 馃攱 FocusPort 涓撴敞鑳介噺妯″潡 =================

class FocusEnergyAdd(BaseModel):
    username: str
    duration: int  # 涓撴敞鏃堕暱锛堝垎閽燂級

class ShopBuyRequest(BaseModel):
    username: str
    item_id: int

class PlaceItemRequest(BaseModel):
    username: str
    item_id: int
    position_x: float
    position_z: float
    rotation: float = 0

@app.get("/api/focus-energy/{username}")
async def get_focus_energy(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT focus_energy FROM User_Growth WHERE username = ?", (username,))
    row = c.fetchone()
    focus_energy = row[0] if row and row[0] else 0
    conn.close()
    return {"focus_energy": focus_energy}

@app.post("/api/focus-energy/add")
async def add_focus_energy(data: FocusEnergyAdd):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛瀛樺湪
    get_or_create_growth(data.username)

    # 璁＄畻鑳介噺锛?鍒嗛挓=1鑳介噺锛屾渶浣?锛?    energy_gained = max(5, data.duration)

    # 鏇存柊鑳介噺
    c.execute('''UPDATE User_Growth
                SET focus_energy = focus_energy + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = ?''',
              (energy_gained, data.username))

    # 鑾峰彇鏂扮殑鑳介噺鍊?
    c.execute("SELECT focus_energy FROM User_Growth WHERE username = ?", (data.username,))
    new_energy = c.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "success": True,
        "energy_gained": energy_gained,
        "new_energy": new_energy,
        "message": f"鑾峰緱 {energy_gained} 鐐逛笓娉ㄨ兘閲?
    }

@app.get("/api/shop/items")
async def get_shop_items():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, item_code, name, type, icon, model_path, price, rarity, description
                 FROM Shop_Items ORDER BY price ASC''')
    items = [{
        "id": row[0],
        "item_code": row[1],
        "name": row[2],
        "type": row[3],
        "icon": row[4],
        "model_path": row[5],
        "price": row[6],
        "rarity": row[7],
        "description": row[8]
    } for row in c.fetchall()]
    conn.close()
    return {"items": items}

@app.post("/api/shop/buy")
async def buy_shop_item(data: ShopBuyRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇鐗╁搧淇℃伅
    c.execute("SELECT id, name, price FROM Shop_Items WHERE id = ?", (data.item_id,))
    item = c.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="鐗╁搧涓嶅瓨鍦?)

    item_id, name, price = item

    # 妫€鏌ョ敤鎴疯兘閲?
    c.execute("SELECT focus_energy FROM User_Growth WHERE username = ?", (data.username,))
    user_row = c.fetchone()
    if not user_row or user_row[0] < price:
        conn.close()
        raise HTTPException(status_code=400, detail=f"涓撴敞鑳介噺涓嶈冻锛侀渶瑕?{price} 鑳介噺")

    # 鎵ｅ噺鑳介噺
    c.execute("UPDATE User_Growth SET focus_energy = focus_energy - ? WHERE username = ?",
              (price, data.username))

    # 娣诲姞鍒拌儗鍖?
    c.execute('''INSERT INTO User_Inventory (username, item_id, status)
                VALUES (?, ?, 'owned')''', (data.username, item_id))

    # 鑾峰彇鏂扮殑鑳介噺鍊?
    c.execute("SELECT focus_energy FROM User_Growth WHERE username = ?", (data.username,))
    new_energy = c.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"鎴愬姛璐拱 {name}锛?,
        "new_energy": new_energy
    }

@app.get("/api/inventory/{username}")
async def get_user_inventory_fc(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT ui.id, ui.item_id, si.item_code, si.name, si.type, si.icon,
                        si.model_path, si.rarity, ui.status
                 FROM User_Inventory ui
                 JOIN Shop_Items si ON ui.item_id = si.id
                 WHERE ui.username = ? AND ui.status = 'owned'
                 ORDER BY ui.created_at DESC''', (username,))
    items = [{
        "inventory_id": row[0],
        "item_id": row[1],
        "item_code": row[2],
        "name": row[3],
        "type": row[4],
        "icon": row[5],
        "model_path": row[6],
        "rarity": row[7],
        "status": row[8]
    } for row in c.fetchall()]
    conn.close()
    return {"items": items}

@app.get("/api/island/infrastructure/{username}")
async def get_island_infrastructure(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT ii.id, ii.item_id, si.item_code, si.name, si.type, si.icon,
                        si.model_path, ii.position_x, ii.position_z, ii.rotation
                 FROM Island_Infrastructure ii
                 JOIN Shop_Items si ON ii.item_id = si.id
                 WHERE ii.username = ?
                 ORDER BY ii.placed_at ASC''', (username,))
    items = [{
        "id": row[0],
        "item_id": row[1],
        "item_code": row[2],
        "name": row[3],
        "type": row[4],
        "icon": row[5],
        "model_path": row[6],
        "position_x": row[7],
        "position_z": row[8],
        "rotation": row[9]
    } for row in c.fetchall()]
    conn.close()
    return {"items": items}

@app.post("/api/island/place")
async def place_island_item(data: PlaceItemRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ョ墿鍝佹槸鍚﹀湪鑳屽寘涓笖涓?owned 鐘舵€?
    c.execute('''SELECT ui.id, si.name FROM User_Inventory ui
                 JOIN Shop_Items si ON ui.item_id = si.id
                 WHERE ui.username = ? AND ui.item_id = ? AND ui.status = 'owned' ''',
              (data.username, data.item_id))
    item = c.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=400, detail="鐗╁搧涓嶅湪鑳屽寘涓垨宸叉斁缃?)

    inventory_id, name = item

    # 娣诲姞鍒板矝灞胯鏂?
    c.execute('''INSERT INTO Island_Infrastructure (username, item_id, position_x, position_z, rotation)
                VALUES (?, ?, ?, ?, ?)''',
              (data.username, data.item_id, data.position_x, data.position_z, data.rotation))

    # 鏇存柊鑳屽寘鐘舵€佷负 placed
    c.execute("UPDATE User_Inventory SET status = 'placed' WHERE id = ?", (inventory_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"鎴愬姛鏀剧疆 {name}锛?
    }

# ================= 馃搮 绛惧埌涓庢椿鍔ㄦā鍧?=================

@app.post("/api/checkin")
async def daily_checkin(data: dict):
    """Internal helper docstring."""
    username = data.get("username")
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ヤ粖鏃ユ槸鍚﹀凡绛惧埌
    c.execute("SELECT id, consecutive_day FROM Daily_Checkins WHERE username = ? AND checkin_date = ?",
              (username, today))
    existing = c.fetchone()

    if existing:
        conn.close()
        return {"already_checked": True, "consecutive_day": existing[1]}

    # 鑾峰彇鏄ㄥぉ绛惧埌璁板綍
    yesterday = datetime.now().strftime('%Y-%m-%d')  # 绠€鍖栵細瀹為檯搴旇鍑?澶?
    c.execute("SELECT consecutive_day FROM Daily_Checkins WHERE username = ? ORDER BY checkin_date DESC LIMIT 1",
              (username,))
    last_checkin = c.fetchone()

    consecutive_day = 1
    if last_checkin:
        consecutive_day = last_checkin[0] + 1

    # 鎻掑叆绛惧埌璁板綍
    c.execute('''INSERT INTO Daily_Checkins (username, checkin_date, consecutive_day)
                VALUES (?, ?, ?)''', (username, today, consecutive_day))

    # 璁＄畻濂栧姳 (杩炵画7澶╅澶栧鍔?
    base_exp = 10
    if consecutive_day % 7 == 0:
        base_exp += 50

    # 澧炲姞缁忛獙
    c.execute("UPDATE User_Growth SET exp = exp + ? WHERE username = ?", (base_exp, username))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "consecutive_day": consecutive_day,
        "reward_exp": base_exp,
        "message": f"绛惧埌鎴愬姛锛佽繛缁{consecutive_day}澶?
    }


@app.get("/api/checkin/{username}")
async def get_checkin_status(username: str):
    """Internal helper docstring."""
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT consecutive_day FROM Daily_Checkins WHERE username = ? AND checkin_date = ?",
              (username, today))
    today_row = c.fetchone()

    c.execute("SELECT MAX(consecutive_day) FROM Daily_Checkins WHERE username = ?", (username,))
    max_row = c.fetchone()

    conn.close()

    return {
        "today_checked": today_row is not None,
        "consecutive_day": today_row[0] if today_row else 0,
        "max_consecutive": max_row[0] if max_row else 0
    }


@app.get("/api/events")
async def get_events(active_only: bool = True):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if active_only:
        c.execute('''SELECT id, event_code, name, description, event_type, start_time, end_time,
                            reward_exp, is_active
                     FROM Events WHERE is_active = 1 AND end_time IS NULL OR end_time > datetime('now')''')
    else:
        c.execute('''SELECT id, event_code, name, description, event_type, start_time, end_time,
                            reward_exp, is_active
                     FROM Events''')

    events = [{
        "id": row[0],
        "event_code": row[1],
        "name": row[2],
        "description": row[3],
        "event_type": row[4],
        "start_time": row[5],
        "end_time": row[6],
        "reward_exp": row[7],
        "is_active": row[8]
    } for row in c.fetchall()]

    conn.close()
    return {"events": events}


# ================= 馃懃 濂藉弸绯荤粺妯″潡 =================

@app.post("/api/friends/request")
async def send_friend_request(data: dict):
    """Internal helper docstring."""
    user_username = data.get("user_username")
    friend_username = data.get("friend_username")

    if user_username == friend_username:
        raise HTTPException(status_code=400, detail="涓嶈兘娣诲姞鑷繁涓哄ソ鍙?)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ョ洰鏍囩敤鎴锋槸鍚﹀瓨鍦?
    c.execute("SELECT username FROM Users WHERE username = ?", (friend_username,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="鐢ㄦ埛涓嶅瓨鍦?)

    # 妫€鏌ユ槸鍚﹀凡鏄ソ鍙嬫垨宸插彂閫佽姹?
    c.execute('''SELECT status FROM Friendships
                WHERE (user_username = ? AND friend_username = ?)
                OR (user_username = ? AND friend_username = ?)''',
              (user_username, friend_username, friend_username, user_username))
    existing = c.fetchone()

    if existing:
        conn.close()
        if existing[0] == 'accepted':
            raise HTTPException(status_code=400, detail="宸茬粡鏄ソ鍙嬩簡")
        else:
            raise HTTPException(status_code=400, detail="濂藉弸璇锋眰宸插瓨鍦?)

    # 鍙戦€佸ソ鍙嬭姹?
    c.execute('''INSERT INTO Friendships (user_username, friend_username, status)
                VALUES (?, ?, 'pending')''', (user_username, friend_username))

    conn.commit()
    conn.close()

    return {"success": True, "message": "濂藉弸璇锋眰宸插彂閫?}


@app.get("/api/friends/{username}")
async def get_friends(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT friend_username, status, created_at
                FROM Friendships
                WHERE user_username = ? OR friend_username = ?''',
              (username, username))

    friends = [{
        "friend_username": row[0],
        "status": row[1],
        "created_at": row[2]
    } for row in c.fetchall()]

    conn.close()
    return {"friends": friends}


# ================= 馃 AI 鍔╂墜妯″潡 =================

class AIChatRequest(BaseModel):
    username: str
    message: str
    conversation_id: str = ""


@app.post("/api/ai/chat")
async def ai_chat(data: AIChatRequest):
    """Internal helper docstring."""
    DASHSCOPE_API_KEY = "sk-10dee7815be045a4a871e396adc6219d"
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        # 鑾峰彇鐢ㄦ埛鏁版嵁浣滀负涓婁笅鏂?        user_growth = get_or_create_growth(data.username)

        system_prompt = f"""浣犳槸涓€涓弸濂界殑瀛︿範鍔╂墜锛屽悕鍙?Focus"锛屾槸FocusPort涓撴敞宀涚殑AI鍔╂墜銆?鐢ㄦ埛 {data.username} 鐨勫綋鍓嶆暟鎹細
- 绛夌骇: {user_growth['level']}
- 缁忛獙鍊? {user_growth['exp']}
- 涓撴敞鏃堕暱: {user_growth['total_focus_minutes']}鍒嗛挓
- 杩炵画瀛︿範: {user_growth['streak_days']}澶?
璇风敤绠€鐭€佸弸濂界殑鏂瑰紡鍥炵瓟鐢ㄦ埛鐨勯棶棰橈紝缁欏嚭瀛︿範寤鸿銆傚洖澶嶈绠€娲佹湁娓╁害銆?""

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data.message}
            ]
        )

        reply = response.choices[0].message.content

        # 淇濆瓨瀵硅瘽璁板綍
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO AI_Chats (username, role, content) VALUES (?, ?, ?)''',
                  (data.username, 'user', data.message))
        c.execute('''INSERT INTO AI_Chats (username, role, content) VALUES (?, ?, ?)''',
                  (data.username, 'assistant', reply))
        conn.commit()
        conn.close()

        return {
            "reply": reply,
            "conversation_id": data.conversation_id,
            "suggestions": ["鍒嗘瀽鎴戠殑瀛︿範鏁版嵁", "缁欐垜瀛︿範寤鸿", "濡備綍鎻愰珮涓撴敞鍔?]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI鍥炲澶辫触: {str(e)}")


@app.get("/api/ai/history/{username}")
async def get_ai_history(username: str, limit: int = 20):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT role, content, created_at FROM AI_Chats
                WHERE username = ? ORDER BY created_at DESC LIMIT ?''',
              (username, limit))
    messages = [{
        "role": row[0],
        "content": row[1],
        "created_at": row[2]
    } for row in c.fetchall()]
    conn.close()
    return {"messages": list(reversed(messages))}


@app.delete("/api/ai/history/{username}")
async def clear_ai_history(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM AI_Chats WHERE username = ?", (username,))
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    return {"success": True, "deleted_count": deleted_count, "message": f"宸叉竻绌?{deleted_count} 鏉″璇濊褰?}


@app.get("/api/ai/suggestions/{username}")
async def get_ai_suggestions(username: str):
    """Internal helper docstring."""
    user_growth = get_or_create_growth(username)

    suggestions = []

    if user_growth['streak_days'] < 7:
        suggestions.append({
            "type": "streak",
            "message": f"宸茶繛缁涔爗user_growth['streak_days']}澶╋紝鍧氭寔浣忥紒鐩爣鏄?澶?,
            "priority": "high"
        })

    if user_growth['total_focus_minutes'] < 60:
        suggestions.append({
            "type": "focus",
            "message": "浠婃棩涓撴敞鏃堕棿杈冨皯锛屽缓璁畬鎴?-2涓暘鑼勯挓",
            "priority": "medium"
        })

    if user_growth['discipline_score'] < 60:
        suggestions.append({
            "type": "discipline",
            "message": "鑷緥鎸囨暟鍋忎綆锛屾敞鎰忓噺灏戞墜鏈轰娇鐢?,
            "priority": "high"
        })

    return {"suggestions": suggestions}


# ================= 鈿旓笍 PK鎸戞垬绯荤粺 =================
class PKCreate(BaseModel):
    creator: str
    opponent: str
    type: str  # focus, tasks, exp
    duration: int = 24  # 灏忔椂
    target_value: int = 60


class PKAction(BaseModel):
    pk_id: int
    username: str


@app.post("/api/pk/create")
async def create_pk(data: PKCreate):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ュ鎵嬫槸鍚﹀瓨鍦?
    c.execute("SELECT username FROM Users WHERE username=?", (data.opponent,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="瀵规墜鐢ㄦ埛涓嶅瓨鍦?)

    # 妫€鏌ユ槸鍚﹀凡鏈夎繘琛屼腑鐨凱K
    c.execute('''SELECT id FROM PK_Challenges
                WHERE ((creator=? AND opponent=?) OR (creator=? AND opponent=?))
                AND status IN ('pending', 'active')''',
              (data.creator, data.opponent, data.opponent, data.creator))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="浣犱滑涔嬮棿宸叉湁杩涜涓殑PK")

    # 璁＄畻缁撴潫鏃堕棿
    from datetime import timedelta
    end_time = (datetime.now() + timedelta(hours=data.duration)).strftime('%Y-%m-%d %H:%M:%S')

    # 鍒涘缓PK
    winner_exp = 50 + data.duration * 2  # 鍩虹50 + 鏃堕暱濂栧姳
    c.execute('''INSERT INTO PK_Challenges
                (creator, opponent, type, duration, target_value, status, end_time, winner_exp)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)''',
              (data.creator, data.opponent, data.type, data.duration, data.target_value, end_time, winner_exp))
    pk_id = c.lastrowid
    conn.commit()
    conn.close()

    return {"success": True, "pk_id": pk_id, "message": "PK鎸戞垬宸插彂閫?}


@app.post("/api/pk/accept")
async def accept_pk(data: PKAction):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT creator, opponent, status, end_time FROM PK_Challenges WHERE id=?", (data.pk_id,))
    pk = c.fetchone()
    if not pk:
        conn.close()
        raise HTTPException(status_code=404, detail="PK涓嶅瓨鍦?)

    if pk[2] != 'pending':
        conn.close()
        raise HTTPException(status_code=400, detail="PK鐘舵€佷笉姝ｇ‘")

    if data.username != pk[1]:  # opponent
        conn.close()
        raise HTTPException(status_code=403, detail="鍙湁琚寫鎴樿€呮墠鑳芥帴鍙?)

    # 鏇存柊鐘舵€佷负杩涜涓?    started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE PK_Challenges SET status='active', started_at=? WHERE id=?",
              (started_at, data.pk_id))
    conn.commit()
    conn.close()

    return {"success": True, "message": "PK宸插紑濮?}


@app.post("/api/pk/decline")
async def decline_pk(data: PKAction):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT opponent, status FROM PK_Challenges WHERE id=?", (data.pk_id,))
    pk = c.fetchone()
    if not pk:
        conn.close()
        raise HTTPException(status_code=404, detail="PK涓嶅瓨鍦?)

    if pk[1] != 'pending':
        conn.close()
        raise HTTPException(status_code=400, detail="PK鐘舵€佷笉姝ｇ‘")

    c.execute("UPDATE PK_Challenges SET status='declined' WHERE id=?", (data.pk_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "宸叉嫆缁濇寫鎴?}


@app.get("/api/pk/active/{username}")
async def get_active_pks(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 鑾峰彇寰呭鐞嗙殑閭€璇凤紙鍒汉鍙戠粰鎴戠殑锛?
    c.execute('''SELECT id, creator, type, duration, end_time, winner_exp
                FROM PK_Challenges
                WHERE opponent=? AND status='pending'
                ORDER BY created_at DESC''', (username,))
    pending = []
    for row in c.fetchall():
        pending.append({
            "id": row[0],
            "creator": row[1],
            "type": row[2],
            "duration": row[3],
            "end_time": row[4],
            "winner_exp": row[5]
        })

    # 鑾峰彇杩涜涓殑PK
    c.execute('''SELECT id, creator, opponent, type, duration, end_time, winner_exp, creator_score, opponent_score, started_at
                FROM PK_Challenges
                WHERE (creator=? OR opponent=?) AND status='active'
                ORDER BY created_at DESC''', (username, username))
    active = []
    for row in c.fetchall():
        is_creator = row[1] == username
        opponent = row[2] if is_creator else row[1]
        my_score = row[7] if is_creator else row[8]
        opponent_score = row[8] if is_creator else row[7]

        # 璁＄畻瀹炴椂鍒嗘暟
        if row[3] == 'focus':
            c.execute("SELECT COALESCE(SUM(duration), 0) FROM Study_Sessions WHERE username=? AND start_time >= ?",
                      (row[1], row[9] or row[6]))
            creator_focus = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(duration), 0) FROM Study_Sessions WHERE username=? AND start_time >= ?",
                      (row[2], row[9] or row[6]))
            opponent_focus = c.fetchone()[0]
            my_score = creator_focus if is_creator else opponent_focus
            opponent_score = opponent_focus if is_creator else creator_focus

        active.append({
            "id": row[0],
            "opponent": opponent,
            "type": row[3],
            "duration": row[4],
            "end_time": row[5],
            "winner_exp": row[6],
            "my_score": my_score,
            "opponent_score": opponent_score
        })

    # 鑾峰彇鍘嗗彶璁板綍
    c.execute('''SELECT id, creator, opponent, type, status, winner, winner_exp, creator_score, opponent_score
                FROM PK_Challenges
                WHERE (creator=? OR opponent=?) AND status IN ('completed', 'declined')
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 20''', (username, username))
    history = []
    for row in c.fetchall():
        is_creator = row[1] == username
        opponent = row[2] if is_creator else row[1]
        my_score = row[7] if is_creator else row[8]
        opponent_score = row[8] if is_creator else row[7]

        result = 'draw'
        exp_gained = 0
        if row[4] == 'completed':
            if row[5] == username:
                result = 'win'
                exp_gained = row[6]
            elif row[5] == opponent:
                result = 'lose'
            elif row[5] is None:
                result = 'draw'
        elif row[4] == 'declined':
            result = 'declined'

        history.append({
            "id": row[0],
            "opponent": opponent,
            "type": row[3],
            "result": result,
            "my_score": my_score,
            "opponent_score": opponent_score,
            "exp_gained": exp_gained
        })

    # 妫€鏌ュ苟缁撴潫杩囨湡鐨凱K
    c.execute('''SELECT id, creator, opponent, creator_score, opponent_score, winner_exp
                FROM PK_Challenges
                WHERE status='active' AND end_time < ?''', (now,))
    expired = c.fetchall()
    for pk in expired:
        winner = None
        if pk[3] > pk[4]:
            winner = pk[1]
        elif pk[4] > pk[3]:
            winner = pk[2]
        # 濡傛灉骞冲眬鎴栭兘鏈夊垎鏁帮紝涓嶈winner

        c.execute("UPDATE PK_Challenges SET status='completed', winner=?, completed_at=? WHERE id=?",
                  (winner, now, pk[0]))

        # 缁欒儨鑰呭姞缁忛獙
        if winner:
            c.execute("UPDATE User_Growth SET exp = exp + ? WHERE username=?", (pk[5], winner))

    if expired:
        conn.commit()

    conn.close()

    return {"pending": pending, "active": active, "history": history}


# ================= 馃拵 闄剁煶鑾峰彇/璐拱 API =================
@app.get("/api/shop/diamonds/{username}")
async def get_diamonds(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT diamonds FROM User_Growth WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return {"diamonds": row[0] if row else 0}


class DiamondsAddRequest(BaseModel):
    username: str
    amount: int


@app.post("/api/shop/diamonds/add")
async def add_diamonds(data: DiamondsAddRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE User_Growth SET diamonds = diamonds + ? WHERE username = ?",
              (data.amount, data.username))
    c.execute("SELECT diamonds FROM User_Growth WHERE username = ?", (data.username,))
    new_diamonds = c.fetchone()[0]
    conn.commit()
    conn.close()
    return {"success": True, "diamonds": new_diamonds[0]}


class StudyRoomItemRequest(BaseModel):
    username: str
    item_id: int


class StudyRoomItem(BaseModel):
    id: int
    name: str
    type: str  # decoration / boost
    icon: str
    model_path: str
    price: int
    rarity: str
    description: str
    effect: str = None
    duration: int = None


@app.get("/api/studyroom/items")
async def get_studyroom_items():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, name, type, icon, model_path, price, rarity, description, effect, duration
                 FROM StudyRoom_Items ORDER BY rarity, price''')
    items = [{
        "id": row[0], "name": row[1], "type": row[2], "icon": row[3],
        "model_path": row[4], "price": row[5], "rarity": row[6],
        "description": row[7], "effect": row[8], "duration": row[9]
    } for row in c.fetchall()]
    conn.close()
    return {"items": items}


@app.post("/api/studyroom/buy")
async def buy_studyroom_item(data: StudyRoomItemRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇鐗╁搧淇℃伅
    c.execute("SELECT id, name, price, type FROM StudyRoom_Items WHERE id = ?", (data.item_id,))
    item = c.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="鍟嗗搧涓嶅瓨鍦?)


    item_id, name, price, item_type = item

    # 妫€鏌ョ敤鎴烽捇鐭?
    c.execute("SELECT diamonds FROM User_Growth WHERE username = ?", (data.username,))
    user_row = c.fetchone()
    if not user_row or user_row[0] < price:
        conn.close()
        raise HTTPException(status_code=400, detail=f"閽荤煶涓嶈冻锛侀渶瑕?{price} 闄剁煶")

    # 鎵ｅ噺閽荤煶
    c.execute("UPDATE User_Growth SET diamonds = diamonds - ? WHERE username = ?",
              (price, data.username))


    # 娣诲姞鍒拌儗鍖?    if item_type == 'decoration':
        c.execute('''INSERT INTO User_Inventory (username, item_id, status)
                    VALUES (?, ?, 'owned')''', (data.username, item_id))
    else:
        # 鍔熻兘閬撳叿
        c.execute('''INSERT INTO User_Items (username, item_id, quantity, source)
                    VALUES (?, ?, 1, 'studyroom')
                    ON CONFLICT(username, item_id) DO UPDATE SET quantity = quantity + 1''', (data.username, item_id))

    # 鑾峰彇鏂扮殑閽荤煶浣欓
    c.execute("SELECT diamonds FROM User_Growth WHERE username = ?", (data.username,))
    new_diamonds = c.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"鎴愬姛璐拱 {name}锛?,
        "diamonds": new_diamonds[0]
    }


# ============================================
# 馃尶 鏃跺厜娓╁ (Greenhouse) 绯荤粺 API
# ============================================

import uuid
from typing import Optional, List
from fastapi import WebSocket, WebSocketDisconnect

# --- 鏃跺厜娓╁鏁版嵁妯″瀷 ---
class GreenhouseCreate(BaseModel):
    name: str
    owner_username: str
    description: str = ""
    max_seats: int = 8
    is_public: bool = True
    password: str = ""
    theme: str = "garden"

class GreenhouseJoin(BaseModel):
    username: str
    password: str = ""

class GreenhouseLeave(BaseModel):
    username: str

class GreenhouseSessionStart(BaseModel):
    room_id: int
    username: str
    seat_number: int
    task_id: Optional[int] = None

class GreenhouseSessionEnd(BaseModel):
    session_id: int
    username: str

class SunshineEarn(BaseModel):
    username: str
    amount: int
    source: str
    description: str = ""

# --- WebSocket 杩炴帴绠＄悊鍣?---
class GreenhouseConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}  # room_id -> [websocket, ...]

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: int, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

greenhouse_manager = GreenhouseConnectionManager()

# --- 鏃跺厜娓╁ API ---

@app.post("/api/greenhouse/create")
async def create_greenhouse(data: GreenhouseCreate):
    """Internal helper docstring."""
    room_code = str(uuid.uuid4())[:8].upper()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鍒涘缓娓╁
    c.execute('''INSERT INTO Greenhouses (room_code, name, description, owner_username, max_seats, is_public, password, theme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (room_code, data.name, data.description, data.owner_username, data.max_seats, data.is_public, data.password, data.theme))
    room_id = c.lastrowid

    # 鍒涘缓搴т綅 (鍦嗗舰甯冨眬)
    import math
    for i in range(data.max_seats):
        angle = (2 * math.pi * i) / data.max_seats
        radius = 3.0
        pos_x = math.cos(angle) * radius
        pos_z = math.sin(angle) * radius
        rotation = -math.degrees(angle) + 90
        c.execute('''INSERT INTO Greenhouse_Seats (room_id, seat_number, position_x, position_z, rotation_y)
                    VALUES (?, ?, ?, ?, ?)''', (room_id, i + 1, pos_x, pos_z, rotation))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "room_id": room_id,
        "room_code": room_code,
        "message": f"娓╁銆恵data.name}銆戝垱寤烘垚鍔燂紒"
    }

@app.get("/api/greenhouse/list")
async def list_greenhouses(is_public: bool = True):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if is_public:
        c.execute('''SELECT id, room_code, name, description, owner_username, max_seats, theme,
                           (SELECT COUNT(*) FROM Greenhouse_Seats WHERE room_id = Greenhouses.id AND is_occupied = 1) as occupied
                    FROM Greenhouses WHERE is_public = 1 ORDER BY created_at DESC''')
    else:
        c.execute('''SELECT id, room_code, name, description, owner_username, max_seats, theme,
                           (SELECT COUNT(*) FROM Greenhouse_Seats WHERE room_id = Greenhouses.id AND is_occupied = 1) as occupied
                    FROM Greenhouses ORDER BY created_at DESC''')

    greenhouses = [{
        "id": row[0], "room_code": row[1], "name": row[2], "description": row[3],
        "owner": row[4], "max_seats": row[5], "theme": row[6], "occupied_seats": row[7]
    } for row in c.fetchall()]
    conn.close()

    return {"greenhouses": greenhouses}

@app.get("/api/greenhouse/{room_id}")
async def get_greenhouse(room_id: int):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT id, room_code, name, description, owner_username, max_seats, is_public, theme, total_sunshine, created_at
                FROM Greenhouses WHERE id = ?''', (room_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="娓╁涓嶅瓨鍦?)

    greenhouse = {
        "id": row[0], "room_code": row[1], "name": row[2], "description": row[3],
        "owner": row[4], "max_seats": row[5], "is_public": row[6], "theme": row[7],
        "total_sunshine": row[8], "created_at": row[9]
    }

    # 鑾峰彇搴т綅鐘舵€?
    c.execute('''SELECT id, seat_number, position_x, position_z, rotation_y, is_occupied, current_user
                FROM Greenhouse_Seats WHERE room_id = ?''', (room_id,))
    seats = [{
        "id": row[0], "seat_number": row[1], "position_x": row[2], "position_z": row[3],
        "rotation_y": row[4], "is_occupied": bool(row[5]), "current_user": row[6]
    } for row in c.fetchall()]

    # 鑾峰彇褰撳墠瀛︿範涓殑鐢ㄦ埛
    c.execute('''SELECT username, seat_id, start_time, duration_minutes
                FROM Greenhouse_Sessions WHERE room_id = ? AND status = 'growing' ''', (room_id,))
    growing_users = [{
        "username": row[0], "seat_id": row[1], "start_time": row[2], "duration": row[3]
    } for row in c.fetchall()]

    conn.close()

    return {
        "greenhouse": greenhouse,
        "seats": seats,
        "growing_users": growing_users
    }

@app.post("/api/greenhouse/{room_id}/join")
async def join_greenhouse(room_id: int, data: GreenhouseJoin):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ユ俯瀹ゆ槸鍚﹀瓨鍦?
    c.execute("SELECT is_public, password FROM Greenhouses WHERE id = ?", (room_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="娓╁涓嶅瓨鍦?)

    is_public, password = row
    if not is_public and password and password != data.password:
        conn.close()
        raise HTTPException(status_code=403, detail="瀵嗙爜閿欒")

    conn.close()
    return {"success": True, "message": "鎴愬姛鍔犲叆娓╁"}

@app.post("/api/greenhouse/{room_id}/select-seat")
async def select_greenhouse_seat(room_id: int, data: GreenhouseSessionStart):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ュ骇浣嶆槸鍚﹀彲鐢?
    c.execute("SELECT is_occupied FROM Greenhouse_Seats WHERE room_id = ? AND seat_number = ?",
              (room_id, data.seat_number))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="搴т綅涓嶅瓨鍦?)
    if row[0]:
        conn.close()
        raise HTTPException(status_code=400, detail="搴т綅宸茶鍗犵敤")

    # 鏇存柊搴т綅鐘舵€?
    c.execute('''UPDATE Greenhouse_Seats SET is_occupied = 1, current_user = ?
                WHERE room_id = ? AND seat_number = ?''', (data.username, room_id, data.seat_number))

    # 鑾峰彇搴т綅ID
    c.execute("SELECT id FROM Greenhouse_Seats WHERE room_id = ? AND seat_number = ?", (room_id, data.seat_number))
    seat_id = c.fetchone()[0]

    # 鍒涘缓瀛︿範浼氳瘽
    c.execute('''INSERT INTO Greenhouse_Sessions (room_id, username, seat_id, task_id, status)
                VALUES (?, ?, ?, ?, 'growing')''', (room_id, data.username, seat_id, data.task_id))
    session_id = c.lastrowid

    conn.commit()
    conn.close()

    # 骞挎挱搴т綅鏇存柊
    await greenhouse_manager.broadcast(room_id, {
        "type": "seat_update",
        "seat_number": data.seat_number,
        "username": data.username,
        "status": "occupied"
    })

    return {
        "success": True,
        "session_id": session_id,
        "message": "鎾鎴愬姛锛屽紑濮嬫垚闀匡紒"
    }

@app.post("/api/greenhouse/session/end")
async def end_greenhouse_session(data: GreenhouseSessionEnd):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇浼氳瘽淇℃伅
    c.execute('''SELECT room_id, username, seat_id, task_id, start_time
                FROM Greenhouse_Sessions WHERE id = ? AND username = ? AND status = 'growing' ''',
              (data.session_id, data.username))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦ㄦ垨宸茬粨鏉?)

    room_id, username, seat_id, task_id, start_time = row

    # 璁＄畻鏃堕暱
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if isinstance(start_time, str) else start_time
    end_dt = datetime.now()
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

    # 璁＄畻闃冲厜濂栧姳
    sunshine_earned = 0

    # 1. 鍩虹鏃堕暱濂栧姳
    if duration_minutes >= 60:
        sunshine_earned += 15
    elif duration_minutes >= 45:
        sunshine_earned += 10
    elif duration_minutes >= 25:
        sunshine_earned += 5

    # 2. AI璇勫垎濂栧姳锛堝鏋滄湁鍏宠仈浠诲姟锛?    ai_score = 0
    if task_id:
        c.execute("SELECT ai_score FROM Todo_Tasks WHERE id = ?", (task_id,))
        task_row = c.fetchone()
        if task_row and task_row[0]:
            ai_score = task_row[0]
            if ai_score >= 100:
                sunshine_earned += 10
            elif ai_score >= 90:
                sunshine_earned += 5
            elif ai_score >= 80:
                sunshine_earned += 3

    # 3. 鍏卞鍔犳垚
    c.execute("SELECT COUNT(*) FROM Greenhouse_Sessions WHERE room_id = ? AND status = 'growing'", (room_id,))
    active_users = c.fetchone()[0]
    if active_users >= 6:
        sunshine_earned += 10 * active_users
    elif active_users >= 4:
        sunshine_earned += 5 * active_users
    elif active_users >= 2:
        sunshine_earned += 2 * active_users

    # 鏇存柊浼氳瘽鐘舵€?
    c.execute('''UPDATE Greenhouse_Sessions SET status = 'completed', end_time = CURRENT_TIMESTAMP,
                duration_minutes = ?, sunshine_earned = ?, ai_score = ? WHERE id = ?''',
              (duration_minutes, sunshine_earned, ai_score, data.session_id))

    # 閲婃斁搴т綅
    c.execute("SELECT seat_number FROM Greenhouse_Seats WHERE id = ?", (seat_id,))
    seat_number = c.fetchone()[0]
    c.execute("UPDATE Greenhouse_Seats SET is_occupied = 0, current_user = '' WHERE id = ?", (seat_id,))

    # 鏇存柊娓╁鎬婚槼鍏?
    c.execute("UPDATE Greenhouses SET total_sunshine = total_sunshine + ? WHERE id = ?", (sunshine_earned, room_id))

    # 缁欑敤鎴峰鍔犻槼鍏?
    c.execute("UPDATE User_Growth SET sunshine = COALESCE(sunshine, 0) + ? WHERE username = ?", (sunshine_earned, username))
    # 濡傛灉鐢ㄦ埛娌℃湁璁板綍鍒欏垱寤?
    c.execute("INSERT OR IGNORE INTO User_Growth (username, sunshine) VALUES (?, ?)", (username, sunshine_earned))

    # 璁板綍闃冲厜浜ゆ槗
    c.execute('''INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description)
                VALUES (?, ?, 'earn', 'greenhouse_harvest', ?)''',
              (username, sunshine_earned, f"娓╁瀛︿範{duration_minutes}鍒嗛挓"))

    # 鑾峰彇鏂颁綑棰?
    c.execute("SELECT sunshine FROM User_Growth WHERE username = ?", (username,))
    new_sunshine = c.fetchone()[0] or 0

    conn.commit()
    conn.close()

    # 骞挎挱鏀惰幏娑堟伅
    await greenhouse_manager.broadcast(room_id, {
        "type": "harvest",
        "username": username,
        "seat_number": seat_number,
        "sunshine_earned": sunshine_earned,
        "duration": duration_minutes
    })

    return {
        "success": True,
        "sunshine_earned": sunshine_earned,
        "duration_minutes": duration_minutes,
        "ai_score": ai_score,
        "new_sunshine_balance": new_sunshine,
        "message": f"鏀惰幏鎴愬姛锛佽幏寰?{sunshine_earned} 闃冲厜 鈽€锔?
    }

@app.get("/api/sunshine/{username}")
async def get_sunshine_balance(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sunshine FROM User_Growth WHERE username = ?", (username,))
    row = c.fetchone()
    balance = row[0] if row and row[0] is not None else 0
    conn.close()
    return {"username": username, "sunshine": balance}

@app.get("/api/sunshine/history/{username}")
async def get_sunshine_history(username: str, limit: int = 50):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT amount, transaction_type, source, description, created_at
                FROM Sunshine_Transactions WHERE username = ?
                ORDER BY created_at DESC LIMIT ?''', (username, limit))
    rows = c.fetchall()
    history = [{
        "amount": row[0], "type": row[1], "source": row[2],
        "description": row[3], "time": row[4]
    } for row in rows]
    conn.close()
    return {"history": history}

# --- WebSocket 绔偣 ---
# 鍗忎綔鐣寗閽熺鐞嗗櫒
class CollabFocusManager:
    def __init__(self):
        self.active_connections: dict = {}  # room_id -> {websockets, session_data}

    async def connect(self, room_id: str, websocket: WebSocket, username: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {"connections": {}, "session": None}
        self.active_connections[room_id]["connections"][username] = websocket

    def disconnect(self, room_id: str, username: str):
        if room_id in self.active_connections:
            self.active_connections[room_id]["connections"].pop(username, None)
            if not self.active_connections[room_id]["connections"]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict, exclude: str = None):
        if room_id in self.active_connections:
            for username, ws in self.active_connections[room_id]["connections"].items():
                if username != exclude:
                    try:
                        await ws.send_json(message)
                    except:
                        pass

    def get_room_members(self, room_id: str):
        if room_id in self.active_connections:
            return list(self.active_connections[room_id]["connections"].keys())
        return []

collab_manager = CollabFocusManager()


@app.websocket("/ws/collab/{room_id}")
async def websocket_collab_focus(websocket: WebSocket, room_id: str, username: str):
    """Internal helper docstring."""
    await collab_manager.connect(room_id, websocket, username)
    try:
        # 閫氱煡鍏朵粬浜烘湁鏂版垚鍛樺姞鍏?        await collab_manager.broadcast(room_id, {
            "type": "user_joined",
            "username": username,
            "members": collab_manager.get_room_members(room_id)
        }, exclude=username)

        # 鍙戦€佸綋鍓嶆埧闂寸姸鎬佺粰鏂版垚鍛?        await websocket.send_json({
            "type": "room_state",
            "members": collab_manager.get_room_members(room_id),
            "session": collab_manager.active_connections.get(room_id, {}).get("session")
        })

        while True:
            data = await websocket.receive_json()

            if data['type'] == 'start_focus':
                # 寮€濮嬪崗浣滅暘鑼勯挓
                session_data = {
                    "status": "active",
                    "duration": data.get('duration', 25),
                    "subject": data.get('subject', '瀛︿範'),
                    "started_at": data.get('started_at'),
                    "started_by": username
                }
                if room_id in collab_manager.active_connections:
                    collab_manager.active_connections[room_id]["session"] = session_data
                await collab_manager.broadcast(room_id, {
                    "type": "focus_started",
                    "session": session_data,
                    "started_by": username
                })

            elif data['type'] == 'complete_focus':
                # 瀹屾垚鍗忎綔鐣寗閽?                await collab_manager.broadcast(room_id, {
                    "type": "focus_completed",
                    "completed_by": username,
                    "duration": data.get('duration'),
                    "reward": REWARD_RULES.get('collab_focus', {})
                })
                if room_id in collab_manager.active_connections:
                    collab_manager.active_connections[room_id]["session"] = None

            elif data['type'] == 'chat':
                # 鑱婂ぉ娑堟伅
                await collab_manager.broadcast(room_id, {
                    "type": "chat",
                    "username": username,
                    "message": data.get('message'),
                    "timestamp": data.get('timestamp')
                })

            elif data['type'] == 'ping':
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        collab_manager.disconnect(room_id, username)
        await collab_manager.broadcast(room_id, {
            "type": "user_left",
            "username": username,
            "members": collab_manager.get_room_members(room_id)
        })


@app.websocket("/ws/greenhouse/{room_id}")
async def websocket_greenhouse(websocket: WebSocket, room_id: int):
    """Internal helper docstring."""
    await greenhouse_manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data['type'] == 'emoji':
                # 琛ㄦ儏浜掑姩
                await greenhouse_manager.broadcast(room_id, {
                    "type": "emoji",
                    "username": data.get('username'),
                    "emoji": data.get('emoji'),
                    "seat_number": data.get('seat_number')
                })

            elif data['type'] == 'grow_progress':
                # 鎴愰暱杩涘害鍚屾
                await greenhouse_manager.broadcast(room_id, {
                    "type": "grow_progress",
                    "username": data.get('username'),
                    "progress": data.get('progress'),
                    "seat_number": data.get('seat_number')
                })

            elif data['type'] == 'ping':
                # 蹇冭烦
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        greenhouse_manager.disconnect(room_id, websocket)


# ============================================
# 鍗忎綔鐣寗閽?API
# ============================================
class CollabRoomCreate(BaseModel):
    host_username: str
    subject: str = "瀛︿範"
    max_members: int = 4
    duration: int = 25


class CollabJoin(BaseModel):
    room_code: str
    username: str


@app.post("/api/collab/create")
async def create_collab_room(data: CollabRoomCreate):
    """Internal helper docstring."""
    room_code = f"collab_{data.host_username}_{int(time.time()*1000):0.0f}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ユ埧闂存槸鍚﹀凡瀛樺湪
    c.execute("SELECT room_code FROM Collab_Sessions WHERE room_code = ?", (room_code,))
    if c.fetchone():
        conn.close()
        return {"success": False, "message": "鎴块棿宸插瓨鍦?}

    # 浣跨敤 members JSON 瀛樺偍鍙備笌鑰呭垪琛?    members_json = json.dumps([data.host_username])

    c.execute("""
        INSERT INTO Collab_Sessions (room_code, host_username, subject, members, duration, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'waiting', ?)
    """Internal helper docstring."""

    conn.commit()
    conn.close()

    return {
        "success": True,
        "room_code": room_code,
        "room_url": f"/collab/{room_code}"
    }


@app.post("/api/collab/join")
async def join_collab_room(data: CollabJoin):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT room_code, host_username, subject, members, duration, status FROM Collab_Sessions WHERE room_code = ?", (data.room_code,))
    room = c.fetchone()

    if not room:
        conn.close()
        return {"success": False, "message": "鎴块棿涓嶅瓨鍦?}

    # 瑙ｆ瀽鎴愬憳鍒楄〃
    members = json.loads(room[3]) if room[3] else []
    max_members = 4  # 榛樿鏈€澶ф垚鍛樻暟

    if len(members) >= max_members:
        conn.close()
        return {"success": False, "message": "鎴块棿宸叉弧"}

    if data.username in members:
        conn.close()
        return {"success": False, "message": "宸插姞鍏ヨ鎴块棿"}

    # 娣诲姞鏂版垚鍛?    members.append(data.username)
    c.execute("UPDATE Collab_Sessions SET members = ? WHERE room_code = ?",
              (json.dumps(members), data.room_code))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "room_code": data.room_code,
        "host": room[1],
        "subject": room[2],
        "members": members
    }


@app.get("/api/collab/rooms")
async def get_collab_rooms(status: str = "waiting"):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT room_code, host_username, subject, members, duration, status
        FROM Collab_Sessions
        WHERE status = ?
        ORDER BY created_at DESC
    """Internal helper docstring."""

    rooms = []
    for row in c.fetchall():
        members = json.loads(row[3]) if row[3] else []
        rooms.append({
            "room_code": row[0],
            "host": row[1],
            "subject": row[2],
            "max_members": 4,
            "member_count": len(members),
            "duration": row[4],
            "status": row[5]
        })

    conn.close()
    return {"rooms": rooms}


@app.post("/api/collab/complete")
async def complete_collab_session(room_code: str, username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇鎴块棿淇℃伅
    c.execute("SELECT host_username, duration, subject FROM Collab_Sessions WHERE room_code = ?", (room_code,))
    room = c.fetchone()
    if not room:
        conn.close()
        return {"success": False, "message": "鎴块棿涓嶅瓨鍦?}

    # 璁＄畻濂栧姳
    reward = REWARD_RULES.get('collab_focus', {'coins': 25, 'diamonds': 10})
    coins_earned = reward['coins']
    diamonds_earned = reward['diamonds']

    # 鏇存柊鐢ㄦ埛璐у竵
    get_or_create_growth(username)
    c.execute("UPDATE User_Growth SET coins = coins + ?, diamonds = diamonds + ? WHERE username = ?",
              (coins_earned, diamonds_earned, username))

    # 璁板綍鍙備笌鑰呭鍔?
    c.execute("""
        UPDATE Collab_Participants
        SET completed = 1, coins_earned = ?, sunshine_earned = ?
        WHERE room_code = ? AND username = ?
    """Internal helper docstring."""

    conn.commit()
    conn.close()

    return {
        "success": True,
        "coins_earned": coins_earned,
        "diamonds_earned": diamonds_earned
    }


# ============================================
# 缁熶竴鍟嗗簵 api
# ============================================

class UnifiedShopBuyRequest(BaseModel):
    username: str
    item_id: int
    quantity: int = 1

class PlaceItemRequest(BaseModel):
    username: str
    item_id: int
    position_x: float
    position_y: float = 0
    position_z: float
    rotation_y: float = 0
    scale: float = 1.0
    map_id: str = 'city'  # 榛樿鏀惧埌鍩庡競鍦板浘
    slot_id: str = None

class FavoriteRequest(BaseModel):
    username: str
    item_id: int


@app.get("/api/unified-shop/items")
async def get_unified_shop_items(
    username: str = None,
    category: str = None,
    subcategory: str = None,
    rarity: str = None,
    grade: str = None,
    search: str = None,
    min_price: int = 0,
    max_price: int = 10000,
    page: int = 1,
    limit: int = 500
):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = "SELECT * FROM Unified_Shop_Items WHERE is_available = 1"
    params = []
    effective_rarity = rarity_for_grade(grade) if grade else rarity

    if category:
        query += " AND category = ?"
        params.append(category)
    if subcategory:
        query += " AND subcategory = ?"
        params.append(subcategory)
    if effective_rarity:
        query += " AND rarity = ?"
        params.append(effective_rarity)

    search_param = None
    if search:
        query += " AND (name LIKE ? OR name_cn LIKE ? OR item_code LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    query += " AND price_sunshine >= ? AND price_sunshine <= ?"
    params.extend([min_price, max_price])
    query += " ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?"
    params.extend([limit, (page - 1) * limit])

    c.execute(query, params)
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]

    item_counts = None
    placed_by_type = None
    slot_capacities = city_slot_capacities()
    if username:
        migrate_city_placements(conn, username)
        item_counts, placed_by_type = get_user_inventory_summary(conn, username)

    items = []
    for row in rows:
        item = dict(zip(columns, row))
        apply_preview_path(item)
        enrich_shop_item(
            item,
            item_counts=item_counts,
            placed_by_type=placed_by_type,
            slot_capacities=slot_capacities,
        )
        items.append(item)

    count_query = "SELECT COUNT(*) FROM Unified_Shop_Items WHERE is_available = 1"
    count_params = []
    if category:
        count_query += " AND category = ?"
        count_params.append(category)
    if subcategory:
        count_query += " AND subcategory = ?"
        count_params.append(subcategory)
    if effective_rarity:
        count_query += " AND rarity = ?"
        count_params.append(effective_rarity)
    if search_param:
        count_query += " AND (name LIKE ? OR name_cn LIKE ? OR item_code LIKE ?)"
        count_params.extend([search_param, search_param, search_param])
    count_query += " AND price_sunshine >= ? AND price_sunshine <= ?"
    count_params.extend([min_price, max_price])

    c.execute(count_query, count_params)
    total = c.fetchone()[0]

    conn.commit()
    conn.close()
    return {"items": items, "total": total, "page": page, "limit": limit}


@app.get("/api/unified-shop/items/{item_id}")
async def get_unified_shop_item(item_id: int, username: str = None):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM Unified_Shop_Items WHERE id = ?", (item_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="鍟嗗搧涓嶅瓨鍦?)
    columns = [desc[0] for desc in c.description]
    item = dict(zip(columns, row))
    apply_preview_path(item)
    item_counts = None
    placed_by_type = None
    slot_capacities = city_slot_capacities()
    if username:
        migrate_city_placements(conn, username)
        item_counts, placed_by_type = get_user_inventory_summary(conn, username)
    enrich_shop_item(
        item,
        item_counts=item_counts,
        placed_by_type=placed_by_type,
        slot_capacities=slot_capacities,
    )
    conn.commit()
    conn.close()
    return item


@app.get("/api/unified-shop/categories")
async def get_shop_categories():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT category, COUNT(*) as count
        FROM Unified_Shop_Items
        WHERE is_available = 1
        GROUP BY category
        ORDER BY count DESC
    """Internal helper docstring."""
    categories = [{"category": row[0], "count": row[1]} for row in c.fetchall()]
    conn.close()
    return {"categories": categories}


@app.get("/api/unified-shop/balance/{username}")
async def get_user_balance(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(diamonds, 0), COALESCE(sunshine, 0), COALESCE(coins, 0) FROM User_Growth WHERE username = ?",
        (username,),
    )
    row = c.fetchone()
    diamonds = max(row[0] or 0, row[1] or 0) if row else 0
    coins = row[2] if row else 0
    conn.close()
    return {"username": username, "diamonds": diamonds, "sunshine": diamonds, "coins": coins}


@app.post("/api/unified-shop/buy")
async def buy_unified_shop_item(data: UnifiedShopBuyRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 妫€鏌ュ晢鍝?
    c.execute("SELECT id, name, name_cn, price_sunshine, price_coins, rarity FROM Unified_Shop_Items WHERE id = ?", (data.item_id,))
    item = c.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="鍟嗗搧涓嶅瓨鍦?)

    item_id, item_name, item_name_cn, price_sunshine, price_coins, rarity = item
    display_name = item_name_cn or item_name

    # 鏍规嵁绋€鏈夊害鍐冲畾浣跨敤鍝璐у竵
    use_coins = rarity == 'common' and price_coins > 0

    if use_coins:
        # 浣跨敤閲戝竵璐拱鏅€氬晢鍝?        total_price = price_coins * data.quantity
        c.execute("SELECT COALESCE(coins, 0) FROM User_Growth WHERE username = ?", (data.username,))
        row = c.fetchone()
        current_balance = row[0] if row else 0

        if current_balance < total_price:
            conn.close()
            raise HTTPException(status_code=400, detail=f"閲戝竵涓嶈冻锛侀渶瑕?{total_price} 閲戝竵锛屽綋鍓?{current_balance} 閲戝竵")

        # 鎵ｉ櫎閲戝竵
        c.execute("UPDATE User_Growth SET coins = coins - ? WHERE username = ?", (total_price, data.username))
        currency_name = "閲戝竵"
    else:
        # 浣跨敤閽荤煶璐拱绋€鏈夊晢鍝?        total_price = price_sunshine * data.quantity
        c.execute(
            "SELECT COALESCE(diamonds, 0), COALESCE(sunshine, 0) FROM User_Growth WHERE username = ?",
            (data.username,),
        )
        row = c.fetchone()
        current_balance = max(row[0] or 0, row[1] or 0) if row else 0

        if current_balance < total_price:
            conn.close()
            raise HTTPException(status_code=400, detail=f"閽荤煶涓嶈冻锛侀渶瑕?{total_price} 閽荤煶锛屽綋鍓?{current_balance} 閽荤煶")

        # 鎵ｉ櫎閽荤煶锛屽苟鍚屾 sunshine 鏃у瓧娈?
        c.execute(
            "UPDATE User_Growth SET diamonds = ?, sunshine = ? WHERE username = ?",
            (current_balance - total_price, current_balance - total_price, data.username),
        )

        # 璁板綍閽荤煶浜ゆ槗
        c.execute("""
            INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description)
            VALUES (?, ?, 'spend', 'shop', ?)
        """Internal helper docstring."""
        currency_name = "閽荤煶"

    # 娣诲姞鍒扮敤鎴峰簱瀛?    for _ in range(data.quantity):
        c.execute("""
            INSERT INTO User_Inventory (username, item_id, status)
            VALUES (?, ?, 'owned')
        """Internal helper docstring."""

    conn.commit()
    conn.close()
    return {
        "success": True,
        "message": f"璐拱鎴愬姛锛佹秷鑰?{total_price} {currency_name}",
        "new_balance": current_balance - total_price,
        "currency": "coins" if use_coins else "diamonds"
    }


@app.get("/api/unified-shop/inventory/{username}")
async def get_user_inventory(username: str, category: str = None):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    migrate_city_placements(conn, username)

    query = """
        SELECT ui.*, usi.name, usi.name_cn, usi.category, usi.icon, usi.model_path, usi.rarity
        FROM User_Inventory ui
        JOIN Unified_Shop_Items usi ON ui.item_id = usi.id
        WHERE ui.username = ?
    """
    params = [username]

    if category:
        query += " AND usi.category = ?"
        params.append(category)

    query += " ORDER BY ui.created_at DESC"

    c.execute(query, params)
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]

    inventory = []
    for row in rows:
        item = dict(zip(columns, row))
        apply_preview_path(item)
        item["grade"] = normalize_grade(item.get("rarity"))
        item["placement_type"] = placement_type_for_category(item.get("category"))
        inventory.append(item)

    item_counts, placed_by_type = get_user_inventory_summary(conn, username)
    conn.commit()
    conn.close()
    return {
        "inventory": inventory,
        "summary": {
            "item_counts": item_counts,
            "placed_by_type": placed_by_type,
            "slot_capacities": city_slot_capacities(),
        },
    }


@app.get("/api/unified-shop/favorites/{username}")
async def get_user_favorites(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT usi.*, usf.added_at
        FROM User_Shop_Favorites usf
        JOIN Unified_Shop_Items usi ON usf.item_id = usi.id
        WHERE usf.username = ?
        ORDER BY usf.added_at DESC
    """Internal helper docstring."""
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    favorites = [dict(zip(columns, row)) for row in rows]
    conn.close()
    return {"favorites": favorites}


@app.post("/api/unified-shop/favorites")
async def add_favorite(data: FavoriteRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO User_Shop_Favorites (username, item_id) VALUES (?, ?)",
                  (data.username, data.item_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "鏀惰棌鎴愬姛"}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "message": "宸叉敹钘?}


@app.delete("/api/unified-shop/favorites")
async def remove_favorite(data: FavoriteRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM User_Shop_Favorites WHERE username = ? AND item_id = ?",
              (data.username, data.item_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "鍙栨秷鏀惰棌"}


@app.post("/api/unified-shop/place")
async def place_item_on_island(data: PlaceItemRequest):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    migrate_city_placements(conn, data.username)

    map_id = getattr(data, 'map_id', 'city') or 'city'
    if map_id != 'city':
        conn.close()
        raise HTTPException(status_code=400, detail="鐩爣鍦板浘涓嶅锛氱洰鍓嶅彧鑳芥斁鍒板煄甯傚湴鍥?)

    c.execute("""
        SELECT id, category, name, name_cn, icon, model_path, rarity, item_code
        FROM Unified_Shop_Items
        WHERE id = ?
    """Internal helper docstring."""
    item_info = c.fetchone()
    if not item_info:
        conn.close()
        raise HTTPException(status_code=404, detail="鍟嗗搧涓嶅瓨鍦?)

    placement_type = placement_type_for_category(item_info[1])
    if placement_type not in {"building", "greenery"}:
        conn.close()
        raise HTTPException(status_code=400, detail="褰撳墠鍩庡競鍦板浘鍙敮鎸佸缓绛戝拰缁垮寲鏀剧疆")

    slot_lookup = city_slot_index()
    slot = slot_lookup.get(data.slot_id)
    if not slot or not slot.get("enabled", True):
        conn.close()
        raise HTTPException(status_code=400, detail="璇烽€夋嫨涓€涓悎娉曠殑鍩庡競妲戒綅")
    if slot.get("slot_type") != placement_type:
        conn.close()
        raise HTTPException(status_code=400, detail="璇ョ墿鍝佸彧鑳芥斁鍒板尮閰嶇殑妲戒綅")

    c.execute("""
        SELECT id FROM Island_Infrastructure
        WHERE username = ? AND map_id = 'city' AND slot_id = ?
        LIMIT 1
    """Internal helper docstring."""
    if c.fetchone():
        conn.close()
        detail = "寤虹瓚浣嶅凡婊? if placement_type == "building" else "缁垮寲浣嶅凡婊?
        raise HTTPException(status_code=400, detail=detail)

    # 妫€鏌ョ敤鎴锋槸鍚︽嫢鏈夎鐗╁搧锛屼互鍙婃槸鍚﹀凡缁忔斁缃?
    c.execute("""
        SELECT id, status FROM User_Inventory
        WHERE username = ? AND item_id = ?
        ORDER BY CASE WHEN status = 'owned' THEN 0 ELSE 1 END, id DESC
        LIMIT 1
    """Internal helper docstring."""
    inventory_item = c.fetchone()

    if not inventory_item:
        conn.close()
        raise HTTPException(status_code=400, detail="璇峰厛璐拱璇ョ墿鍝侊紝鍐嶅洖鍩庡競鍦板浘鏀剧疆")

    if inventory_item[1] != 'owned':
        conn.close()
        raise HTTPException(status_code=400, detail="璇ョ墿鍝佸凡缁忔斁缃繃浜嗭紝璇峰厛浠庡煄甯傚湴鍥剧Щ闄ゅ悗鍐嶉噸鏂版斁缃?)

    final_x = slot.get("x", 0)
    final_y = slot.get("y", CITY_SURFACE_Y)
    final_z = slot.get("z", 0)
    final_rotation = slot.get("rotation_y", 0)
    final_scale = data.scale or 1.0

    # 鏇存柊搴撳瓨鐘舵€?
    c.execute("""
        UPDATE User_Inventory SET status = 'placed'
        WHERE id = ?
    """Internal helper docstring."""

    # 娣诲姞鍒板矝灞?
    c.execute("""
        INSERT INTO Island_Infrastructure (username, item_id, position_x, position_y, position_z, rotation_y, scale, map_id, slot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """Internal helper docstring."""
    placed_id = c.lastrowid

    conn.commit()
    conn.close()
    return {
        "success": True,
        "message": "鏀剧疆鎴愬姛",
        "placed_item": {
            "id": placed_id,
            "item_id": data.item_id,
            "item_code": item_info[7] if item_info else None,
            "name": item_info[2] if item_info else "",
            "name_cn": item_info[3] if item_info else "",
            "category": item_info[1] if item_info else "",
            "icon": item_info[4] if item_info else "馃摝",
            "model_path": item_info[5] if item_info else "",
            "rarity": item_info[6] if item_info else "common",
            "grade": normalize_grade(item_info[6] if item_info else "common"),
            "placement_type": placement_type,
            "slot_id": data.slot_id,
            "position_x": final_x,
            "position_y": final_y,
            "position_z": final_z,
            "rotation_y": final_rotation,
            "scale": final_scale,
        }
    }


@app.get("/api/unified-shop/placed/{username}")
async def get_placed_items(username: str, map: str = 'city'):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if map == 'city':
        migrate_city_placements(conn, username)
        c.execute("""
            UPDATE Island_Infrastructure
            SET position_y = ?
            WHERE username = ?
              AND map_id = 'city'
              AND (position_y IS NULL OR ABS(position_y) < 0.01)
        """Internal helper docstring."""
        conn.commit()
    c.execute("""
        SELECT ii.id, ii.item_id, usi.item_code, usi.name, usi.name_cn, usi.category,
               usi.icon, usi.model_path, usi.rarity,
               ii.position_x, ii.position_y, ii.position_z, ii.rotation_y, ii.scale, ii.slot_id
        FROM Island_Infrastructure ii
        JOIN Unified_Shop_Items usi ON ii.item_id = usi.id
        WHERE ii.username = ? AND ii.map_id = ?
        ORDER BY ii.placed_at ASC
    """Internal helper docstring."""
    rows = c.fetchall()
    items = [{
        "id": row[0], "item_id": row[1], "item_code": row[2],
        "name": row[3], "name_cn": row[4], "category": row[5],
        "icon": row[6], "model_path": row[7], "rarity": row[8],
        "position_x": row[9] if row[9] is not None else 0,
        "position_y": row[10] if row[10] is not None else CITY_SURFACE_Y,
        "position_z": row[11] if row[11] is not None else 0,
        "rotation_y": row[12] if row[12] is not None else 0,
        "scale": row[13] if row[13] is not None else 1.0,
        "slot_id": row[14],
        "grade": normalize_grade(row[8]),
        "placement_type": placement_type_for_category(row[5])
    } for row in rows]
    conn.close()
    return {"items": items}


@app.delete("/api/unified-shop/placed/{placed_id}")
async def remove_placed_item(placed_id: int, username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇鏀剧疆鐨勭墿鍝佷俊鎭?
    c.execute("""
        SELECT item_id FROM Island_Infrastructure
        WHERE id = ? AND username = ?
    """Internal helper docstring."""
    placed_item = c.fetchone()

    if not placed_item:
        conn.close()
        raise HTTPException(status_code=404, detail="鏈壘鍒拌鏀剧疆鐗╁搧")

    # 鍒犻櫎鏀剧疆璁板綍
    c.execute("DELETE FROM Island_Infrastructure WHERE id = ?", (placed_id,))

    # 鏇存柊搴撳瓨鐘舵€?    restore_item_to_owned(conn, username, placed_item[0])

    conn.commit()
    conn.close()
    return {"success": True, "message": "宸茬Щ闄?}


# ============================================
# 馃寪 Vue 鍓嶇璧勬簮璺敱锛堟斁鍦ㄦ渶鍚庯紝纭繚 API 浼樺厛锛?# ============================================

# 鎸傝浇 Vue 鍓嶇鐨?assets 鐩綍
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="vue-assets")


@app.get("/{path:path}")
async def serve_vue_spa(path: str):
    """
    Vue SPA 璺敱鏀寔
    - 闈欐€佽祫婧愶紙assets/*锛夌敱涓婇潰鐨?mount 澶勭悊
    - 鍏朵粬璺敱杩斿洖 index.html锛岃 Vue Router 澶勭悊
    """
    # 濡傛灉鏄?API 璇锋眰浣嗘病鍖归厤鍒颁笂闈㈢殑璺敱锛岃繑鍥?404
    if path.startswith("api/") or path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # 灏濊瘯杩斿洖鍏蜂綋鏂囦欢
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    # Vue Router history 妯″紡锛氳繑鍥?index.html
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return serve_frontend_entry(index_path)

    # 濡傛灉 Vue dist 涓嶅瓨鍦紝灏濊瘯鏃х増 index.html
    old_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(old_index):
        return serve_frontend_entry(old_index)

    raise HTTPException(status_code=404, detail="Page not found")


# ===== 鎺﹁姒滅郴缁?API =====

@app.get("/api/greenhouse/{room_id}/leaderboard")
async def get_room_leaderboard(room_id: int, period: str = "weekly"):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鏍规嵁鏃堕棿鑼冨洿璁＄畻
    if period == "daily":
        time_filter = "date(start_time) = date('now')"
    elif period == "weekly":
        time_filter = "date(start_time) >= date('now', '-7 days')"
    else:  # monthly
        time_filter = "date(start_time) >= date('now', '-30 days')"

    c.execute('''
        SELECT username, SUM(duration_minutes) as total_minutes, COUNT(*) as sessions
        FROM Greenhouse_Sessions
        WHERE room_id = ? AND status = 'completed' AND ''' + time_filter + '''
        GROUP BY username
        ORDER BY total_minutes DESC
        LIMIT 10
    ''', (room_id,))

    leaderboard = [{
        "rank": i + 1,
        "username": row[0],
        "total_minutes": row[1],
        "sessions": row[2]
    } for i, row in enumerate(c.fetchall())]

    conn.close()
    return {"leaderboard": leaderboard, "period": period}


# ===== 鎴愬氨绯荤粺 API =====

@app.get("/api/achievements")
async def get_achievements():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚琛ㄥ瓨鍦?
    c.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            category TEXT,
            requirement TEXT,
            exp_reward INTEGER DEFAULT 10
        )
    ''')

    c.execute("SELECT id, name, description, icon, category, requirement, exp_reward FROM achievements")
    achievements = [{
        "id": row[0], "name": row[1], "description": row[2],
        "icon": row[3], "category": row[4], "requirement": row[5], "exp_reward": row[6]
    } for row in c.fetchall()]

    # 濡傛灉娌℃湁鎴愬氨鏁版嵁锛屽垵濮嬪寲榛樿鎴愬氨
    if not achievements:
        default_achievements = [
            ("鍒濆鑰?, "瀹屾垚绗竴娆′笓娉?, "馃幆", "focus", '{"minutes": 25}', 10),
            ("涓撴敞杈句汉", "杩炵画涓撴敞7澶?, "馃敟", "streak", '{"days": 7}', 20),
            ("绀句氦杈句汉", "鍔犲叆10涓埧闂?, "馃懃", "social", '{"rooms": 10}', 15),
            ("鏃╄捣楦?, "鏃╀笂6鐐瑰墠寮€濮嬩笓娉?, "馃寘", "special", '{"hour": 6}', 25),
            ("澶滅尗瀛?, "绱涓撴敞1000鍒嗛挓", "馃", "special", '{"minutes": 1000}', 30),
            ("澶┖鎺㈤櫓瀹?, "鍦ㄥお绌轰富棰樻埧闂村涔?, "馃殌", "special", '{"theme": "space"}', 15)
        ]
        for ach in default_achievements:
            c.execute("INSERT INTO achievements (name, description, icon, category, requirement, exp_reward) VALUES (?, ?, ?, ?, ?, ?)", ach)
        conn.commit()
        c.execute("SELECT id, name, description, icon, category, requirement, exp_reward FROM achievements")
        achievements = [{
            "id": row[0], "name": row[1], "description": row[2],
            "icon": row[3], "category": row[4], "requirement": row[5], "exp_reward": row[6]
        } for row in c.fetchall()]

    conn.close()
    return {"achievements": achievements}


@app.get("/api/user/{username}/achievements")
async def get_user_achievements(username: str):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鐢ㄦ埛鎴愬氨琛ㄥ瓨鍦?
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            achievement_id INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (achievement_id) REFERENCES achievements(id)
        )
    ''')

    c.execute('''
        SELECT a.id, a.name, a.description, a.icon, a.category, a.exp_reward, ua.progress, ua.unlocked_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.username = ?
        ORDER BY a.category, a.name
    ''', (username,))

    achievements = [{
        "id": row[0], "name": row[1], "description": row[2],
        "icon": row[3], "category": row[4], "exp_reward": row[5],
        "progress": row[6] or 0, "unlocked": row[7] is not None
    } for row in c.fetchall()]

    conn.close()
    return {"achievements": achievements, "username": username}


class AchievementCheck(BaseModel):
    username: str
    achievement_type: str = "focus"  # focus, streak, social, special


@app.post("/api/achievements/check")
async def check_achievements(data: AchievementCheck):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    unlocked = []

    # 鑾峰彇鐢ㄦ埛缁熻
    c.execute("SELECT SUM(duration_minutes) FROM Greenhouse_Sessions WHERE username = ? AND status = 'completed'", (data.username,))
    total_minutes = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(DISTINCT room_id) FROM Greenhouse_Sessions WHERE username = ?", (data.username,))
    rooms_joined = c.fetchone()[0] or 0

    # 妫€鏌ヤ笓娉ㄦ垚灏?
    c.execute("SELECT id, name, requirement, exp_reward FROM achievements WHERE category = 'focus'")
    for row in c.fetchall():
        import json
        req = json.loads(row[2])
        if total_minutes >= req.get("minutes", 0):
            c.execute("SELECT id FROM user_achievements WHERE username = ? AND achievement_id = ?", (data.username, row[0]))
            if not c.fetchone():
                c.execute("INSERT INTO user_achievements (username, achievement_id, progress, unlocked_at) VALUES (?, ?, 100, CURRENT_TIMESTAMP)", (data.username, row[0]))
                unlocked.append({"id": row[0], "name": row[1], "exp_reward": row[3]})

    # 妫€鏌ョぞ浜ゆ垚灏?
    c.execute("SELECT id, name, requirement, exp_reward FROM achievements WHERE category = 'social'")
    for row in c.fetchall():
        import json
        req = json.loads(row[2])
        if rooms_joined >= req.get("rooms", 0):
            c.execute("SELECT id FROM user_achievements WHERE username = ? AND achievement_id = ?", (data.username, row[0]))
            if not c.fetchone():
                c.execute("INSERT INTO user_achievements (username, achievement_id, progress, unlocked_at) VALUES (?, ?, 100, CURRENT_TIMESTAMP)", (data.username, row[0]))
                unlocked.append({"id": row[0], "name": row[1], "exp_reward": row[3]})

    conn.commit()
    conn.close()
    return {"unlocked": unlocked, "total_checked": len(unlocked)}


# ===== 瑁呴グ绯荤粺 API =====

@app.get("/api/decorations")
async def get_decorations():
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚瑁呴グ琛ㄥ瓨鍦?
    c.execute('''
        CREATE TABLE IF NOT EXISTS decorations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            price INTEGER DEFAULT 50,
            category TEXT DEFAULT 'plant',
            image_url TEXT
        )
    ''')

    c.execute("SELECT id, name, description, icon, price, category, image_url FROM decorations ORDER BY category, price")
    decorations = [{
        "id": row[0], "name": row[1], "description": row[2],
        "icon": row[3], "price": row[4], "category": row[5], "image_url": row[6]
    } for row in c.fetchall()]

    # 濡傛灉娌℃湁瑁呴グ鏁版嵁锛屽垵濮嬪寲榛樿瑁呴グ
    if not decorations:
        default_decorations = [
            ("鏄熼檯妞嶇墿", "鍙戝厜鐨勫お绌烘鐗?, "馃尡", 50, "plant", None),
            ("鏄熶簯瑁呴グ", "缇庝附鐨勮摑鑹叉槦浜?, "馃寣", 80, "background", None),
            ("鐏妯″瀷", "绾㈣壊鐏妯″瀷", "馃殌", 120, "vehicle", None),
            ("鏄熸槦鐏?, "闂儊鐨勬槦鏄熺伅", "猸?, 30, "light", None),
            ("瀹囪埅鍛橀洉鍍?, "灏忓皬瀹囪埅鍛?, "馃懆鈥嶐煔€", 200, "statue", None),
            ("鍗槦妯″瀷", "缁曡鐨勫崼鏄?, "馃洶锔?, 150, "vehicle", None)
        ]
        for dec in default_decorations:
            c.execute("INSERT INTO decorations (name, description, icon, price, category, image_url) VALUES (?, ?, ?, ?, ?, ?)", dec)
        conn.commit()
        c.execute("SELECT id, name, description, icon, price, category, image_url FROM decorations ORDER BY category, price")
        decorations = [{
            "id": row[0], "name": row[1], "description": row[2],
            "icon": row[3], "price": row[4], "category": row[5], "image_url": row[6]
        } for row in c.fetchall()]

    conn.close()
    return {"decorations": decorations}


@app.get("/api/room/{room_id}/decorations")
async def get_room_decorations(room_id: int):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 纭繚鎴块棿瑁呴グ鍏宠仈琛ㄥ瓨鍦?
    c.execute('''
        CREATE TABLE IF NOT EXISTS room_decorations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            decoration_id INTEGER NOT NULL,
            position_x REAL DEFAULT 0,
            position_y REAL DEFAULT 0,
            scale REAL DEFAULT 1,
            rotation REAL DEFAULT 0,
            placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES Greenhouses(id),
            FOREIGN KEY (decoration_id) REFERENCES decorations(id)
        )
    ''')

    c.execute('''
        SELECT d.id, d.name, d.description, d.icon, d.price, d.category, d.image_url,
               rd.id, rd.position_x, rd.position_y, rd.scale, rd.rotation
        FROM decorations d
        JOIN room_decorations rd ON d.id = rd.decoration_id
        WHERE rd.room_id = ?
        ORDER BY rd.placed_at DESC
    ''', (room_id,))

    decorations = [{
        "decoration_id": row[0], "name": row[1], "description": row[2],
        "icon": row[3], "price": row[4], "category": row[5], "image_url": row[6],
        "placed_id": row[7], "position_x": row[8], "position_y": row[9],
        "scale": row[10], "rotation": row[11]
    } for row in c.fetchall()]

    conn.close()
    return {"decorations": decorations, "room_id": room_id}


class DecorationPurchase(BaseModel):
    decoration_id: int
    username: str
    position_x: float = 0.0
    position_y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0


@app.post("/api/room/{room_id}/decorations/buy")
async def buy_room_decoration(room_id: int, data: DecorationPurchase):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鑾峰彇瑁呴グ浠锋牸
    c.execute("SELECT id, name, price FROM decorations WHERE id = ?", (data.decoration_id,))
    dec = c.fetchone()
    if not dec:
        conn.close()
        raise HTTPException(status_code=404, detail="瑁呴グ涓嶅瓨鍦?)

    decoration_id, name, price = dec

    # 妫€鏌ョ敤鎴烽槼鍏?
    c.execute("SELECT sunshine FROM user_growth WHERE username = ?", (data.username,))
    result = c.fetchone()
    if not result or result[0] < price:
        conn.close()
        raise HTTPException(status_code=400, detail="闃冲厜涓嶈冻")

    # 鎵ｉ櫎闃冲厜
    c.execute("UPDATE user_growth SET sunshine = sunshine - ? WHERE username = ?", (price, data.username))

    # 娣诲姞瑁呴グ鍒版埧闂?
    c.execute('''
        INSERT INTO room_decorations (room_id, decoration_id, position_x, position_y, scale, rotation)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (room_id, decoration_id, data.position_x, data.position_y, data.scale, data.rotation))

    conn.commit()
    conn.close()

    return {"success": True, "message": f"鎴愬姛璐拱 {name}锛?, "sunshine_cost": price}


class DecorationPlace(BaseModel):
    placed_id: int
    position_x: float
    position_y: float
    scale: float = 1.0
    rotation: float = 0.0


@app.post("/api/room/{room_id}/decorations/place")
async def place_room_decoration(room_id: int, data: DecorationPlace):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        UPDATE room_decorations
        SET position_x = ?, position_y = ?, scale = ?, rotation = ?
        WHERE id = ? AND room_id = ?
    ''', (data.position_x, data.position_y, data.scale, data.rotation, data.placed_id, room_id))

    conn.commit()
    conn.close()

    return {"success": True, "message": "瑁呴グ浣嶇疆宸叉洿鏂?}


@app.delete("/api/room/{room_id}/decorations/{placed_id}")
async def remove_room_decoration(room_id: int, placed_id: int):
    """Internal helper docstring."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM room_decorations WHERE id = ? AND room_id = ?", (placed_id, room_id))

    conn.commit()
    conn.close()

    return {"success": True, "message": "瑁呴グ宸茬Щ闄?}


if __name__ == "__main__":
    import uvicorn

    startup_port = 8000
    while startup_port <= 8010:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port_probe:
            try:
                port_probe.bind(("0.0.0.0", startup_port))
                break
            except OSError:
                startup_port += 1

    if startup_port > 8010:
        raise RuntimeError("8000-8010 绔彛閮借鍗犵敤浜嗭紝璇峰厛鍏抽棴鏃х殑鍚庣杩涚▼")

    if startup_port != 8000:
        print(f"[WARN] 8000 绔彛琚崰鐢紝宸茶嚜鍔ㄥ垏鎹㈠埌 http://127.0.0.1:{startup_port}")

    uvicorn.run(app, host="0.0.0.0", port=startup_port)


