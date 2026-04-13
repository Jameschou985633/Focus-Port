"""
Pygame 闂備胶纭堕弲娑欘殽閸濄儳鍗氶悹杞拌閸ゅ牊绻涘顔荤按闁稿鎹囬幃鈺呭矗婢跺苯缍旈梻浣瑰缁嬫垿鎮ч崱妤婂殨闁煎鍊栭弳婊兠归敐鍡樸仢闁稿繐娲ㄧ槐?+ 3D OBJ 缂傚倷绀侀崐钘夌暦閻㈢鍚归幖杈剧到閸ㄦ繈鏌涢幘妤€鍊荤憴锕傛⒑閹肩偛鍔ら柛瀣尵閺侇噣骞橀鑲╊槯闂侀潧锛忛崘鐐瘔闂?
闂備礁鎲″濠氬窗閺囥垹绀傛慨妞诲亾闁?- 濠?focusport.db 闂佽崵濮村ú鈺咁敋瑜戦妵?濠电儑绲藉ú锔炬崲閸岀偞鍋ら柕濞炬櫆閻撳倿鏌熺€涙绠樻い蹇旂叀閺屾洟宕遍弴鐘电崲闂佸湱鎳撳ú顓㈠箚瀹€鍕€烽悷娆欑到娴滄儳霉閿濆浂鐒鹃柛銈嗗浮閺岋繝鍩€椤掑嫬绀堢憸蹇涘几閸屾壕鍋撻悙鐟扳偓娑樷枍閿濆鍋?- 濠电偞娼欓崥瀣晪闂佸憡蓱缁嬫帞绮?city_sprite_manifest.json 闂備礁鎲″缁樻叏閹灐?OBJ 缂傚倷绀侀崐钘夌暦閻㈢鍚归幖缁版壋鍋撻幒妤€鐭楀璺鸿嫰鐢剟姊洪崨濠傜伇婵炲拑绲介埢?PNG 缂傚倷绶￠崰鏍ㄦ櫠閼恒儱顕?- 濠电姷顣介埀顒€鍟块埀顒€缍婇幃妯诲緞閹邦剝鎽曢梺褰掑亰閸犳盯锝為敂閿亾閻愮懓鈧稑鈻嶉敐澶嬪仱婵﹩鍘芥禍銈嗕繆椤栨繂鍚规慨濠囩畺閹鎮介棃娑樹粯闂?PNG闂備焦瀵х粙鎴︽嚐椤栫偛鍨傛い鏍仦閸ゅ﹥銇勮箛鎾愁仼鐞氱喖姊洪幖鐐插姢闁稿鍊濋崺鈧い鎴ｆ娴滈箖姊洪崨濠傜瑐闁告濞婅矾濞撴埃鍋撻柟铏箞楠炴捇骞掗幘鍏呮樊闂備礁鎲￠〃鍫熸叏瀹曞洨绀婇柛娑卞灣缁?- 闂備浇銆€閸嬫挻銇勯弽銊р槈闁?1-5 闁诲海鍋ｉ崐鏍ь渻娴犲鐒垫い鎺戝€歌ⅷ闂侀€炲苯鍘搁梻?闂備胶鎳撻崲鎻捨涘┑鍡忔瀺閹兼番鍔岃繚婵炴垶鎸绘竟瀛?闂備礁鎲￠悷锕傛偋濡ゅ啰鐭撻柣鎴ｆ杩濇繛?闂佸搫顦遍崑娑㈡偤閵娧勬殰闁规儳鐡ㄩ崕鐔肩叓閸ャ劍顥嗘い鈺婂亰閺?
闂佸搫顦弲婊堝礉濮椻偓閵嗕線骞嬮敂鑺ユ珫?python city_builder_pygame.py
python city_builder_pygame.py 濠电偠鎻徊鎸庢叏瀹勬壋鏋旈柟杈鹃檮閸嬨劑鏌曟繝蹇曠暠闁绘挻娲熼弻?"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame


BASE_DIR = Path(__file__).resolve().parent
PRIMARY_DB_PATH = BASE_DIR / "focusport.db"
LEGACY_DB_PATH = BASE_DIR / "focuscrossing.db"
MANIFEST_PATH = BASE_DIR / "city_sprite_manifest.json"
DEFAULT_USERNAME = os.getenv("FOCUS_CITY_USER", "demo_player")


def resolve_db_path() -> Path:
    if PRIMARY_DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return PRIMARY_DB_PATH
    return LEGACY_DB_PATH


DB_PATH = resolve_db_path()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
SYNC_INTERVAL_MS = 1500

INITIAL_COINS = 1000
INITIAL_DIAMONDS = 50
DEMOLISH_COST = 10

# 濠碘槅鍋嗘晶妤冨垝韫囨梻鐝跺┑鐘叉搐闁裤倖淇婇妶鍌氫壕闂佸憡顭堥～澶愬箚閺冨牆鍗虫い蹇撴閻涱櫀NG 缂傚倷绶￠崰鏍ㄦ櫠閼恒儱顕遍柟鐑樻⒒绾句粙鏌涘┑鍡楊仴濞存粌銈搁弻锟犲礃閳哄倹鐎紓渚囧枟閻╊垰鐣烽敐澶樻晬婵炴垵宕俊褔鏌ｉ姀鈺佺仩闁硅姤绮庨弫顔济洪鍕?WHITE = (255, 255, 255)
BLACK = (25, 25, 25)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (40, 44, 52)
GREEN = (46, 168, 76)
ROAD_GRAY = (118, 124, 131)
BLUE = (64, 118, 255)
GOLD = (255, 196, 0)
PURPLE = (152, 86, 255)
RED = (235, 79, 79)
GRASS_BG = (126, 191, 84)
PANEL_BG = (26, 28, 34)
CYAN = (115, 223, 255)

OBJECT_TYPE_ORDER = ["plant", "road", "building_b", "building_a", "building_s"]

DEFAULT_TYPE_CONFIG = {
    "plant": {
        "name": "Plant",
        "price": 100,
        "currency": "coins",
        "color": GREEN,
        "size": (84, 84),
        "hotkey": pygame.K_1,
        "tier": "Plant",
        "priority": ("tree-large", "planter", "tree-small"),
    },
    "road": {
        "name": "Road",
        "price": 50,
        "currency": "coins",
        "color": ROAD_GRAY,
        "size": (72, 40),
        "hotkey": pygame.K_2,
        "tier": "Road",
        "priority": ("road-straight", "road-crossroad", "road-bend", "bridge"),
    },
    "building_b": {
        "name": "B级建筑",
        "price": 300,
        "currency": "coins",
        "color": BLUE,
        "size": (88, 120),
        "hotkey": pygame.K_3,
        "tier": "B",
        "priority": ("building-a", "building-type-a", "building-type-b"),
    },
    "building_a": {
        "name": "A级建筑",
        "price": 500,
        "currency": "coins",
        "color": GOLD,
        "size": (96, 136),
        "hotkey": pygame.K_4,
        "tier": "A",
        "priority": ("building-a", "building-b", "low-detail-building-a"),
    },
    "building_s": {
        "name": "S级建筑",
        "price": 10,
        "currency": "diamonds",
        "color": PURPLE,
        "size": (112, 164),
        "hotkey": pygame.K_5,
        "tier": "S",
        "priority": ("building-skyscraper-a", "building-skyscraper-b", "building-skyscraper-c"),
    },
}


@dataclass(frozen=True)
class BuildingSpec:
    code: str
    name: str
    price: int
    currency: str
    color: Tuple[int, int, int]
    size: Tuple[int, int]
    hotkey: int
    tier: str
    sprite_path: str = ""
    source_item_code: str = ""


@dataclass
class PlacedObject:
    object_id: int
    object_type: str
    x: int
    y: int

    @property
    def spec(self) -> BuildingSpec:
        return BUILDINGS[self.object_type]

    @property
    def rect(self) -> pygame.Rect:
        width, height = self.spec.size
        return pygame.Rect(self.x, self.y, width, height)

    @property
    def sort_y(self) -> int:
        # Sort by the object's bottom edge so layering feels natural.
        return self.y + self.spec.size[1]

def load_cn_font(size: int) -> pygame.font.Font:
    """Prefer a Chinese-capable font so the UI text can render correctly."""
    for font_name in ("microsoftyahei", "simhei", "simsun", "arialunicode"):
        font_path = pygame.font.match_font(font_name)
        if font_path:
            return pygame.font.Font(font_path, size)
    return pygame.font.Font(None, size)


def normalize_sprite_path(sprite_path: str) -> str:
    if not sprite_path:
        return ""
    path = Path(sprite_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


def build_default_spec(object_type: str) -> BuildingSpec:
    cfg = DEFAULT_TYPE_CONFIG[object_type]
    return BuildingSpec(
        code=object_type,
        name=cfg["name"],
        price=cfg["price"],
        currency=cfg["currency"],
        color=cfg["color"],
        size=cfg["size"],
        hotkey=cfg["hotkey"],
        tier=cfg["tier"],
    )


def pick_manifest_item(object_type: str, items: List[dict]) -> Optional[dict]:
    candidates = [item for item in items if item.get("object_type") == object_type]
    if not candidates:
        return None

    priority_names = DEFAULT_TYPE_CONFIG[object_type]["priority"]

    def score(item: dict) -> Tuple[int, str]:
        item_code = str(item.get("item_code", ""))
        source_path = str(item.get("source_obj_path", ""))
        for index, keyword in enumerate(priority_names):
            if keyword in item_code or keyword in source_path:
                return index, item_code
        return len(priority_names), item_code

    return sorted(candidates, key=score)[0]


def load_buildings_from_manifest() -> Dict[str, BuildingSpec]:
    buildings = {object_type: build_default_spec(object_type) for object_type in OBJECT_TYPE_ORDER}
    if not MANIFEST_PATH.exists():
        return buildings

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] 闂佽崵濮村ú鈺咁敋瑜戦妵?manifest 濠电姰鍨洪崕鑲╁垝閸撗勫枂闁挎洖鍊归弲顒勬倶閻愯泛袚缂佲偓閳ь剟姊绘笟鍥т簮闁稿鎸歌灋闁绘鐗忛惌搴☆熆閻熷府韬€? {exc}")
        return buildings

    for object_type in OBJECT_TYPE_ORDER:
        chosen = pick_manifest_item(object_type, manifest.get("items", []))
        if not chosen:
            continue

        sprite_path = normalize_sprite_path(str(chosen.get("sprite_path", "")))
        if sprite_path and not Path(sprite_path).exists():
            print(f"[WARN] {object_type} 闂?PNG 濠电偞鍨堕幐鍝ョ矓閹绢喗鍋ら柕濞炬櫅閹硅埖銇勯鐔风缂佲偓婢舵劖鐓曢柕澹啩妲愰梺閫炲苯鍘撮柛瀣尭铻為柣妤€鐗忛惌搴☆熆閻熷府韬€? {sprite_path}")
            continue

        cfg = DEFAULT_TYPE_CONFIG[object_type]
        size = chosen.get("size") or cfg["size"]
        buildings[object_type] = BuildingSpec(
            code=object_type,
            name=cfg["name"],
            price=int(chosen.get("price", cfg["price"])),
            currency=str(chosen.get("currency", cfg["currency"])),
            color=cfg["color"],
            size=(int(size[0]), int(size[1])),
            hotkey=cfg["hotkey"],
            tier=str(chosen.get("tier", cfg["tier"])),
            sprite_path=sprite_path,
            source_item_code=str(chosen.get("item_code", "")),
        )
    return buildings


BUILDINGS: Dict[str, BuildingSpec] = load_buildings_from_manifest()


class CityRepository:
    """Persist the Pygame city data in the project database."""
    def __init__(self, db_path: Path, username: str) -> None:
        self.db_path = str(db_path)
        self.username = username
        self.initialize_schema()
        self.bootstrap_player()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=5)

    def _table_columns(self, cursor: sqlite3.Cursor, table_name: str) -> set[str]:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1] for row in cursor.fetchall()}

    def initialize_schema(self) -> None:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS User_Growth (
                    username TEXT PRIMARY KEY,
                    focus_energy INTEGER DEFAULT 0,
                    total_focus_minutes INTEGER DEFAULT 0,
                    streak_days INTEGER DEFAULT 0,
                    last_active_date DATE,
                    diamonds INTEGER DEFAULT 50,
                    sunshine INTEGER DEFAULT 50,
                    coins INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            columns = self._table_columns(c, "User_Growth")
            for column_name, ddl in (
                ("focus_energy", "ALTER TABLE User_Growth ADD COLUMN focus_energy INTEGER DEFAULT 0"),
                ("total_focus_minutes", "ALTER TABLE User_Growth ADD COLUMN total_focus_minutes INTEGER DEFAULT 0"),
                ("streak_days", "ALTER TABLE User_Growth ADD COLUMN streak_days INTEGER DEFAULT 0"),
                ("last_active_date", "ALTER TABLE User_Growth ADD COLUMN last_active_date DATE"),
                ("diamonds", "ALTER TABLE User_Growth ADD COLUMN diamonds INTEGER DEFAULT 50"),
                ("sunshine", "ALTER TABLE User_Growth ADD COLUMN sunshine INTEGER DEFAULT 50"),
                ("coins", "ALTER TABLE User_Growth ADD COLUMN coins INTEGER DEFAULT 1000"),
            ):
                if column_name not in columns:
                    c.execute(ddl)

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS Pygame_City_Profile (
                    username TEXT PRIMARY KEY,
                    initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS Pygame_City_Objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def bootstrap_player(self) -> None:
        """Seed the player with initial currency on first entry."""
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM Pygame_City_Profile WHERE username = ?", (self.username,))
            city_profile_exists = c.fetchone() is not None

            c.execute(
                """
                INSERT OR IGNORE INTO User_Growth
                    (username, focus_energy, total_focus_minutes, streak_days, diamonds, sunshine, coins)
                VALUES (?, 0, 0, 0, ?, ?, ?)
                """,
                (self.username, INITIAL_DIAMONDS, INITIAL_DIAMONDS, INITIAL_COINS),
            )

            if not city_profile_exists:
                coins, diamonds = self.read_wallet_row(c)
                c.execute(
                    "UPDATE User_Growth SET coins = ?, diamonds = ?, sunshine = ? WHERE username = ?",
                    (max(coins, INITIAL_COINS), max(diamonds, INITIAL_DIAMONDS), max(diamonds, INITIAL_DIAMONDS), self.username),
                )
                c.execute("INSERT OR IGNORE INTO Pygame_City_Profile (username) VALUES (?)", (self.username,))

    def read_wallet_row(self, c: sqlite3.Cursor) -> Tuple[int, int]:
        c.execute(
            "SELECT COALESCE(coins, 0), COALESCE(diamonds, 0), COALESCE(sunshine, 0) "
            "FROM User_Growth WHERE username = ?",
            (self.username,),
        )
        row = c.fetchone()
        if not row:
            return INITIAL_COINS, INITIAL_DIAMONDS
        sunshine_value = int(row[2] or 0)
        diamonds = sunshine_value if sunshine_value > 0 else int(row[1] or 0)
        return int(row[0]), max(diamonds, 0)

    def load_wallet(self) -> Tuple[int, int]:
        with self._connect() as conn:
            c = conn.cursor()
            coins, diamonds = self.read_wallet_row(c)
            c.execute(
                "UPDATE User_Growth SET diamonds = ?, sunshine = ? WHERE username = ?",
                (diamonds, diamonds, self.username),
            )
            return coins, diamonds

    def load_objects(self) -> List[PlacedObject]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, object_type, x, y
                FROM Pygame_City_Objects
                WHERE username = ?
                ORDER BY y ASC, id ASC
                """,
                (self.username,),
            )
            return [
                PlacedObject(int(object_id), str(object_type), int(x), int(y))
                for object_id, object_type, x, y in c.fetchall()
                if object_type in BUILDINGS
            ]

    def buy_and_place(self, object_type: str, x: int, y: int) -> Tuple[bool, str, Optional[PlacedObject], int, int]:
        spec = BUILDINGS[object_type]
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            coins, diamonds = self.read_wallet_row(c)

            if spec.currency == "coins":
                if coins < spec.price:
                    return False, f"Not enough coins to buy {spec.name}. Need {spec.price} coins.", None, coins, diamonds
                coins -= spec.price
            else:
                if diamonds < spec.price:
                    return False, f"Not enough diamonds to buy {spec.name}. Need {spec.price} diamonds.", None, coins, diamonds
                diamonds -= spec.price

            c.execute(
                "UPDATE User_Growth SET coins = ?, diamonds = ?, sunshine = ? WHERE username = ?",
                (coins, diamonds, diamonds, self.username),
            )
            c.execute(
                "INSERT INTO Pygame_City_Objects (username, object_type, x, y) VALUES (?, ?, ?, ?)",
                (self.username, object_type, x, y),
            )
            new_object = PlacedObject(int(c.lastrowid), object_type, x, y)

        currency_name = "diamonds" if spec.currency == "diamonds" else "coins"
        return True, f"Placed {spec.name} for {spec.price} {currency_name}.", new_object, coins, diamonds

    def demolish(self, object_id: int) -> Tuple[bool, str, int, int]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            coins, diamonds = self.read_wallet_row(c)

            if coins < DEMOLISH_COST:
                return False, "Not enough coins to demolish. Need more coins.", coins, diamonds

            c.execute(
                "SELECT object_type FROM Pygame_City_Objects WHERE id = ? AND username = ?",
                (object_id, self.username),
            )
            row = c.fetchone()
            if not row or row[0] not in BUILDINGS:
                return False, "Object not found or cannot be demolished.", coins, diamonds

            coins -= DEMOLISH_COST
            c.execute(
                "UPDATE User_Growth SET coins = ?, diamonds = ?, sunshine = ? WHERE username = ?",
                (coins, diamonds, diamonds, self.username),
            )
            c.execute(
                "DELETE FROM Pygame_City_Objects WHERE id = ? AND username = ?",
                (object_id, self.username),
            )

        return True, f"Demolished {BUILDINGS[row[0]].name}. Refunded {-DEMOLISH_COST} coins.", coins, diamonds


