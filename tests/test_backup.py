import io
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from app import backup, db, settings
from tests.conftest import EVENING
from tests.test_setup import read_code

BACKUPS = "/api/v1/backups"
CONFIRMED = {"confirm": "restore"}


def query(tmp_path, sql, params=()):
    conn = db.connect(tmp_path / "personal_os.db")
    try:
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def add_activity(client, name):
    created = client.post("/api/v1/activities", json={"area": "mindset", "name": name, "weight": 2})
    assert created.status_code == 201


def activity_names(tmp_path):
    return {row["name"] for row in query(tmp_path, "SELECT name FROM activities")}


def download(client, name):
    response = client.get(f"{BACKUPS}/{name}")
    assert response.status_code == 200
    return response.content


def database_of(archive_bytes, target):
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        target.write_bytes(archive.read("personal_os.db"))
    return target


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_a_backup_is_a_zip_with_the_database_and_a_manifest(client, tmp_path):
    add_activity(client, "Kept habit")
    created = client.post(BACKUPS)
    assert created.status_code == 201
    item = created.json()
    assert item["kind"] == "manual"
    assert item["name"] == "personal-os-manual-20261020-200000.zip"
    content = download(client, item["name"])
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert sorted(archive.namelist()) == ["manifest.json", "personal_os.db"]
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["kind"] == "manual"
    assert manifest["migrations"]
    copy = database_of(content, tmp_path / "copy.db")
    names = {row[0] for row in sqlite3.connect(copy).execute("SELECT name FROM activities")}
    assert "Kept habit" in names


def test_the_setup_code_is_never_part_of_a_backup(client):
    item = client.post(BACKUPS).json()
    with zipfile.ZipFile(io.BytesIO(download(client, item["name"]))) as archive:
        assert "setup-code.txt" not in archive.namelist()


def test_backups_are_listed_newest_first(client, clock):
    first = client.post(BACKUPS).json()
    clock.now = EVENING + timedelta(minutes=5)
    second = client.post(BACKUPS).json()
    listing = client.get(BACKUPS).json()
    assert [item["name"] for item in listing["backups"]] == [second["name"], first["name"]]
    assert listing["keep"] == {"auto": 7, "manual": 20, "before-restore": 5}


def test_old_automatic_backups_are_pruned_to_seven(client, tmp_path):
    for day in range(10):
        backup.create("auto", EVENING + timedelta(days=day))
    names = [item["name"] for item in backup.list_backups() if item["kind"] == "auto"]
    assert len(names) == 7
    assert names[0].endswith("20261029-200000.zip")
    assert not (tmp_path / "backups" / "personal-os-auto-20261020-200000.zip").exists()


def test_pruning_one_kind_does_not_touch_the_others(client):
    backup.create("manual", EVENING)
    for day in range(9):
        backup.create("auto", EVENING + timedelta(days=day))
    assert len([item for item in backup.list_backups() if item["kind"] == "manual"]) == 1


def local_moment(conn, day, hour, minute=0):
    zone = settings.day_rules(conn).zone
    return datetime(2026, 10, day, hour, minute, tzinfo=zone).astimezone(timezone.utc)


def test_the_scheduled_backup_runs_once_per_scheduled_moment(client, tmp_path):
    conn = db.connect(tmp_path / "personal_os.db")
    first = backup.run_scheduled(conn, local_moment(conn, 21, 3, 5))
    assert first is not None and first["kind"] == "auto"
    assert backup.run_scheduled(conn, local_moment(conn, 21, 15)) is None
    assert backup.run_scheduled(conn, local_moment(conn, 22, 2, 30)) is None
    assert backup.run_scheduled(conn, local_moment(conn, 22, 3, 1)) is not None
    conn.close()


def test_a_backup_missed_while_the_device_was_off_is_made_when_it_is_back(client, tmp_path):
    conn = db.connect(tmp_path / "personal_os.db")
    assert backup.run_scheduled(conn, local_moment(conn, 21, 3, 5)) is not None
    assert backup.run_scheduled(conn, local_moment(conn, 23, 10)) is not None
    assert backup.run_scheduled(conn, local_moment(conn, 23, 11)) is None
    conn.close()


def test_the_user_chooses_the_time_and_can_turn_it_off(client, tmp_path):
    assert client.patch("/api/v1/settings", json={"backup_time": "22:30"}).json()["backup_time"] == "22:30"
    conn = db.connect(tmp_path / "personal_os.db")
    assert backup.run_scheduled(conn, local_moment(conn, 21, 22, 40)) is not None
    assert backup.run_scheduled(conn, local_moment(conn, 22, 21, 0)) is None
    assert backup.run_scheduled(conn, local_moment(conn, 22, 22, 31)) is not None
    client.patch("/api/v1/settings", json={"backup_auto": False})
    assert backup.run_scheduled(conn, local_moment(conn, 25, 23, 0)) is None
    conn.close()


def test_a_bad_backup_time_is_refused(client):
    assert client.patch("/api/v1/settings", json={"backup_time": "25:99"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"backup_time": "3am"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"backup_auto": None}).status_code == 422


