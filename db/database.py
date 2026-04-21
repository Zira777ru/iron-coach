import aiosqlite
import json
from config import settings
from db.schema import CREATE_TABLES


_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.db_path)
        _db.row_factory = aiosqlite.Row
        await _db.executescript(CREATE_TABLES)
        await _db.commit()
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def get_user(tg_id: int) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def upsert_user(tg_id: int, **fields):
    db = await get_db()
    existing = await get_user(tg_id)
    if existing:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        await db.execute(f"UPDATE users SET {cols} WHERE tg_id=?", (*fields.values(), tg_id))
    else:
        fields["tg_id"] = tg_id
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        await db.execute(f"INSERT INTO users ({cols}) VALUES ({placeholders})", tuple(fields.values()))
    await db.commit()


async def log_workout(tg_id: int, source: str, workout_date: str, name: str,
                      duration_min: int, exercises: list, notes: str = "", raw_data: str = ""):
    db = await get_db()
    await db.execute(
        """INSERT INTO workouts (tg_id, source, workout_date, name, duration_min, exercises, notes, raw_data)
           VALUES (?,?,?,?,?,?,?,?)""",
        (tg_id, source, workout_date, name, duration_min, json.dumps(exercises, ensure_ascii=False), notes, raw_data)
    )
    await db.commit()


async def get_recent_workouts(tg_id: int, days: int = 7) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM workouts WHERE tg_id=? AND workout_date >= date('now', ?) ORDER BY workout_date DESC",
        (tg_id, f"-{days} days")
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def log_food(tg_id: int, log_date: str, meal_type: str, description: str,
                   calories: float, protein_g: float, carbs_g: float, fat_g: float,
                   source: str, ai_analysis: str = ""):
    db = await get_db()
    await db.execute(
        """INSERT INTO food_logs (tg_id, log_date, meal_type, description, calories, protein_g, carbs_g, fat_g, source, ai_analysis)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (tg_id, log_date, meal_type, description, calories, protein_g, carbs_g, fat_g, source, ai_analysis)
    )
    await db.commit()


async def get_today_food(tg_id: int, date: str) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM food_logs WHERE tg_id=? AND log_date=? ORDER BY created_at",
        (tg_id, date)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def upsert_fitbit_daily(tg_id: int, date: str, **fields):
    db = await get_db()
    fields_str = ", ".join(f"{k}=excluded.{k}" for k in fields)
    cols = "tg_id, date, " + ", ".join(fields.keys())
    placeholders = "?, ?, " + ", ".join("?" for _ in fields)
    await db.execute(
        f"""INSERT INTO fitbit_daily ({cols}) VALUES ({placeholders})
            ON CONFLICT(tg_id, date) DO UPDATE SET {fields_str}""",
        (tg_id, date, *fields.values())
    )
    await db.commit()


async def get_fitbit_today(tg_id: int, date: str) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT * FROM fitbit_daily WHERE tg_id=? AND date=?", (tg_id, date)) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def save_coach_message(tg_id: int, msg_type: str, content: str):
    db = await get_db()
    await db.execute(
        "INSERT INTO coach_messages (tg_id, msg_type, content) VALUES (?,?,?)",
        (tg_id, msg_type, content)
    )
    await db.commit()