class CityBuilderGame:
    def __init__(self, username: str) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("FocusPort City Builder - OBJ Sprite Edition")

        self.font_large = load_cn_font(32)
        self.font_medium = load_cn_font(24)
        self.font_small = load_cn_font(18)

        self.username = username
        self.repo = CityRepository(DB_PATH, username)
        self.coins, self.diamonds = self.repo.load_wallet()
        self.placed_objects = self.repo.load_objects()

        self.selected_type: Optional[str] = None
        self.recycle_mode = False
        self.message = self.startup_message()
        self.message_color = CYAN
        self.message_until = pygame.time.get_ticks() + 3200
        self.last_wallet_sync = 0

        self.sprite_cache: Dict[str, pygame.Surface] = {}
        self.preview_cache: Dict[str, pygame.Surface] = {}
        self.build_area = pygame.Rect(40, 80, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 210)
        self.clock = pygame.time.Clock()

    def startup_message(self) -> str:
        if MANIFEST_PATH.exists() and any(spec.sprite_path for spec in BUILDINGS.values()):
            return "Loaded OBJ-derived PNG sprites from the manifest for the city builder."
        return "Manifest not found. Falling back to color blocks until city_sprite_manifest.json is available."

    def show_message(self, text: str, color: Tuple[int, int, int] = WHITE, duration: int = 2200) -> None:
        self.message = text
        self.message_color = color
        self.message_until = pygame.time.get_ticks() + duration

    def sync_wallet_from_db(self) -> None:
        now = pygame.time.get_ticks()
        if now - self.last_wallet_sync < SYNC_INTERVAL_MS:
            return
        self.last_wallet_sync = now

        latest_coins, latest_diamonds = self.repo.load_wallet()
        if latest_coins > self.coins or latest_diamonds > self.diamonds:
            self.show_message(
                f"Wallet synced: coins {self.coins} -> {latest_coins}, diamonds {self.diamonds} -> {latest_diamonds}",
                CYAN,
                2600,
            )
        self.coins = latest_coins
        self.diamonds = latest_diamonds

    def get_sprite(self, spec: BuildingSpec) -> Optional[pygame.Surface]:
        if not spec.sprite_path:
            return None
        if spec.sprite_path in self.sprite_cache:
            return self.sprite_cache[spec.sprite_path]
        if not Path(spec.sprite_path).exists():
            return None

        surface = pygame.image.load(spec.sprite_path).convert_alpha()
        surface = pygame.transform.smoothscale(surface, spec.size)
        self.sprite_cache[spec.sprite_path] = surface
        return surface

    def get_preview_sprite(self, spec: BuildingSpec) -> Optional[pygame.Surface]:
        sprite = self.get_sprite(spec)
        if sprite is None:
            return None
        if spec.code not in self.preview_cache:
            preview = sprite.copy()
            preview.set_alpha(150)
            self.preview_cache[spec.code] = preview
        return self.preview_cache[spec.code]

    def find_object_at(self, mouse_pos: Tuple[int, int]) -> Optional[PlacedObject]:
        for obj in sorted(self.placed_objects, key=lambda item: item.sort_y, reverse=True):
            if obj.rect.collidepoint(mouse_pos):
                return obj
        return None

    def is_overlapping_existing(self, rect: pygame.Rect) -> bool:
        return any(rect.colliderect(obj.rect) for obj in self.placed_objects)

    def try_place(self, mouse_pos: Tuple[int, int]) -> None:
        if not self.selected_type:
            self.show_message("Press 1-5 to select a building type before placing.", GOLD)
            return

        spec = BUILDINGS[self.selected_type]
        width, height = spec.size
        x = mouse_pos[0] - width // 2
        y = mouse_pos[1] - height
        target_rect = pygame.Rect(x, y, width, height)

        if not self.build_area.contains(target_rect):
            self.show_message("Placement must stay inside the build area.", RED)
            return

        if self.is_overlapping_existing(target_rect):
            self.show_message("This spot overlaps an existing object.", RED)
            return

        ok, message, new_obj, self.coins, self.diamonds = self.repo.buy_and_place(self.selected_type, x, y)
        if ok and new_obj:
            self.placed_objects.append(new_obj)
            self.show_message(message, (128, 255, 160))
        else:
            self.show_message(message, RED)

    def try_demolish(self, mouse_pos: Tuple[int, int]) -> None:
        target = self.find_object_at(mouse_pos)
        if not target:
            self.show_message("No object found at the current cursor position.", RED)
            return

        ok, message, self.coins, self.diamonds = self.repo.demolish(target.object_id)
        if ok:
            self.placed_objects = [obj for obj in self.placed_objects if obj.object_id != target.object_id]
            self.show_message(message, (255, 214, 138))
        else:
            self.show_message(message, RED)

    def toggle_recycle_mode(self) -> None:
        self.recycle_mode = not self.recycle_mode
        self.selected_type = None
        pygame.mouse.set_visible(not self.recycle_mode)
        if self.recycle_mode:
            self.show_message("Recycle mode enabled. Click a placed object to remove it for a coin cost.", RED)
        else:
            self.show_message("Recycle mode disabled.", LIGHT_GRAY)

    def select_building(self, object_type: str) -> None:
        self.selected_type = object_type
        self.recycle_mode = False
        pygame.mouse.set_visible(True)
        spec = BUILDINGS[object_type]
        currency_name = "diamonds" if spec.currency == "diamonds" else "coins"
        source_hint = f" | {spec.source_item_code}" if spec.source_item_code else ""
        self.show_message(f"Selected {spec.name} for {spec.price} {currency_name}{source_hint}", WHITE)

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.selected_type = None
                    self.recycle_mode = False
                    pygame.mouse.set_visible(True)
                    self.show_message("Selection cleared.", LIGHT_GRAY)
                elif event.key == pygame.K_r:
                    self.toggle_recycle_mode()
                else:
                    for object_type, spec in BUILDINGS.items():
                        if event.key == spec.hotkey:
                            self.select_building(object_type)
                            break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.recycle_mode:
                    self.try_demolish(event.pos)
                else:
                    self.try_place(event.pos)

        return True

    def draw_ground(self) -> None:
        self.screen.fill(DARK_GRAY)
        pygame.draw.rect(self.screen, GRASS_BG, self.build_area, border_radius=18)
        pygame.draw.rect(self.screen, (73, 117, 53), self.build_area, width=4, border_radius=18)

        # Draw a light grid over the build area.
        for x in range(self.build_area.left + 40, self.build_area.right, 80):
            pygame.draw.line(
                self.screen,
                (150, 205, 110),
                (x, self.build_area.top + 14),
                (x, self.build_area.bottom - 14),
                1,
            )
        for y in range(self.build_area.top + 40, self.build_area.bottom, 80):
            pygame.draw.line(
                self.screen,
                (150, 205, 110),
                (self.build_area.left + 14, y),
                (self.build_area.right - 14, y),
                1,
            )

    def draw_fallback_block(self, rect: pygame.Rect, spec: BuildingSpec) -> None:
        pygame.draw.rect(self.screen, spec.color, rect, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, rect, width=2, border_radius=8)

        if spec.code == "road":
            pygame.draw.line(self.screen, (245, 235, 180), (rect.left + 6, rect.centery), (rect.right - 6, rect.centery), 3)
        elif spec.code == "plant":
            pygame.draw.rect(self.screen, (118, 78, 42), (rect.centerx - 4, rect.centery, 8, 16), border_radius=4)
            pygame.draw.circle(self.screen, (86, 222, 115), (rect.centerx, rect.centery - 4), 16)

    def draw_object(self, obj: PlacedObject) -> None:
        rect = obj.rect
        spec = obj.spec

        if spec.code == "building_s":
            glow_rect = rect.inflate(22, 24)
            glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (185, 120, 255, 70), glow_surface.get_rect(), border_radius=22)
            self.screen.blit(glow_surface, glow_rect.topleft)

        sprite = self.get_sprite(spec)
        if sprite is not None:
            self.screen.blit(sprite, rect.topleft)
        else:
            self.draw_fallback_block(rect, spec)

        if spec.code == "building_s":
            pygame.draw.rect(self.screen, PURPLE, rect.inflate(6, 6), width=3, border_radius=12)

        label = self.font_small.render(spec.name, True, WHITE)
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.top + 6))

    def draw_preview(self) -> None:
        if not self.selected_type or self.recycle_mode:
            return

        spec = BUILDINGS[self.selected_type]
        width, height = spec.size
        mx, my = pygame.mouse.get_pos()
        x = mx - width // 2
        y = my - height

        preview_sprite = self.get_preview_sprite(spec)
        if preview_sprite is not None:
            self.screen.blit(preview_sprite, (x, y))
            pygame.draw.rect(self.screen, spec.color, (x, y, width, height), width=2, border_radius=8)
            return

        preview_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        preview_surface.fill((*spec.color, 128))
        self.screen.blit(preview_surface, (x, y))
        pygame.draw.rect(self.screen, spec.color, (x, y, width, height), width=2, border_radius=8)

    def draw_recycle_cursor(self) -> None:
        if not self.recycle_mode:
            return
        mx, my = pygame.mouse.get_pos()
        cursor_rect = pygame.Rect(mx - 18, my - 18, 36, 36)
        pygame.draw.rect(self.screen, RED, cursor_rect, width=3, border_radius=6)
        pygame.draw.line(self.screen, RED, (mx - 10, my - 10), (mx + 10, my + 10), 3)
        pygame.draw.line(self.screen, RED, (mx + 10, my - 10), (mx - 10, my + 10), 3)

    def draw_wallet_ui(self) -> None:
        pygame.draw.rect(self.screen, PANEL_BG, (20, 14, 240, 58), border_radius=14)
        coin_surface = self.font_medium.render(f"Coins: {self.coins}", True, GOLD)
        diamond_surface = self.font_medium.render(f"Diamonds: {self.diamonds}", True, CYAN)
        self.screen.blit(coin_surface, (36, 18))
        self.screen.blit(diamond_surface, (36, 44))

        user_surface = self.font_small.render(f"Player: {self.username}", True, LIGHT_GRAY)
        self.screen.blit(user_surface, (SCREEN_WIDTH - user_surface.get_width() - 28, 24))

    def current_mode_text(self) -> str:
        if self.recycle_mode:
            return "Mode: recycle"
        if self.selected_type:
            return f"Mode: place [{BUILDINGS[self.selected_type].name}]"
        return "Mode: idle. Press 1-5 to choose, R to recycle, ESC to cancel."

    def draw_bottom_ui(self) -> None:
        mode_surface = self.font_medium.render(self.current_mode_text(), True, RED if self.recycle_mode else WHITE)
        self.screen.blit(mode_surface, ((SCREEN_WIDTH - mode_surface.get_width()) // 2, SCREEN_HEIGHT - 112))

        help_text = (
            "1 Plant 100 coins | 2 Road 50 coins | 3 B Building 300 coins | "
            "4 A Building 500 coins | 5 S Building 10 diamonds | R Demolish | ESC Cancel"
        )
        help_surface = self.font_small.render(help_text, True, LIGHT_GRAY)
        self.screen.blit(help_surface, ((SCREEN_WIDTH - help_surface.get_width()) // 2, SCREEN_HEIGHT - 52))

    def draw_message(self) -> None:
        if not self.message or pygame.time.get_ticks() > self.message_until:
            return
        msg_surface = self.font_medium.render(self.message, True, self.message_color)
        msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 148))
        panel_rect = msg_rect.inflate(24, 16)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.message_color, panel_rect, width=2, border_radius=10)
        self.screen.blit(msg_surface, msg_rect)

    def render(self) -> None:
        self.draw_ground()

        # Render placed objects sorted by their bottom edge.
        for obj in sorted(self.placed_objects, key=lambda item: item.sort_y):
            self.draw_object(obj)

        self.draw_preview()
        self.draw_recycle_cursor()
        self.draw_wallet_ui()
        self.draw_bottom_ui()
        self.draw_message()
        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            running = self.handle_events()
            self.sync_wallet_from_db()
            self.render()
            self.clock.tick(FPS)

        pygame.mouse.set_visible(True)
        pygame.quit()


def main() -> None:
    username = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_USERNAME
    game = CityBuilderGame(username)
    game.run()


if __name__ == "__main__":
    main()