def test_restoring_a_stored_backup_brings_the_data_back(client, tmp_path, clock):
    add_activity(client, "Before the backup")
    stored = client.post(BACKUPS).json()
    add_activity(client, "After the backup")
    clock.now = EVENING + timedelta(minutes=10)
    result = client.post(f"{BACKUPS}/{stored['name']}/restore", params=CONFIRMED)
    assert result.status_code == 200
    assert result.json()["restored"] is True
    names = activity_names(tmp_path)
    assert "Before the backup" in names and "After the backup" not in names
    safety = result.json()["safety_backup"]
    assert safety["kind"] == "before-restore"
    copy = database_of(download(client, safety["name"]), tmp_path / "safety.db")
    assert "After the backup" in {row[0] for row in sqlite3.connect(copy).execute("SELECT name FROM activities")}


def test_restoring_an_uploaded_file_works_and_renews_the_setup_code(client, tmp_path, clock):
    add_activity(client, "Uploaded state")
    content = download(client, client.post(BACKUPS).json()["name"])
    add_activity(client, "Lost state")
    code = read_code(tmp_path)
    clock.now = EVENING + timedelta(minutes=10)
    result = client.post(f"{BACKUPS}/restore", params=CONFIRMED, content=content)
    assert result.status_code == 200
    names = activity_names(tmp_path)
    assert "Uploaded state" in names and "Lost state" not in names
    assert read_code(tmp_path) != code


def test_a_restore_needs_the_confirmation(client, tmp_path):
    stored = client.post(BACKUPS).json()
    add_activity(client, "Stays")
    for response in (
        client.post(f"{BACKUPS}/{stored['name']}/restore"),
        client.post(f"{BACKUPS}/{stored['name']}/restore", params={"confirm": "yes"}),
        client.post(f"{BACKUPS}/restore", content=b"x"),
    ):
        assert (response.status_code, response.json()["error"]["code"]) == (422, "confirmation_required")
    assert "Stays" in activity_names(tmp_path)


@pytest.mark.parametrize(
    "content",
    [b"not a zip at all", make_zip({"other.txt": b"x"}), make_zip({"personal_os.db": b"garbage"})],
    ids=["not-a-zip", "no-database", "damaged-database"],
)
def test_bad_files_are_refused_and_nothing_changes(client, tmp_path, content):
    add_activity(client, "Safe")
    response = client.post(f"{BACKUPS}/restore", params=CONFIRMED, content=content)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_backup")
    assert "Safe" in activity_names(tmp_path)
    assert not [item for item in backup.list_backups() if item["kind"] == "before-restore"]


def test_a_database_from_another_app_is_refused(client, tmp_path):
    other = tmp_path / "other.db"
    sqlite3.connect(other).executescript("CREATE TABLE notes (id INTEGER);")
    content = make_zip({"personal_os.db": other.read_bytes()})
    response = client.post(f"{BACKUPS}/restore", params=CONFIRMED, content=content)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_backup")


def test_a_backup_from_a_newer_version_is_refused(client, tmp_path):
    stored = client.post(BACKUPS).json()
    work = database_of(download(client, stored["name"]), tmp_path / "future.db")
    conn = sqlite3.connect(work)
    conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES ('9999_future', 'now')")
    conn.commit()
    conn.close()
    response = client.post(
        f"{BACKUPS}/restore", params=CONFIRMED, content=make_zip({"personal_os.db": work.read_bytes()})
    )
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_backup")
    assert "newer version" in response.json()["error"]["message"]


def test_an_oversized_upload_is_refused(client, monkeypatch):
    monkeypatch.setattr(backup, "MAX_UPLOAD_BYTES", 10)
    response = client.post(f"{BACKUPS}/restore", params=CONFIRMED, content=b"x" * 50)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "too_large")


@pytest.mark.parametrize(
    "name",
    [
        "personal-os-manual-20261020-200000.zip",
        "notes.txt",
        "personal-os-x-1.zip",
    ],
)
def test_only_existing_backups_can_be_downloaded_or_restored(client, name):
    assert client.get(f"{BACKUPS}/{name}").status_code == 404
    assert client.post(f"{BACKUPS}/{name}/restore", params=CONFIRMED).status_code == 404


def test_a_path_cannot_escape_the_backup_folder(client):
    assert client.get(f"{BACKUPS}/..%2Fpersonal_os.db").status_code == 404
    assert client.get(f"{BACKUPS}/%2E%2E%2Fpersonal_os.db").status_code == 404


def test_restoring_an_older_database_upgrades_its_schema(client, tmp_path):
    stored = client.post(BACKUPS).json()
    work = database_of(download(client, stored["name"]), tmp_path / "old.db")
    conn = sqlite3.connect(work)
    newest = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    conn.execute("DELETE FROM schema_migrations WHERE version = ?", (newest,))
    conn.execute("DROP TABLE push_subscriptions")
    conn.commit()
    conn.close()
    response = client.post(
        f"{BACKUPS}/restore", params=CONFIRMED, content=make_zip({"personal_os.db": work.read_bytes()})
    )
    assert response.status_code == 200
    assert query(tmp_path, "SELECT COUNT(*) AS d FROM push_subscriptions")[0]["d"] == 0
    assert client.get("/api/v1/plugins").status_code == 200
