CREATE_TABLES = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    tg_id       INTEGER PRIMARY KEY,
    name        TEXT,
    age         INTEGER,
    weight_kg   REAL,
    height_cm   REAL,
    goal        TEXT,          -- lose_weight / gain_muscle / maintain
    activity    TEXT,          -- sedentary / light / moderate / active
    fitbit_token TEXT,         -- JSON OAuth token
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workouts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    source      TEXT NOT NULL,  -- strong / manual / fitbit
    workout_date TEXT NOT NULL, -- ISO date
    name        TEXT,
    duration_min INTEGER,
    exercises   TEXT,           -- JSON list of {name, sets:[{reps,weight}]}
    notes       TEXT,
    raw_data    TEXT,           -- original file content
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS food_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    log_date    TEXT NOT NULL,
    meal_type   TEXT,           -- breakfast / lunch / dinner / snack
    description TEXT,
    calories    REAL,
    protein_g   REAL,
    carbs_g     REAL,
    fat_g       REAL,
    source      TEXT,           -- photo / fatsecret_screenshot / manual
    ai_analysis TEXT,           -- raw AI response
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fitbit_daily (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    date        TEXT NOT NULL,
    steps       INTEGER,
    calories_out INTEGER,
    active_minutes INTEGER,
    sleep_min   INTEGER,
    resting_hr  INTEGER,
    weight_kg   REAL,
    UNIQUE(tg_id, date)
);

CREATE TABLE IF NOT EXISTS coach_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    msg_type    TEXT NOT NULL,  -- motivation / warning / praise / daily_steps / weekly_review
    content     TEXT,
    sent_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS meta (
    key         TEXT PRIMARY KEY,
    value       TEXT
);
"""
