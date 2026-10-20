from datetime import datetime, timedelta, timezone

import pytest

from app import auth, db, security
from app.auth import InvalidCredentials, LockedOut, UserExists, UserNotFound
from tests.conftest import utc

PASSWORD = "correct horse battery"
NOW = utc(2026, 10, 20, 20, 0)


def test_hash_roundtrip_and_unique_salts():
    first = security.hash_password(PASSWORD)
    second = security.hash_password(PASSWORD)
    assert first != second
    assert security.verify_password(PASSWORD, first)
    assert not security.verify_password("wrong password", first)


@pytest.mark.parametrize("stored", ["", "!", "scrypt$bad", "md5$1$2$3$4$5"])
def test_malformed_hashes_never_verify(stored):
    assert security.verify_password(PASSWORD, stored) is False


def test_password_strength_rules():
    security.validate_new_password("x" * security.MIN_PASSWORD_LENGTH)
    with pytest.raises(security.WeakPassword):
        security.validate_new_password("short")
    with pytest.raises(security.WeakPassword):
        security.validate_new_password("x" * (security.MAX_PASSWORD_LENGTH + 1))


def test_tokens_are_random_and_stored_hashed():
    assert security.new_token() != security.new_token()
    assert security.hash_token("abc") == security.hash_token("abc")
    assert security.hash_token("abc") != "abc"


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    db.migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def user(conn):
    auth.create_user(conn, "alice", PASSWORD)
    return "alice"


def test_create_user_allows_only_one_real_user(conn, user):
    with pytest.raises(UserExists):
        auth.create_user(conn, "bob", PASSWORD)


def test_create_user_adopts_the_placeholder_user(conn):
    conn.execute("INSERT INTO users (name, password_hash) VALUES ('owner', '!')")
    conn.commit()
    user_id = auth.create_user(conn, "alice", PASSWORD)
    rows = conn.execute("SELECT id, name FROM users").fetchall()
    assert [(r["id"], r["name"]) for r in rows] == [(user_id, "alice")]


def test_placeholder_user_can_never_log_in(conn):
    conn.execute("INSERT INTO users (name, password_hash) VALUES ('owner', '!')")
    conn.commit()
    with pytest.raises(InvalidCredentials):
        auth.login(conn, "owner", "!", NOW)


def test_login_success_creates_a_resolvable_session(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    assert auth.resolve_session(conn, token, NOW) is not None
    stored = conn.execute("SELECT token_hash FROM sessions").fetchone()["token_hash"]
    assert stored != token


def test_wrong_password_and_unknown_user_look_the_same(conn, user):
    with pytest.raises(InvalidCredentials) as wrong:
        auth.login(conn, user, "wrong password!", NOW)
    with pytest.raises(InvalidCredentials) as unknown:
        auth.login(conn, "nobody", PASSWORD, NOW)
    assert str(wrong.value) == str(unknown.value)


def test_unknown_session_token_is_rejected(conn, user):
    assert auth.resolve_session(conn, "not-a-token", NOW) is None


def test_session_expires_after_thirty_idle_days(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    assert auth.resolve_session(conn, token, NOW + timedelta(days=29)) is not None
    token = auth.login(conn, user, PASSWORD, NOW)
    assert auth.resolve_session(conn, token, NOW + auth.SESSION_LIFETIME) is None
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE token_hash = ?",
                        (security.hash_token(token),)).fetchone()[0] == 0


def test_session_renews_on_use(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    later = NOW + timedelta(days=20)
    assert auth.resolve_session(conn, token, later) is not None
    assert auth.resolve_session(conn, token, later + timedelta(days=29)) is not None


def test_logout_removes_the_session(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    auth.logout(conn, token)
    assert auth.resolve_session(conn, token, NOW) is None


def test_purge_removes_only_expired_sessions(conn, user):
    old = auth.login(conn, user, PASSWORD, NOW - timedelta(days=40))
    fresh = auth.login(conn, user, PASSWORD, NOW)
    assert auth.purge_expired_sessions(conn, NOW) == 1
    assert auth.resolve_session(conn, old, NOW) is None
    assert auth.resolve_session(conn, fresh, NOW) is not None


def fail_times(conn, count):
    for _ in range(count):
        with pytest.raises((InvalidCredentials, LockedOut)):
            auth.login(conn, "alice", "wrong password!", NOW)


def test_lockout_after_five_failures_even_with_the_right_password(conn, user):
    fail_times(conn, 4)
    with pytest.raises(LockedOut) as locked:
        auth.login(conn, user, "wrong password!", NOW)
    assert locked.value.retry_after == 15 * 60
    with pytest.raises(LockedOut):
        auth.login(conn, user, PASSWORD, NOW + timedelta(minutes=14, seconds=59))


def test_lockout_ends_after_fifteen_minutes(conn, user):
    fail_times(conn, 5)
    assert auth.login(conn, user, PASSWORD, NOW + timedelta(minutes=15))


def test_successful_login_resets_the_failure_counter(conn, user):
    fail_times(conn, 4)
    auth.login(conn, user, PASSWORD, NOW)
    fail_times(conn, 4)
    assert auth.login(conn, user, PASSWORD, NOW)


def test_reset_password_unlocks_and_closes_sessions(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    fail_times(conn, 5)
    auth.reset_password(conn, None, "a brand new password")
    assert auth.resolve_session(conn, token, NOW) is None
    assert auth.login(conn, user, "a brand new password", NOW)
    with pytest.raises(InvalidCredentials):
        auth.login(conn, user, PASSWORD, NOW)


def test_reset_password_needs_a_known_user(conn, user):
    with pytest.raises(UserNotFound):
        auth.reset_password(conn, "nobody", PASSWORD)


def test_change_password_keeps_current_session_only(conn, user):
    current = auth.login(conn, user, PASSWORD, NOW)
    other = auth.login(conn, user, PASSWORD, NOW)
    user_id = auth.resolve_session(conn, current, NOW)
    auth.change_password(conn, user_id, PASSWORD, "another long password", current, NOW)
    assert auth.resolve_session(conn, current, NOW) == user_id
    assert auth.resolve_session(conn, other, NOW) is None
    with pytest.raises(InvalidCredentials):
        auth.login(conn, user, PASSWORD, NOW)


def test_change_password_requires_the_current_one(conn, user):
    token = auth.login(conn, user, PASSWORD, NOW)
    user_id = auth.resolve_session(conn, token, NOW)
    with pytest.raises(InvalidCredentials):
        auth.change_password(conn, user_id, "not the password", "another long password", token, NOW)
