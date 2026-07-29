import argparse
import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
MAIN_PATH = BASE_DIR / "main.py"
DEFAULT_DB_PATH = BASE_DIR / "focusport_test.db"


def extract_schema() -> str:
    source = MAIN_PATH.read_text(encoding="utf-8-sig")
    match = re.search(r"conn\.executescript\(\s*\"\"\"\s*(.*?)\s*\"\"\"\s*\)", source, re.S)
    if not match:
        raise RuntimeError("Could not find init_db executescript schema in main.py")
    return match.group(1)


def seed_user(conn: sqlite3.Connection, username: str, password: str, coins: int = 1200) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO Users (username, password, avatar, nickname, bio) VALUES (?, ?, ?, ?, ?)",
        (username, password, "test", username, "Test account"),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO User_Growth (
            username, focus_energy, total_focus_minutes, streak_days, sunshine, coins, diamonds,
            exp, level, discipline_score, max_streak, total_trees, achievements_count
        ) VALUES (?, 80, 150, 2, 320, ?, 50, 240, 3, 72.5, 2, 4, 0)
        """,
        (username, coins),
    )


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply_migrations(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "Users", "nickname", "TEXT DEFAULT ''")
    ensure_column(conn, "Users", "bio", "TEXT DEFAULT ''")
    ensure_column(conn, "User_Growth", "exp", "INTEGER DEFAULT 0")
    ensure_column(conn, "User_Growth", "level", "INTEGER DEFAULT 1")
    ensure_column(conn, "User_Growth", "discipline_score", "REAL DEFAULT 50")
    ensure_column(conn, "User_Growth", "max_streak", "INTEGER DEFAULT 0")
    ensure_column(conn, "User_Growth", "total_trees", "INTEGER DEFAULT 0")
    ensure_column(conn, "User_Growth", "achievements_count", "INTEGER DEFAULT 0")
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
    ensure_column(conn, "Todo_Tasks", "duration_minutes", "INTEGER DEFAULT 25")
    ensure_column(conn, "Todo_Tasks", "priority", "TEXT DEFAULT 'middle'")
    ensure_column(conn, "Todo_Tasks", "reminder_minutes", "INTEGER DEFAULT 15")
    ensure_column(conn, "Todo_Tasks", "recurrence", "TEXT DEFAULT 'none'")
    ensure_column(conn, "Todo_Tasks", "completed_at", "TIMESTAMP")


def seed_data(conn: sqlite3.Connection) -> None:
    seed_user(conn, "test_user", "test123", 1200)
    seed_user(conn, "friend_user", "test123", 900)
    seed_user(conn, "admin_test", "FocusPortAdmin888", 999999999)

    conn.execute(
        """
        INSERT INTO Todo_Tasks (
            username, content, scheduled_date, scheduled_time, status, category, duration_minutes, priority, reminder_minutes
        ) VALUES
            ('test_user', '完成数学错题复盘', date('now', 'localtime'), '19:30', 'todo', '数学', 45, '高', 15),
            ('test_user', '测试番茄钟奖励流程', date('now', 'localtime'), '20:30', 'todo', 'FocusPort', 25, '中', 5),
            ('friend_user', '验证好友请求接收', date('now', 'localtime'), '18:00', 'todo', '测试', 15, '中', 0)
        """
    )
    conn.execute(
        """
        INSERT INTO Focus_Sessions (username, subject, duration_minutes, status, session_log, final_energy)
        VALUES
            ('test_user', '数学', 45, 'completed', '完成函数专题复盘。', 90),
            ('test_user', '英语', 30, 'completed', '背诵核心词汇。', 60)
        """
    )
    conn.execute(
        """
        INSERT INTO AI_Chats (username, role, content, conversation_id)
        VALUES
            ('test_user', 'user', '怎样提升数学成绩', 'test'),
            ('test_user', 'assistant', '先按错因分类，再做限时训练。', 'test')
        """
    )
    conn.execute(
        """
        INSERT INTO Phone_Usage (username, usage_minutes, category, notes)
        VALUES ('test_user', 160, '娱乐', '测试数据：娱乐 160 分钟，社交 441 分钟，工具 32 分钟。')
        """
    )
    conn.execute(
        """
        INSERT INTO Sunshine_Transactions (username, amount, transaction_type, source, description)
        VALUES
            ('test_user', 90, 'earn', 'focus_complete', '测试专注奖励'),
            ('test_user', -25, 'spend', 'arcade_room_create', '测试创建房间消耗')
        """
    )


def create_test_db(db_path: Path, reset: bool) -> None:
    if reset and db_path.exists():
        if "test" not in db_path.stem.lower():
            raise RuntimeError(f"Refusing to reset non-test database: {db_path}")
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(extract_schema())
        apply_migrations(conn)
        seed_data(conn)
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local FocusPort SQLite database for testing.")
    parser.add_argument("--path", default=str(DEFAULT_DB_PATH), help="Database path. Defaults to focusport_test.db.")
    parser.add_argument("--reset", action="store_true", help="Recreate the database if it already exists.")
    args = parser.parse_args()

    db_path = Path(args.path)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    create_test_db(db_path, args.reset)
    print(f"Created test database: {db_path}")
    print("Accounts: test_user/test123, friend_user/test123, admin_test/FocusPortAdmin888")
    print(f"Run with this database by setting FOCUSPORT_DB_PATH={db_path}")


if __name__ == "__main__":
    main()
