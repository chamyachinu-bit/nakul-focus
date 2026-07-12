"""
migrate_to_supabase.py
Copies all local SQLite data into Supabase (PostgreSQL).
Run once:  python migrate_to_supabase.py
"""

import sqlite3
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse, unquote

SQLITE_PATH = r"D:\Nakul.exe\nakul-focus\nakul_focus.db"
PG_URL = "postgresql://postgres.ygdjgauciciswplwnnbh:Basuri%40321123@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

# Tables in dependency order
TABLES = [
    "settings",
    "habits",
    "habit_logs",
    "reminders",
    "focus_sessions",
    "work_sessions",
    "weight_logs",
    "mood_logs",
    "bali_fund",
    "timetable_entries",
    "timetable_logs",
]


def pg_connect(url):
    p = urlparse(url.replace("postgresql://", "https://", 1))
    return psycopg2.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=(p.path or "/postgres").lstrip("/") or "postgres",
        user=unquote(p.username or ""),
        password=unquote(p.password or ""),
        sslmode="require",
        connect_timeout=15,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def migrate():
    print("Connecting to SQLite...")
    sqlite = sqlite3.connect(SQLITE_PATH)
    sqlite.row_factory = sqlite3.Row

    print("Connecting to Supabase...")
    pg = pg_connect(PG_URL)
    pg.autocommit = False

    for table in TABLES:
        rows = sqlite.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: 0 rows — skipping")
            continue

        cols = list(rows[0].keys())
        col_list = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))

        # Build upsert: if row with same PK exists, skip it
        if "id" in cols:
            conflict = "ON CONFLICT (id) DO NOTHING"
        elif table == "settings":
            conflict = "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        elif table == "habit_logs":
            conflict = "ON CONFLICT (habit_id, date) DO NOTHING"
        elif table == "timetable_logs":
            conflict = "ON CONFLICT (entry_id, date) DO NOTHING"
        else:
            conflict = ""

        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) {conflict}"

        cur = pg.cursor()
        count = 0
        for row in rows:
            values = [row[c] for c in cols]
            try:
                cur.execute(sql, values)
                count += 1
            except Exception as e:
                pg.rollback()
                print(f"  {table} row error: {e}")
                break
        else:
            pg.commit()

        # Reset the sequence so new inserts after migration don't collide
        if "id" in cols and table != "settings":
            try:
                cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}")
                pg.commit()
            except Exception:
                pg.rollback()

        print(f"  {table}: {count} rows migrated")

    sqlite.close()
    pg.close()
    print("\nDone. All local data is now in Supabase.")


if __name__ == "__main__":
    migrate()
