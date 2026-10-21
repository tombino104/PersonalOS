import hmac
import logging
import math
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from . import auth, config

logger = logging.getLogger("uvicorn.error")

CODE_FILE = "setup-code.txt"
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)

_lock = threading.Lock()
_failures: dict = {"count": 0, "locked_until": None}


class SetupDone(Exception):
    pass


class InvalidSetupCode(Exception):
    pass


def code_path() -> Path:
    return config.data_dir() / CODE_FILE


def _normalize(value: str) -> str:
    return "".join(char for char in value.upper() if char.isalnum())


def _display(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def _reset_failures() -> None:
    _failures["count"] = 0
    _failures["locked_until"] = None


def _write_new_code() -> str:
    code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
    code_path().write_text(f"{_display(code)}\n", encoding="utf-8")
    return code


def ensure_code(conn: sqlite3.Connection) -> None:
    with _lock:
        _reset_failures()
        code = _write_new_code()
    if auth.setup_required(conn):
        logger.warning("No account yet. Setup code: %s (also saved in %s)", _display(code), code_path())
    else:
        logger.info("A setup code for resetting the app is saved in %s", code_path())


def verify(candidate: str, now: datetime) -> None:
    with _lock:
        locked_until = _failures["locked_until"]
        if locked_until is not None and locked_until > now:
            raise auth.LockedOut(math.ceil((locked_until - now).total_seconds()))
        try:
            expected = _normalize(code_path().read_text(encoding="utf-8"))
        except FileNotFoundError:
            expected = ""
        if expected and hmac.compare_digest(_normalize(candidate), expected):
            _reset_failures()
            return
        _failures["count"] += 1
        if _failures["count"] >= MAX_FAILED_ATTEMPTS:
            _failures["count"] = 0
            _failures["locked_until"] = now + LOCKOUT
            raise auth.LockedOut(int(LOCKOUT.total_seconds()))
        raise InvalidSetupCode("invalid setup code")


def finish() -> None:
    with _lock:
        _write_new_code()
