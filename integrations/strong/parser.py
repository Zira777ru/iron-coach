"""Parse Strong app CSV/XML export files."""
import csv
import io
import json
from datetime import datetime


def parse_strong_csv(content: str) -> list[dict]:
    """
    Parse Strong app CSV export.
    Returns list of workout dicts: {date, name, duration_min, exercises, notes}
    """
    workouts: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(content), delimiter=";")

    for row in reader:
        date_str = row.get("Date", "").strip()
        workout_name = row.get("Workout Name", "").strip()
        exercise_name = row.get("Exercise Name", "").strip()
        set_order = row.get("Set Order", "")
        weight = row.get("Weight", "0") or "0"
        reps = row.get("Reps", "0") or "0"
        duration = row.get("Duration", "0") or "0"
        notes = row.get("Notes", "").strip()

        if not date_str:
            continue

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            workout_date = dt.date().isoformat()
            key = f"{workout_date}_{workout_name}"
        except ValueError:
            continue

        if key not in workouts:
            workouts[key] = {
                "workout_date": workout_date,
                "name": workout_name,
                "duration_min": int(float(duration)) if duration != "0" else 60,
                "exercises": {},
                "notes": notes,
            }

        if exercise_name:
            if exercise_name not in workouts[key]["exercises"]:
                workouts[key]["exercises"][exercise_name] = []
            workouts[key]["exercises"][exercise_name].append({
                "set": set_order,
                "weight_kg": float(weight.replace(",", ".")),
                "reps": int(float(reps)) if reps else 0,
            })

    result = []
    for w in workouts.values():
        exercises_list = [
            {"name": ex_name, "sets": sets}
            for ex_name, sets in w["exercises"].items()
        ]
        result.append({
            "workout_date": w["workout_date"],
            "name": w["name"],
            "duration_min": w["duration_min"],
            "exercises": exercises_list,
            "notes": w["notes"],
        })

    return sorted(result, key=lambda x: x["workout_date"], reverse=True)


def workout_summary(workout: dict) -> str:
    lines = [f"🏋️ *{workout['name']}* — {workout['workout_date']}"]
    lines.append(f"⏱ {workout['duration_min']} мин")
    for ex in workout["exercises"]:
        sets_str = ", ".join(
            f"{s['reps']}×{s['weight_kg']:.1f}кг" for s in ex["sets"]
        )
        lines.append(f"  • {ex['name']}: {sets_str}")
    if workout.get("notes"):
        lines.append(f"📝 {workout['notes']}")
    return "\n".join(lines)
