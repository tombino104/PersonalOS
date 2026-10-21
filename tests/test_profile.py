from datetime import timedelta

from tests.test_backup import BACKUPS, CONFIRMED
from tests.test_reset import RESET
from tests.test_setup import payload, read_code

PROFILE = "/api/v1/profile"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


def test_a_new_profile_is_empty(client):
    assert client.get(PROFILE).json() == {
        "display_name": None,
        "about": None,
        "birth_year": None,
        "has_photo": False,
        "version": None,
    }
    assert client.get(f"{PROFILE}/photo").status_code == 404


def test_the_details_are_saved_trimmed_and_cleared(client):
    saved = client.put(PROFILE, json={"display_name": "  Sam  ", "about": "Likes quiet mornings", "birth_year": 1999})
    assert saved.status_code == 200
    body = saved.json()
    assert (body["display_name"], body["about"], body["birth_year"]) == ("Sam", "Likes quiet mornings", 1999)
    assert body["version"]
    cleared = client.put(PROFILE, json={"about": "", "birth_year": None}).json()
    assert (cleared["display_name"], cleared["about"], cleared["birth_year"]) == ("Sam", None, None)


def test_invalid_details_are_refused(client):
    assert client.put(PROFILE, json={"birth_year": 1800}).status_code == 422
    assert client.put(PROFILE, json={"display_name": "x" * 61}).status_code == 422
    assert client.put(PROFILE, json={"about": "x" * 501}).status_code == 422
    assert client.put(PROFILE, json={"nickname": "no"}).status_code == 422


def test_a_photo_is_stored_and_served_with_its_type(client):
    for content, kind in ((PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")):
        assert client.put(f"{PROFILE}/photo", content=content).json()["has_photo"] is True
        served = client.get(f"{PROFILE}/photo")
        assert (served.status_code, served.headers["content-type"], served.content) == (200, kind, content)
        assert "private" in served.headers["cache-control"]


def test_the_photo_version_changes_so_browsers_reload_it(client, clock):
    first = client.put(f"{PROFILE}/photo", content=PNG).json()["version"]
    clock.now = clock.now + timedelta(seconds=5)
    second = client.put(f"{PROFILE}/photo", content=JPEG).json()["version"]
    assert first != second


def test_the_photo_can_be_removed(client):
    client.put(f"{PROFILE}/photo", content=PNG)
    assert client.delete(f"{PROFILE}/photo").json()["has_photo"] is False
    assert client.get(f"{PROFILE}/photo").status_code == 404


def test_only_real_images_within_the_size_limit_are_accepted(client, monkeypatch):
    for content in (b"", b"just text", b"GIF89a" + b"\x00" * 20):
        response = client.put(f"{PROFILE}/photo", content=content)
        assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_photo")
    monkeypatch.setattr("app.profile.MAX_PHOTO_BYTES", 32)
    big = client.put(f"{PROFILE}/photo", content=PNG)
    assert (big.status_code, big.json()["error"]["code"]) == (413, "too_large")


def test_the_profile_travels_with_a_backup_and_is_wiped_by_a_reset(client, tmp_path):
    client.put(PROFILE, json={"display_name": "Sam"})
    client.put(f"{PROFILE}/photo", content=PNG)
    stored = client.post(BACKUPS).json()
    client.put(PROFILE, json={"display_name": "Changed"})
    client.delete(f"{PROFILE}/photo")
    assert client.post(f"{BACKUPS}/{stored['name']}/restore", params=CONFIRMED).status_code == 200
    restored = client.get(PROFILE).json()
    assert (restored["display_name"], restored["has_photo"]) == ("Sam", True)
    assert client.get(f"{PROFILE}/photo").content == PNG
    assert client.post(RESET, json=payload(read_code(tmp_path))).status_code == 200
    assert client.get(PROFILE).json()["display_name"] is None
