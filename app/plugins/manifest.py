import json
import re
from dataclasses import dataclass
from pathlib import Path

CORE_API_VERSION = "1.0"

PERMISSIONS = frozenset(
    {
        "read_activities",
        "read_reports",
        "read_scores",
        "questionnaire_block",
        "ui_panel",
        "api_routes",
        "listen_events",
        "request_reminder",
    }
)

CORE_EVENTS = frozenset(
    {
        "report.completed",
        "report.modified",
        "report.closed",
        "activity.created",
        "activity.modified",
        "activity.archived",
        "plugin.activated",
        "plugin.deactivated",
    }
)

PLACEMENTS = frozenset({"dock", "more"})
RESERVED_PATHS = frozenset({"activate", "deactivate", "remove-data"})

_ID = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_CORE_API = re.compile(r"^(\d+)\.x$")
_EVENT = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class ManifestError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    id: str
    label: str
    icon: str
    placement: str
    page: str


@dataclass(frozen=True)
class Manifest:
    id: str
    name: str
    version: str
    description: str
    core_api: str
    permissions: frozenset
    questionnaire_blocks: tuple
    report_sections: tuple
    widgets: tuple
    pages: tuple
    entries: tuple
    settings: bool
    listens: tuple
    emits: tuple
    migrations: str | None
    default_active: bool = False

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "core_api": self.core_api,
            "permissions": sorted(self.permissions),
            "questionnaire_blocks": list(self.questionnaire_blocks),
            "report_sections": list(self.report_sections),
            "widgets": list(self.widgets),
            "pages": list(self.pages),
            "entries": [
                {
                    "id": entry.id,
                    "label": entry.label,
                    "icon": entry.icon,
                    "placement": entry.placement,
                    "page": entry.page,
                }
                for entry in self.entries
            ],
            "settings": self.settings,
            "default_active": self.default_active,
        }


def core_compatible(core_api: str) -> bool:
    match = _CORE_API.match(core_api)
    return bool(match) and match.group(1) == CORE_API_VERSION.split(".")[0]


def _text(data: dict, key: str, maximum: int = 200) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ManifestError(f"'{key}' must be a non-empty string of at most {maximum} characters")
    return value.strip()


def _names(values, what: str) -> tuple:
    if not isinstance(values, list) or any(not isinstance(v, str) or not _NAME.match(v) for v in values):
        raise ManifestError(f"'{what}' must be a list of lowercase identifiers")
    if len(set(values)) != len(values):
        raise ManifestError(f"'{what}' has duplicates")
    return tuple(values)


def parse_manifest(data, folder_name: str) -> Manifest:
    if not isinstance(data, dict):
        raise ManifestError("the manifest must be a JSON object")
    plugin_id = _text(data, "id", 32)
    if not _ID.match(plugin_id):
        raise ManifestError("'id' must be lowercase letters, digits and underscores, starting with a letter")
    if plugin_id != folder_name:
        raise ManifestError(f"'id' ({plugin_id}) must match the folder name ({folder_name})")
    version = _text(data, "version", 20)
    if not _VERSION.match(version):
        raise ManifestError("'version' must look like 1.2.3")
    core_api = _text(data, "core_api", 20)
    if not _CORE_API.match(core_api):
        raise ManifestError("'core_api' must look like 1.x")

    permissions = data.get("permissions", [])
    if not isinstance(permissions, list) or any(p not in PERMISSIONS for p in permissions):
        unknown = [p for p in permissions if p not in PERMISSIONS] if isinstance(permissions, list) else []
        raise ManifestError(f"unknown permissions: {', '.join(map(str, unknown)) or 'invalid list'}")
    granted = frozenset(permissions)

    adds = data.get("adds", {})
    if not isinstance(adds, dict):
        raise ManifestError("'adds' must be an object")
    unknown_adds = set(adds) - {
        "questionnaire_blocks",
        "report_sections",
        "widgets",
        "pages",
        "entries",
        "settings",
    }
    if unknown_adds:
        raise ManifestError(f"unknown 'adds' keys: {', '.join(sorted(unknown_adds))}")
    blocks = _names(adds.get("questionnaire_blocks", []), "adds.questionnaire_blocks")
    report_sections = _names(adds.get("report_sections", []), "adds.report_sections")
    widgets = _names(adds.get("widgets", []), "adds.widgets")
    pages = _names(adds.get("pages", []), "adds.pages")
    has_settings = adds.get("settings", False)
    if not isinstance(has_settings, bool):
        raise ManifestError("'adds.settings' must be true or false")
    if blocks and "questionnaire_block" not in granted:
        raise ManifestError("questionnaire blocks need the 'questionnaire_block' permission")
    if (report_sections or widgets or pages or has_settings or adds.get("entries")) and "ui_panel" not in granted:
        raise ManifestError("report sections, widgets, pages, entries and settings need the 'ui_panel' permission")

    entries = []
    raw_entries = adds.get("entries", [])
    if not isinstance(raw_entries, list):
        raise ManifestError("'adds.entries' must be a list")
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ManifestError("each entry must be an object")
        entry_id = _text(raw, "id", 32)
        if not _NAME.match(entry_id):
            raise ManifestError(f"invalid entry id: {entry_id}")
        placement = raw.get("placement", "more")
        if placement not in PLACEMENTS:
            raise ManifestError(f"entry placement must be one of: {', '.join(sorted(PLACEMENTS))}")
        page = _text(raw, "page", 32)
        if page not in pages:
            raise ManifestError(f"entry '{entry_id}' points to an unknown page: {page}")
        entries.append(
            Entry(
                id=entry_id,
                label=_text(raw, "label", 40),
                icon=_text(raw, "icon", 32),
                placement=placement,
                page=page,
            )
        )

    listens = data.get("listens", [])
    emits = data.get("emits", [])
    for what, events in (("listens", listens), ("emits", emits)):
        if not isinstance(events, list) or any(not isinstance(e, str) or not _EVENT.match(e) for e in events):
            raise ManifestError(f"'{what}' must be a list of event names like object.action")
    if listens and "listen_events" not in granted:
        raise ManifestError("listening to events needs the 'listen_events' permission")
    for event in emits:
        if not event.startswith(f"{plugin_id}."):
            raise ManifestError(f"emitted events must start with '{plugin_id}.': {event}")
    migrations = data.get("migrations")
    if migrations is not None and (not isinstance(migrations, str) or ".." in migrations or migrations.startswith(("/", "\\"))):
        raise ManifestError("'migrations' must be a relative folder inside the plugin")

    default_active = data.get("default_active", False)
    if not isinstance(default_active, bool):
        raise ManifestError("'default_active' must be true or false")

    return Manifest(
        id=plugin_id,
        name=_text(data, "name", 60),
        version=version,
        description=_text(data, "description", 300),
        core_api=core_api,
        permissions=granted,
        questionnaire_blocks=blocks,
        report_sections=report_sections,
        widgets=widgets,
        pages=pages,
        entries=tuple(entries),
        settings=has_settings,
        listens=tuple(listens),
        emits=tuple(emits),
        migrations=migrations,
        default_active=default_active,
    )


def load_manifest(folder: Path) -> Manifest:
    path = folder / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ManifestError("manifest.json is missing") from None
    except (OSError, ValueError) as error:
        raise ManifestError(f"manifest.json cannot be read: {error}") from None
    return parse_manifest(data, folder.name)
