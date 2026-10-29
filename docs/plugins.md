# Writing a plugin

A plugin is a folder in `plugins/` with a manifest, an optional Python backend and an optional Svelte interface. `plugins/mood` is a complete, real plugin (a mood tracker with a questionnaire block, a page and a section in past reports) and `plugins/calendar` is one with a backend, a page and a dock entry, and `plugins/journal` is a small one with a backend and a page. Plugins are bundled into the Docker image: add a folder, rebuild the image, then turn the plugin on in **Settings > Plugins**.

```
plugins/<id>/
  manifest.json
  backend/
    __init__.py        # defines setup(api)
    migrations/        # numbered .sql files
  ui/
    index.js           # exports the screens the plugin adds
    locales/en.json    # optional texts, one file per language
```

Plugins trust the core and the core trusts plugins: they run in the same process. The rules below keep honest mistakes from hurting your data; they are **not** a security boundary against hostile code. Only install plugins you have read.

## Manifest

```json
{
  "id": "mood",
  "name": "Example",
  "version": "0.1.0",
  "description": "One line shown in the settings.",
  "core_api": "1.x",
  "permissions": ["read_reports", "questionnaire_block", "api_routes"],
  "adds": {
    "questionnaire_blocks": ["mood"],
    "report_sections": [],
    "widgets": [],
    "pages": [],
    "entries": [],
    "settings": false
  },
  "listens": [],
  "emits": [],
  "migrations": "backend/migrations"
}
```

Optional: `"default_active": true` turns the plugin on once, the first time the app sees it (and after a full reset), with the permissions it lists. The user can turn it off afterwards and it stays off. Only use it for features that are part of the app, like the calendar.

- `id` is lowercase letters, digits and underscores, and must equal the folder name. Your tables must start with `plg_<id>_`.
- `core_api` is the core API major version you need (`1.x`). If it does not match, the plugin shows as incompatible and cannot be turned on.
- `widgets` show a card on Home. By default it goes below the charts; a UI module can export `widgetPlacement: { <widget>: 'top' }` to put it right under the date.
- `report_sections` add a section to the detail of a past report (in the review, when you tap a day).
- `entries` are links to your pages: `{ "id", "label", "icon", "placement": "dock" | "more", "page" }`. The dock holds at most five entries in total, so extra ones go to the More page.
- `emits` must start with `<id>.`; `listens` can name any core event or another plugin's event.

## Permissions

The user sees this list and confirms it when turning the plugin on.

| Permission | Allows |
| --- | --- |
| `read_activities` | read the `activities` and `areas` tables, receive the `activity` field of events |
| `read_reports` | read `reports` and `completions`, receive `completions` and `reflection` in events |
| `read_scores` | read `daily_scores`, receive `scores` and `overall` in events |
| `questionnaire_block` | add a block to the evening questionnaire |
| `ui_panel` | add widgets, pages, entries and a settings panel |
| `api_routes` | serve routes under `/api/v1/plugins/<id>/` |
| `listen_events` | react to events |
| `ingest` | receive data posted from outside with a revocable, write-only token |
| `request_reminder` | reserved for the notifications plugin |

Scores are only reachable with `read_scores`, so a plugin without it cannot build anything around points.

## Backend

`backend/__init__.py` defines `setup(api)`:

```python
from datetime import date

def setup(api):
    @api.router.get("/notes/{day}")
    def get_note(day: date, ctx=api.ctx):
        row = ctx.db.execute("SELECT note FROM plg_mood_entries WHERE ...").fetchone()
        return {"text": row["text"] if row else None}

    @api.on("report.completed")
    def on_completed(ctx, payload):
        ...
```

- `api.router` is a FastAPI router. Routes are served only while the plugin is on, and only to a logged-in user. An error inside a route returns a clean `500` for that request and counts against the plugin; it never affects the rest of the app.
- `api.ctx` gives each route a `PluginContext` with `db` (a SQLite connection), `now`, `today` and `plugin_id`. `ctx.report_id("2026-10-20")` returns the id of a day's report (or `None`) without needing to read the reports table. Statements commit one by one; use `with ctx.transaction():` to group several.
- `api.on(event)` registers an event handler `handler(ctx, payload)`. Declare the event in `listens`.
- `api.emit(event, payload)` sends one of your own events.

