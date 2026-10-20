from fastapi.testclient import TestClient

from app import __version__
from app.main import app


def test_health_reports_ok_and_creates_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "database": True}
    assert (tmp_path / "personal_os.db").exists()


def test_unknown_route_is_404_without_a_web_build(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WEB_DIR", str(tmp_path / "missing"))
    with TestClient(app) as client:
        assert client.get("/nope").status_code == 404
