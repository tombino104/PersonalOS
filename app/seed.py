import sqlite3

from . import settings

SAMPLE_ACTIVITIES = {
    "physical": [("Workout", 3), ("Walk or run", 2), ("Regular sleep", 2), ("Balanced meals", 1)],
    "discipline": [("Wake up on time", 2), ("Morning routine", 2), ("Follow the daily plan", 2)],
    "social": [("Small kind gesture", 1), ("Start a conversation", 2), ("Take the initiative", 3)],
    "intellect": [("Reading", 2), ("Follow a course", 3), ("Personal project", 2)],
    "career": [("Planned study or work hours", 3), ("Finish one task today", 2)],
    "mindset": [("Meditation or journaling", 2), ("Handle a stressful moment calmly", 3)],
}


def sample_activities(conn: sqlite3.Connection) -> bool:
    if settings.get(conn, "sample_activities_seeded", False):
        return False
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if count == 0:
        with conn:
            for slug, activities in SAMPLE_ACTIVITIES.items():
                area_id = conn.execute(
                    "SELECT id FROM areas WHERE slug = ?", (slug,)
                ).fetchone()["id"]
                conn.executemany(
                    "INSERT INTO activities (area_id, name, weight) VALUES (?, ?, ?)",
                    [(area_id, name, weight) for name, weight in activities],
                )
    settings.put(conn, "sample_activities_seeded", True)
    return count == 0