### Data rules, enforced by the core

- Your connection can read and write only your own `plg_<id>_` tables. It can read the core tables its permissions allow, nothing else (no users, sessions, settings).
- Migrations may only create or change `plg_<id>_` objects. A migration that touches anything else fails and is rolled back.
- A table with a `report_id` column is guarded: inserts, updates and deletes are refused when the report is closed (the day after the edit window) or does not exist. Tables without `report_id` are not restricted.
- Turning a plugin off never deletes its data. Its data is removed only by the explicit **Remove its data** action in Settings > Plugins (the plugin must be off and you type its id to confirm); that drops its `plg_<id>_` tables and nothing else.

## Receiving data from outside

A plugin with the `ingest` permission can accept data from a device that has no login, such as a phone posting its step count. It registers one handler:

```python
def setup(api):
    @api.ingest
    def receive(ctx, payload):
        if not isinstance(payload, dict):
            raise ValueError("the payload must be an object")
        ...
```

The core does the rest. The user creates a token for that plugin (`POST /api/v1/tokens` with `name` and `plugin`; the secret is shown once and only its hash is stored), and the device posts JSON to `POST /api/v1/ingest/<id>` with `Authorization: Bearer <token>` (or an `X-Api-Key` header). A token works for one plugin only, can be revoked (`DELETE /api/v1/tokens/<id>`), and can only write: the response is always `{"ok": true}`. The body is limited to 1 MB, the handler runs with the same table rules as the routes, and a `ValueError` becomes a `422` for the sender. A turned-off plugin answers `404`.

## Events

Handlers run after the data is saved, in the background, so a slow or failing plugin cannot make a save fail.

| Event | When | Payload |
| --- | --- | --- |
| `report.completed` | a report is completed for the first time | `day`, `completions`, `reflection`, `scores`, `overall` |
| `report.modified` | a completed report is edited | same |
| `report.closed` | the edit window ended | `day`, `report_id` |
| `activity.created` / `activity.modified` / `activity.archived` | activity changes | `activity` |
| `plugin.activated` / `plugin.deactivated` | a plugin is turned on or off | `plugin` |

Fields are removed from the payload when the plugin lacks the matching permission.

### Failures

A handler that raises, or takes longer than 5 seconds, is recorded in the audit log and the plugin shows as **Error** in the settings with the last message. After 5 failures in a row the plugin is switched off automatically; it can be turned back on. Any success resets the count.

## Interface

`ui/index.js` default-exports what the plugin adds. Components are compiled into the app, so they use the core's classes and CSS variables (`var(--ink)`, `var(--area-physical)`, ...) and never hard-coded colors.

```js
import MoodBlock from './MoodBlock.svelte';

export default {
  questionnaireBlocks: { mood: MoodBlock },
  reportSections: {},
  widgets: {},
  pages: {},
  settingsPanel: null,
};
```

- A questionnaire block receives `day` and `editable`; a report section receives `day`; pages and widgets receive nothing.
- Import core helpers with the `$core` alias: `import { pluginRequest } from '$core/lib/api.js'`, `import { t } from '$core/lib/i18n.svelte.js'`.
- `pluginRequest(id, method, path, body)` calls your backend routes.
- Texts: put `ui/locales/en.json` (and other languages) next to `index.js`; they become `t('plugin.<id>.<key>')`. English is the source language. `name` and `description` keys translate the plugin's own name and description.
- Entry labels can be translated with the key `entry.<entryId>`.

Run `npm run dev` or `npm run build` in `web/` after changing a plugin interface: the `sync-plugins` script copies every `plugins/*/ui` into the web build.

## Checklist

1. Folder name, `id` and table prefix agree.
2. Ask only for the permissions you use.
3. Migrations are numbered (`001_init.sql`) and never edited once released: add a new file instead.
4. Try it with the plugin off, on, off again, and with a deliberate error in a handler.
