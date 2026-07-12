"""
database.py -- Dual-mode DB layer: SQLite locally, PostgreSQL (Supabase) in cloud.

If DATABASE_URL env var is set  -> uses PostgreSQL (Supabase / Vercel).
Otherwise                       -> uses local SQLite file (offline, original behaviour).

The PostgreSQL wrapper makes all existing code work unchanged:
  - conn.execute(sql, params)  works exactly like sqlite3
  - row["key"] and row[0]      both work on result rows
  - cursor.lastrowid           works via RETURNING id
"""

import os
import re
import hashlib
import compat  # noqa: F401

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# ── SQLite path (local fallback) ───────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(_BASE_DIR, "nakul_focus.db")


# ══════════════════════════════════════════════════════════════════════════════
#  POSTGRESQL ADAPTER
# ══════════════════════════════════════════════════════════════════════════════

def _fix_sql(sql: str) -> str:
    """Convert SQLite SQL dialect to PostgreSQL."""
    # Parameter placeholders
    sql = sql.replace("?", "%s")
    # Date / time functions
    sql = sql.replace("date('now')", "CURRENT_DATE")
    sql = sql.replace("DATE('now')", "CURRENT_DATE")
    sql = sql.replace("(date('now'))", "CURRENT_DATE")
    sql = sql.replace("DEFAULT (CURRENT_DATE)", "DEFAULT CURRENT_DATE")
    # strftime → PostgreSQL equivalents
    sql = re.sub(r"strftime\s*\(\s*'%Y'\s*,\s*(\w+)\s*\)",
                 r"EXTRACT(YEAR FROM \1::date)::text", sql)
    sql = re.sub(r"strftime\s*\(\s*'%m'\s*,\s*(\w+)\s*\)",
                 r"TO_CHAR(\1::date, 'MM')", sql)
    # CREATE TABLE fixes
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
    sql = sql.replace("REAL", "DOUBLE PRECISION")
    # PRAGMA → no-op marker
    if sql.strip().upper().startswith("PRAGMA"):
        return "__SKIP__"
    return sql


