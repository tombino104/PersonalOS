import io

import pytest

from app import auth, cli, db
from tests.conftest import utc

PASSWORD = "correct horse battery"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path


def run(monkeypatch, args, password):
    monkeypatch.setattr("sys.stdin", io.StringIO(password + "\n"))
    return cli.main([*args, "--password-stdin"])


def open_db(data_dir):
    return db.connect(data_dir / "personal_os.db")


def test_create_user_then_login_works(data_dir, monkeypatch):
    assert run(monkeypatch, ["create-user", "--name", "alice"], PASSWORD) == 0
    conn = open_db(data_dir)
    assert auth.login(conn, "alice", PASSWORD, utc(2026, 10, 20, 20, 0))
    conn.close()


def test_second_user_is_refused(data_dir, monkeypatch, capsys):
    run(monkeypatch, ["create-user", "--name", "alice"], PASSWORD)
    assert run(monkeypatch, ["create-user", "--name", "bob"], PASSWORD) == 1
    assert "already exists" in capsys.readouterr().err


def test_weak_password_is_refused(data_dir, monkeypatch, capsys):
    assert run(monkeypatch, ["create-user", "--name", "alice"], "short") == 1
    assert "at least" in capsys.readouterr().err


def test_reset_password_unlocks_a_locked_account(data_dir, monkeypatch):
    run(monkeypatch, ["create-user", "--name", "alice"], PASSWORD)
    now = utc(2026, 10, 20, 20, 0)
    conn = open_db(data_dir)
    for _ in range(5):
        with pytest.raises((auth.InvalidCredentials, auth.LockedOut)):
            auth.login(conn, "alice", "wrong password!", now)
    with pytest.raises(auth.LockedOut):
        auth.login(conn, "alice", PASSWORD, now)
    conn.close()

    assert run(monkeypatch, ["reset-password"], "a brand new password") == 0
    conn = open_db(data_dir)
    assert auth.login(conn, "alice", "a brand new password", now)
    conn.close()


def test_reset_password_for_unknown_name_fails(data_dir, monkeypatch, capsys):
    run(monkeypatch, ["create-user", "--name", "alice"], PASSWORD)
    assert run(monkeypatch, ["reset-password", "--name", "nobody"], PASSWORD) == 1
    assert "no user named" in capsys.readouterr().err
