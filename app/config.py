import os
from pathlib import Path


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "./data"))


def db_path() -> Path:
    return data_dir() / "personal_os.db"


def plugins_dir() -> Path:
    configured = os.environ.get("PLUGINS_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "plugins"
