import shutil
from pathlib import Path

import pytest

from tests.plugin_site import Site, activate, plugin_state

SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "quotes"


@pytest.fixture
def quotes(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "quotes")
    with site.running() as client:
        yield client


def test_it_is_off_until_the_user_turns_it_on(quotes):
    item = plugin_state(quotes, "quotes")
    assert item["state"] == "inactive"
    assert item["default_active"] is False
    assert item["permissions"] == ["ui_panel"]
    assert item["widgets"] == ["daily"]
    assert item["entries"] == []


def test_it_turns_on_without_a_backend_and_adds_no_tables(quotes):
    assert activate(quotes, "quotes").status_code == 200
    assert plugin_state(quotes, "quotes")["state"] == "active"
    assert quotes.post("/api/v1/plugins/quotes/deactivate").status_code == 200
    assert plugin_state(quotes, "quotes")["state"] == "inactive"
