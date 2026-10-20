import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def site(tmp_path, monkeypatch):
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<html>personal-os</html>", encoding="utf-8")
    (web / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("top secret", encoding="utf-8")
    monkeypatch.setenv("WEB_DIR", str(web))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with TestClient(app) as client:
        yield client


def test_root_serves_the_interface(site):
    response = site.get("/")
    assert response.status_code == 200
    assert "personal-os" in response.text
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/archive", "/questionnaire/done", "/settings"])
def test_unknown_paths_fall_back_to_the_interface(site, path):
    response = site.get(path)
    assert response.status_code == 200
    assert "personal-os" in response.text


def test_assets_are_cached_for_a_long_time(site):
    response = site.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log(1)"
    assert "immutable" in response.headers["cache-control"]


def test_unknown_api_paths_stay_json_404s(site):
    response = site.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert site.get("/api").status_code == 404


def test_health_still_works_next_to_the_interface(site):
    assert site.get("/health").json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/assets/%2e%2e/secret.txt", "/%2e%2e/secret.txt", "/assets/..%2fsecret.txt"])
def test_files_outside_the_web_folder_are_never_served(site, path):
    response = site.get(path)
    assert "top secret" not in response.text


def test_missing_build_gives_a_clear_404(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_DIR", str(tmp_path / "missing"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 404
    assert "not built" in response.json()["error"]["message"]


def test_security_headers_are_on_every_response(site):
    for path in ("/", "/health", "/api/v1/areas", "/assets/app.js"):
        headers = site.get(path).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"
        assert "default-src 'self'" in headers["content-security-policy"]
