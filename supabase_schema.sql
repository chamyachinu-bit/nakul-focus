-- supabase_schema.sql
-- Run this once in the Supabase SQL editor (Dashboard > SQL Editor > New query)
-- Safe to re-run: all statements use IF NOT EXISTS

CREATE TABLE IF NOT EXISTS habits (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT DEFAULT 'general',
    active     INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id        BIGSERIAL PRIMARY KEY,
    habit_id  INTEGER NOT NULL,
    date      TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    notes     TEXT,
    UNIQUE(habit_id, date)
);

CREATE TABLE IF NOT EXISTS focus_sessions (
    id            BIGSERIAL PRIMARY KEY,
    duration_mins INTEGER NOT NULL,
    mode          TEXT DEFAULT 'pomodoro',
    completed     INTEGER DEFAULT 0,
    project       TEXT,
    date          TEXT DEFAULT CURRENT_DATE,
    start_time    TEXT,
    end_time      TEXT
);

CREATE TABLE IF NOT EXISTS work_sessions (
    id            BIGSERIAL PRIMARY KEY,
    project       TEXT NOT NULL,
    duration_mins INTEGER NOT NULL,
    work_type     TEXT DEFAULT 'freelance',
    income        DOUBLE PRECISION DEFAULT 0,
    notes         TEXT,
    date          TEXT DEFAULT CURRENT_DATE,
    start_time    TEXT
);

CREATE TABLE IF NOT EXISTS weight_logs (
    id        BIGSERIAL PRIMARY KEY,
    weight_kg DOUBLE PRECISION NOT NULL,
    date      TEXT DEFAULT CURRENT_DATE,
    notes     TEXT
);

CREATE TABLE IF NOT EXISTS mood_logs (
    id         BIGSERIAL PRIMARY KEY,
    mood_score INTEGER NOT NULL,
    mood_label TEXT,
    date       TEXT DEFAULT CURRENT_DATE,
    time       TEXT,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
    id      BIGSERIAL PRIMARY KEY,
    time    TEXT NOT NULL,
    message TEXT NOT NULL,
    active  INTEGER DEFAULT 1,
    days    TEXT DEFAULT 'daily'
);

CREATE TABLE IF NOT EXISTS bali_fund (
    id         BIGSERIAL PRIMARY KEY,
    amount     DOUBLE PRECISION NOT NULL,
    entry_type TEXT DEFAULT 'deposit',
    date       TEXT DEFAULT CURRENT_DATE,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id         BIGSERIAL PRIMARY KEY,
    time_start TEXT NOT NULL,
    time_end   TEXT,
    name       TEXT NOT NULL,
    category   TEXT DEFAULT 'work',
    note       TEXT DEFAULT '',
    days       TEXT DEFAULT 'daily',
    active     INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id         BIGSERIAL PRIMARY KEY,
    date       TEXT DEFAULT CURRENT_DATE,
    created_at TEXT,
    gratitude1 TEXT DEFAULT '',
    gratitude2 TEXT DEFAULT '',
    gratitude3 TEXT DEFAULT '',
    entry      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS timetable_logs (
    id       BIGSERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    date     TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    UNIQUE(entry_id, date)
);

CREATE TABLE IF NOT EXISTS milestones (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    target_date TEXT NOT NULL DEFAULT '',
    progress    INTEGER NOT NULL DEFAULT 0,
    color       TEXT NOT NULL DEFAULT 'var(--blue)',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id         BIGSERIAL PRIMARY KEY,
    text       TEXT NOT NULL,
    category   TEXT DEFAULT 'work',
    deadline   TEXT DEFAULT '',
    priority   TEXT DEFAULT 'mid',
    done       INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_DATE,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS goals (
    id         BIGSERIAL PRIMARY KEY,
    text       TEXT NOT NULL,
    type       TEXT DEFAULT '6month',
    target     TEXT DEFAULT '',
    progress   INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    amount      DOUBLE PRECISION NOT NULL,
    type        TEXT DEFAULT 'expense',
    date        TEXT DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS water_logs (
    id   BIGSERIAL PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    cups INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meal_logs (
    id        BIGSERIAL PRIMARY KEY,
    date      TEXT NOT NULL UNIQUE,
    breakfast TEXT DEFAULT '',
    lunch     TEXT DEFAULT '',
    dinner    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS seva_logs (
    id          BIGSERIAL PRIMARY KEY,
    date        TEXT DEFAULT CURRENT_DATE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS divine_logs (
    id         BIGSERIAL PRIMARY KEY,
    date       TEXT NOT NULL UNIQUE,
    attachment TEXT DEFAULT '',
    social     TEXT DEFAULT '',
    peace      TEXT DEFAULT '',
    reflection TEXT DEFAULT ''
);
