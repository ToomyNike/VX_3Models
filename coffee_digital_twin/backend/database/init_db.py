import sqlite3
from datetime import datetime

from config import DATABASE_PATH, ensure_dirs


def get_connection():
    ensure_dirs()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    ensure_dirs()
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS plots (
                plot_id TEXT PRIMARY KEY,
                plot_name TEXT NOT NULL,
                crop TEXT NOT NULL DEFAULT 'coffee',
                coffee_variety TEXT,
                area_mu REAL,
                tree_age INTEGER,
                latitude REAL,
                longitude REAL,
                elevation_m REAL,
                soil_type TEXT,
                shade_level TEXT,
                plant_density REAL,
                row_spacing_m REAL,
                plant_spacing_m REAL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS farm_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plot_id TEXT NOT NULL,
                op_type TEXT NOT NULL,
                op_date TEXT NOT NULL,
                amount REAL,
                unit TEXT,
                fertilizer_type TEXT,
                operation_type TEXT,
                severity TEXT,
                remark TEXT,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_tasks (
                task_id TEXT PRIMARY KEY,
                plot_id TEXT NOT NULL,
                scenario_name TEXT,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_results (
                task_id TEXT PRIMARY KEY,
                plot_id TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS advice_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                advice_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


if __name__ == "__main__":
    init_db()
    print(f"SQLite database initialized: {DATABASE_PATH}")