class _Row(dict):
    """Dict that also supports integer indexing (row[0]) for aggregate queries."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _Cursor:
    """Wraps a psycopg2 cursor to match the sqlite3 cursor interface."""

    def __init__(self, pg_cur):
        self._cur   = pg_cur
        self.lastrowid = None

    def execute(self, sql: str, params=()):
        sql = _fix_sql(sql)
        if sql == "__SKIP__":
            return self

        needs_returning = (
            sql.strip().upper().startswith("INSERT")
            and "RETURNING" not in sql.upper()
        )
        if needs_returning:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"

        self._cur.execute(sql, params if params else None)

        if needs_returning:
            try:
                row = self._cur.fetchone()
                if row:
                    self.lastrowid = row.get("id") or row.get("ID")
            except Exception:
                pass
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return _Row(row) if row is not None else None

    def fetchall(self):
        return [_Row(r) for r in (self._cur.fetchall() or [])]

    def __iter__(self):
        return iter(self.fetchall())


class _PgConnection:
    """Wraps psycopg2 connection to match the sqlite3.Connection interface."""

    def __init__(self, url: str):
        import psycopg2
        import psycopg2.extras
        self._conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql: str, params=()):
        wrapper = _Cursor(self._conn.cursor())
        wrapper.execute(sql, params)
        return wrapper

    def cursor(self):
        return _Cursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    # Ignored -- kept for interface compatibility
    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, _):
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def get_connection():
    """Return a DB connection. PostgreSQL if DATABASE_URL is set, else SQLite."""
    if DATABASE_URL:
        return _PgConnection(DATABASE_URL)

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create all tables. Safe to call on every startup (CREATE IF NOT EXISTS)."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            category   TEXT DEFAULT 'general',
            active     INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id  INTEGER NOT NULL,
            date      TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            notes     TEXT,
            UNIQUE(habit_id, date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            duration_mins INTEGER NOT NULL,
            mode          TEXT DEFAULT 'pomodoro',
            completed     INTEGER DEFAULT 0,
            project       TEXT,
            date          TEXT DEFAULT (date('now')),
            start_time    TEXT,
            end_time      TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS work_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project       TEXT NOT NULL,
            duration_mins INTEGER NOT NULL,
            work_type     TEXT DEFAULT 'freelance',
            income        REAL DEFAULT 0,
            notes         TEXT,
            date          TEXT DEFAULT (date('now')),
            start_time    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            weight_kg REAL NOT NULL,
            date      TEXT DEFAULT (date('now')),
            notes     TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mood_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            mood_score INTEGER NOT NULL,
            mood_label TEXT,
            date       TEXT DEFAULT (date('now')),
            time       TEXT,
            notes      TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            time    TEXT NOT NULL,
            message TEXT NOT NULL,
            active  INTEGER DEFAULT 1,
            days    TEXT DEFAULT 'daily'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bali_fund (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            amount     REAL NOT NULL,
            entry_type TEXT DEFAULT 'deposit',
            date       TEXT DEFAULT (date('now')),
            notes      TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS timetable_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            time_start  TEXT NOT NULL,
            time_end    TEXT,
            name        TEXT NOT NULL,
            category    TEXT DEFAULT 'work',
            note        TEXT DEFAULT '',
            days        TEXT DEFAULT 'daily',
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (date('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS timetable_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id  INTEGER NOT NULL,
            date      TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            UNIQUE(entry_id, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            target_date TEXT NOT NULL DEFAULT '',
            progress    INTEGER NOT NULL DEFAULT 0,
            color       TEXT NOT NULL DEFAULT 'var(--blue)',
            sort_order  INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def seed_defaults():
    """Seed habits/reminders on first run. Password hash always ensured."""
    from config import DEFAULT_HABITS, DEFAULT_REMINDERS

    conn = get_connection()
    c = conn.cursor()

    # Always ensure password hash exists
    c.execute("SELECT value FROM settings WHERE key='override_password_hash'")
    if not c.fetchone():
        from config import DEFAULT_OVERRIDE_PASSWORD
        pw_hash = hashlib.sha256(DEFAULT_OVERRIDE_PASSWORD.encode()).hexdigest()
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("override_password_hash", pw_hash))
        conn.commit()

    # Seed milestones if table is empty
    c.execute("SELECT COUNT(*) FROM milestones")
    if c.fetchone()[0] == 0:
        default_milestones = [
            ("Exams Done",               "May 28, 2026",    90, "var(--gold)",   1),
            ("Portfolio + Suhas Call",   "June 1, 2026",    20, "var(--blue)",   2),
            ("Syrma Internship Start",   "June 1, 2026",    10, "var(--purple)", 3),
            ("First International Client","August 2026",     5, "var(--green)",  4),
            ("Move Out — Own Space",     "Early 2027",       3, "var(--orange)", 5),
            ("Bali Trip",                "December 2026",    2, "var(--gold)",   6),
        ]
        for m in default_milestones:
            c.execute("INSERT INTO milestones (title, target_date, progress, color, sort_order) VALUES (?,?,?,?,?)", m)
        conn.commit()

    # Only seed habits/reminders if table is empty
    c.execute("SELECT COUNT(*) FROM habits")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    for h in DEFAULT_HABITS:
        c.execute("INSERT INTO habits (name, category) VALUES (?, ?)", (h["name"], h["category"]))
    for r in DEFAULT_REMINDERS:
        c.execute("INSERT INTO reminders (time, message, days) VALUES (?, ?, ?)",
                  (r["time"], r["message"], r["days"]))

    conn.commit()
    conn.close()
    print("[OK] Default habits and reminders loaded.")


def backup_database() -> str:
    """Local SQLite backup. Returns path. No-op on Supabase (use Supabase dashboard)."""
    if DATABASE_URL:
        return "Supabase: use the Supabase dashboard for backups."
    import shutil
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.replace(".db", f"_backup_{stamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def get_setting(key: str, default=None):
    conn = get_connection()
    row  = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()
    seed_defaults()
    src = "Supabase" if DATABASE_URL else DB_PATH
    print(f"Database ready: {src}")
