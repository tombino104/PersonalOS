import csv
import io
import json
import sqlite3
import zipfile

from app import config
from tests.conftest import utc

EXPORT = "/api/v1/export"
DAY = "2026-10-20"


def open_zip(client):
    response = client.get(EXPORT)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    return response, zipfile.ZipFile(io.BytesIO(response.content))


def rows(archive, name):
    text = archive.read(name).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def record_a_day(client, clock):
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/reports", json={"day": DAY})
    first = client.get(f"/api/v1/reports/{DAY}").json()["completions"][0]
    client.put(f"/api/v1/reports/{DAY}/completions/{first['activity_id']}", json={"done": True})
    client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "A good line"})
    client.post(f"/api/v1/reports/{DAY}/complete")
    return first


def test_the_export_is_a_zip_with_every_file(client, clock):
    clock.now = utc(2026, 10, 20, 20, 0)
    response, archive = open_zip(client)
    assert response.headers["content-disposition"] == 'attachment; filename="personal-os-export-20261020.zip"'
    assert {"README.txt", "activities.csv", "reports.csv", "completions.csv", "scores.csv", "weekly_notes.csv", "data.json"} <= set(
        archive.namelist()
    )


def test_it_holds_what_was_recorded(client, clock):
    first = record_a_day(client, clock)
    _, archive = open_zip(client)
    activities = rows(archive, "activities.csv")
    assert len(activities) >= 10 and {"area", "name", "weight", "days", "times_per_week"} <= set(activities[0])
    assert rows(archive, "reports.csv") == [{"day": DAY, "completed_at": rows(archive, "reports.csv")[0]["completed_at"], "reflection": "A good line"}]
    done = [item for item in rows(archive, "completions.csv") if item["done"] == "1"]
    assert [item["activity"] for item in done] == [first["name"]]
    scores = rows(archive, "scores.csv")
    assert len(scores) == 6
    empty = [item for item in scores if item["maximum"] == "0"]
    assert all(item["score"] == "" for item in empty)
    data = json.loads(archive.read("data.json"))
    assert data["exported_at"].startswith("2026-10-20")
    assert data["reports"][0]["reflection"] == "A good line"
    assert data["settings"]["timezone"] == "Europe/Rome"


def test_nothing_that_protects_the_app_is_in_it(client, clock):
    record_a_day(client, clock)
    conn = sqlite3.connect(config.db_path())
    secrets = [row[0] for row in conn.execute("SELECT password_hash FROM users")]
    conn.close()
    assert secrets and all(secrets)
    _, archive = open_zip(client)
    for name in archive.namelist():
        content = archive.read(name).decode("utf-8", errors="ignore")
        assert not any(secret in content for secret in secrets)
        assert "password" not in content.lower().replace("no password", "")
    assert not any("session" in name or "user" in name for name in archive.namelist())


def test_a_deleted_activity_is_left_out_but_its_history_stays(client, clock):
    first = record_a_day(client, clock)
    client.patch(f"/api/v1/activities/{first['activity_id']}", json={"archived": True})
    client.delete(f"/api/v1/activities/{first['activity_id']}")
    _, archive = open_zip(client)
    assert first["name"] not in [item["name"] for item in rows(archive, "activities.csv")]
    assert first["name"] in [item["activity"] for item in rows(archive, "completions.csv")]


def test_text_that_looks_like_a_formula_is_defused(client, clock):
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/activities", json={"area": "career", "name": "=HYPERLINK(\"x\")", "weight": 1})
    client.post("/api/v1/reports", json={"day": DAY})
    client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "+1 idea"})
    client.post(f"/api/v1/reports/{DAY}/complete")
    _, archive = open_zip(client)
    assert any(item["name"] == "'=HYPERLINK(\"x\")" for item in rows(archive, "activities.csv"))
    assert rows(archive, "reports.csv")[0]["reflection"] == "'+1 idea"
    assert json.loads(archive.read("data.json"))["reports"][0]["reflection"] == "+1 idea"


def test_weekly_notes_are_included(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    client.put("/api/v1/reviews/2026-10-19/note", json={"text": "Keep the mornings"})
    _, archive = open_zip(client)
    assert [item["note"] for item in rows(archive, "weekly_notes.csv")] == ["Keep the mornings"]


def test_plugin_tables_are_exported_and_the_journal_becomes_markdown(client, clock):
    conn = sqlite3.connect(config.db_path())
    conn.execute("CREATE TABLE plg_journal_entries (id INTEGER PRIMARY KEY, day TEXT, title TEXT, body TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("INSERT INTO plg_journal_entries VALUES (1, '2026-10-19', 'Monday', 'First line.\n\nSecond.', 'a', 'a')")
    conn.execute("INSERT INTO plg_journal_entries VALUES (2, '2026-10-18', NULL, 'Untitled.', 'a', 'a')")
    conn.execute("CREATE TABLE plg_empty_things (id INTEGER PRIMARY KEY, note TEXT)")
    conn.commit()
    conn.close()
    _, archive = open_zip(client)
    assert "plugins/plg_journal_entries.csv" in archive.namelist()
    assert archive.read("plugins/plg_empty_things.csv").decode("utf-8-sig").strip() == "id,note"
    markdown = archive.read("journal.md").decode("utf-8")
    assert markdown.index("## 2026-10-18") < markdown.index("## 2026-10-19 — Monday")
    assert "First line.\n\nSecond." in markdown
    assert json.loads(archive.read("data.json"))["plugins"]["plg_journal_entries"][0]["id"] == 1
