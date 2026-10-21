# Changelog

All notable changes to this project are listed here, newest first.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.14.0] - 2026-10-21

### Added
- Activities can have a short description (up to 300 characters, optional). It shows under the name in the evening questionnaire, as a reminder of what counts. Activities and the completions of a report now carry `description` in the API. Closes #3.

### Changed
- Reports that can still be edited now follow your changes to the activities, also after they are completed: when you open today's or yesterday's report, new activities appear, archived ones disappear, renames and weight changes apply, ticks are kept and the scores are recalculated. Older reports stay as they were. `POST /api/v1/reports/{day}/sync` no longer refuses a completed report. Closes #4.

## [0.13.1] - 2026-10-21

### Added
- A live demo on GitHub Pages: the real interface running in the browser against a built-in fake server with made-up data, nothing stored anywhere. Built with `DEMO=1 npm run build` (`web/src/demo/`) and deployed by the new Demo workflow.

### Changed
- The README now starts with the screenshots and is much shorter; running details moved to `docs/running.md`, and umbrelOS is presented as one supported option rather than the target.
- Home no longer shows a "Home" label next to the avatar.

## [0.13.0] - 2026-10-22

### Added
- Each activity can be set for specific days of the week (seven toggles, Monday to Sunday, all on by default). The evening questionnaire of a day lists only the activities scheduled for that weekday; the relative score ignores the others, and an area with nothing scheduled that day is empty, not 0%. Changes apply from today on and past reports are unchanged. Activities now carry `days` (a list of weekdays, 0 for Monday to 6 for Sunday) in the API. Closes #1.
- Optional report time (Settings > Activities): before the chosen time, the report of the current day is locked, with a message saying when it opens. Yesterday stays editable, and the lock is enforced by the server (`report_not_open`). Settings `report_lock` and `report_time`; `GET /api/v1/today` returns `report_opens_at` while the report is locked. Closes #2.

## [0.12.1] - 2026-10-22

### Added
- Settings > Community: links to GitHub to suggest an idea, report a problem, contribute code, read the source, the releases, the security policy and the license, with the installed version.

### Changed
- New positioning in the README, the repository description and the Umbrel listing: "Discipline, without the dopamine tricks".

## [0.12.0] - 2026-10-22

### Added
- Welcome screens: before creating the account, the first run walks through what the app does (the six areas, the evening questionnaire, the score, Home and the Star, plugins, your data), with smooth transitions. They can be skipped.
- Settings > Guide: a user guide with the basics (questionnaire, score, activities, Home, calendar, plugins, mascot, backups, account, data), in English and Italian.

### Changed
- "Erase all data" now needs only the setup code and a confirmation. It wipes everything, including the account, and the app starts again from the welcome screens (`POST /api/v1/auth/reset` takes only `code` and returns `setup_required`). The name and password are chosen in the last welcome step.
- The theme and language kept in the browser are forgotten too after erasing.

## [0.11.0] - 2026-10-22

### Changed
- **License:** from this version the project is released under the GNU Affero General Public License v3.0. Versions up to 0.10.2 were published under PolyForm Noncommercial 1.0.0.
- New setting `SETUP_CODE_REQUIRED` (on by default): when off, the first account is created without the setup code. The code still protects "Erase all data". The setup page and `GET /api/v1/auth/status` follow it (`setup_code_required`).
- The Umbrel packaging keeps the umbrelOS login in front of the app and turns the setup code off, so the first run needs no file or log.

### Added
- A link to the source code on the More page, as the AGPL asks for network services.
- `umbrel-official/`: the packaging and the pull request text for the official umbrelOS App Store.

## [0.10.2] - 2026-10-22

### Added
- Settings > Account > Erase all data: the same reset as the login page, available while logged in (setup code, a name, the password typed twice and a confirmation).
- `CONTRIBUTING.md`, `SECURITY.md`, issue templates and a pull request template.

## [0.10.1] - 2026-10-22

### Changed
- Home remembers the period (week or month) and the area filter (all six, or the first or second three), saved with the rest of your settings (`home_period`, `home_areas`).
- Every release tag now also creates a GitHub release, with its notes taken from this changelog.

### Removed
- The example plugin. `plugins/mood` and `plugins/calendar` are the references for writing a plugin.

## [0.10.0] - 2026-10-22

### Added
- Mascot profile (Settings > Mascot): a photo, a name shown in the app, a short note about you and an optional birth year. The photo is resized in the browser and stored in the database, so it is part of the data folder and of the backups. It shows in the Home header and on the More page.
- Daily quote plugin (`plugins/quotes`): a famous quote, one a day, in English or Italian, in a card under the date on Home. Off until you turn it on in Settings > Plugins. It never creates points.
- Home widgets can ask for the top position (`widgetPlacement` in the plugin UI module).
- API: `GET/PUT /api/v1/profile`, `PUT/DELETE/GET /api/v1/profile/photo`.

## [0.9.1] - 2026-10-22

### Changed
- Automatic backups can be turned off and their time chosen in Settings > Backups. If the device was off at that time, the backup is made as soon as it is on again.
- New settings `backup_auto` and `backup_time`.

## [0.9.0] - 2026-10-22

### Added
- Backups: a consistent copy of the database in a `.zip` (with a small manifest) made every night at 03:00 in `data/backups` (the last 7 kept), on demand (the last 20 kept), and automatically before every restore (the last 5 kept).
- Settings > Backups: back up now and download, list, download and restore saved backups, and restore from an uploaded file. A restore needs a typed confirmation, refuses damaged files and backups from a newer version, and upgrades the schema of older ones.
- API: `GET/POST /api/v1/backups`, `GET /api/v1/backups/{name}`, `POST /api/v1/backups/restore` and `POST /api/v1/backups/{name}/restore` (both need `?confirm=restore`).
- Theme and language are now kept in the server settings (`theme`, `language`), so they are part of the data folder and the backups. The first time, the choice already made in the browser is copied to the server.

## [0.8.0] - 2026-10-22

### Added
- Calendar plugin (`plugins/calendar`), on from the start and shown in the dock: a month grid and the agenda of the chosen day, events with a title, a day, an optional time, a category and notes, repeats (daily, weekly, monthly, yearly, with an optional end day), editing and deleting. It never creates points.
- Manifest field `default_active`: the plugin is turned on once the first time the app sees it, and stays off if the user turns it off.
- "Start over" on the login page: the setup code plus a new name and a password typed twice erase all data (reports, activities, settings and plugin data) and create a new account (`POST /api/v1/auth/reset`).
- App icon and gallery screenshots for the Umbrel store entry.

### Changed
- The setup code file now always exists: a new code is written at every start and each time a code is used, so it can also unlock the reset.

### Fixed
- Plugin migrations can create indexes.

## [0.7.2] - 2026-10-22

### Fixed
- The login and first-run setup pages are now centered vertically on phones too (they were pushed up by the space reserved for the dock).

## [0.7.1] - 2026-10-21

### Added
- GitHub workflows: **CI** runs all tests on every push, **Image** builds and publishes the Docker image (amd64 and arm64) to `ghcr.io/tombino104/personalos` on every release tag.
- `umbrel-store/`: a community app store for umbrelOS with the Personal OS app, and `docs/umbrel.md` explaining how to install it.

### Changed
- The container now starts as root, fixes the ownership of the data folder and then drops to a normal user, so it works with any mounted folder (like the one umbrelOS provides).
- Write requests are now accepted when the browser says they are same-origin (`Sec-Fetch-Site`), which keeps the app working behind proxies that rewrite the host. The previous Origin check remains as a fallback.
- The Docker build no longer runs the web tests; CI does.

## [0.7.0] - 2026-10-21

### Added
- Mood tracker plugin (`plugins/mood`): a 1 to 5 scale and an optional note in the evening questionnaire, a page with the trend (the line breaks on days without an entry), how many times each level was chosen and recent notes, and the mood shown in past reports. It never enters scores and cannot read them.
- Plugin extension point `report_sections`: plugins can add a section to the detail of a past report.
- Plugin data removal: Settings > Plugins can remove a switched-off plugin's data after typing its id (`POST /api/v1/plugins/{id}/remove-data`); core data is never touched.
- `ctx.report_id(day)` for plugins, so they no longer need permission to read reports just to find a day's report.

### Changed
- The example plugin no longer asks to read reports.

### Fixed
- Plugin tables with a `UNIQUE` constraint can now be created by migrations.

## [0.6.0] - 2026-10-21

### Added
- Plugin system: manifests, discovery, install on first activation, numbered migrations, per-plugin API routes, events delivered after saving, a sandboxed database connection per plugin and fault isolation (errors are recorded, repeated errors switch the plugin off).
- Plugin extension points in the interface: questionnaire blocks, Home widgets, pages, dock and More entries, and a settings panel. Plugin texts are merged into the translations.
- Settings > Plugins: turn plugins on and off after confirming the permissions they ask for, with their state and last error.
- `plugins/example`: a small example plugin, off by default, with a developer guide in `docs/plugins.md`.
- Audit log table; the app now closes reports whose edit window ended and announces it to plugins (`report.closed`).
- Events: `report.completed`, `report.modified`, `report.closed`, `activity.created`, `activity.modified`, `activity.archived`, `plugin.activated`, `plugin.deactivated`.
- `GET /api/v1/plugins` and `POST /api/v1/plugins/{id}/activate` and `.../deactivate`.

### Changed
- Settings are split into separate tabs: Activities, Account, Appearance, Plugins.
- English is now the default interface language; Italian and automatic detection are options in Settings > Appearance.

## [0.5.1] - 2026-10-21

### Added
- First-run setup page: until an account exists, the interface asks for a one-time setup code (saved in `data/setup-code.txt` and printed in the logs), then creates the account and signs in. Five wrong codes lock the page for 15 minutes.
- `GET /api/v1/auth/status` and `POST /api/v1/auth/setup`.

### Changed
- Creating the first user from the command line is now optional.

## [0.5.0] - 2026-10-21

### Added
- Web interface (Svelte 5 + Vite), built inside the Docker image and served by the same container: login, home (trends per area and a six-month heatmap), evening questionnaire with a completion stamp, star (radar of the six areas), past reports, more menu and settings (activities, account, appearance).
- Light and dark themes from a single set of tokens, plus a six-area color palette; fonts are bundled, nothing is loaded from other sites.
- English and Italian texts (English is the source); the language follows the device unless changed in the settings.
- API: `GET /api/v1/today`, `GET /api/v1/stats/areas`, `GET /api/v1/stats/activities`, and an `overall` score per day (mean of the area scores, empty areas ignored).
- Security headers and a content security policy on every response.

### Changed
- The Docker image is now multi-stage and runs the web unit tests while building.
- The dock has four entries until plugins add their own (calendar, mood, skills).

## [0.4.0] - 2026-10-20

### Added
- Password login: `POST /api/v1/auth/login`, `logout`, `me` and `password` (change). Everything except login and `/health` now requires a session.
- Passwords hashed with scrypt (standard library); minimum length of 10 characters.
- Server-side sessions in an HttpOnly, SameSite=Strict cookie; only a hash of the token is stored. Sessions last 30 days and renew on use.
- Account lock for 15 minutes after 5 failed attempts.
- Command line: `python -m app.cli create-user` and `reset-password` (also unlocks the account and closes all sessions).
- Write requests from a foreign `Origin` are refused (`ALLOWED_ORIGINS` adds trusted hosts).

### Changed
- Interactive API docs are off unless `ENABLE_DOCS=1`.
- The placeholder user from 0.3.0 is adopted by `create-user`, so existing reports are kept.

## [0.3.0] - 2026-10-20

### Added
- Versioned core API under `/api/v1`: areas, activities (create, edit, archive, restore), reports (open, tick, reflection, sync, complete, list), scores by period and settings.
- Uniform error format: `{"error": {"code", "message"}}`.
- Free-text `reflection` on reports, frozen with the rest of the report.
- Soft warning when an area has more than 5 active activities.
- A draft report can be re-synced with the current activities until it is completed.

### Changed
- The container port is bound to `127.0.0.1` only until login exists.

## [0.2.0] - 2026-10-20

### Changed
- Server rewritten in Python + FastAPI (was Node.js).

### Added
- SQLite schema with numbered SQL migrations: users, settings, areas, activities, reports, completions, daily scores.
- Scoring engine as an isolated pure function; a maximum of 0 gives a null score, not 0%.
- Logical day with a 04:00 cutoff and a "yesterday only" edit window.
- Immutable report snapshots: completions keep the activity name and weight at the time.
- Activities and reports can never be deleted, only archived.
- Generic sample activities, seeded once on an empty database.
- Test suite (pytest).

## [0.1.0] - 2026-10-20

### Added
- Minimal Node.js server with a `/health` endpoint (no dependencies).
- `Dockerfile` and `docker-compose.yml`: data folder mounted as a volume, non-root user, healthcheck, automatic restart.

## [0.0.0] - 2026-10-19

### Added
- Initial project skeleton: README, PolyForm Noncommercial license, `.gitignore`, `.env.example`.

[Unreleased]: https://github.com/tombino104/PersonalOS/compare/v0.14.0...HEAD
[0.14.0]: https://github.com/tombino104/PersonalOS/compare/v0.13.1...v0.14.0
[0.13.1]: https://github.com/tombino104/PersonalOS/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/tombino104/PersonalOS/compare/v0.12.1...v0.13.0
[0.12.1]: https://github.com/tombino104/PersonalOS/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/tombino104/PersonalOS/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/tombino104/PersonalOS/compare/v0.10.2...v0.11.0
[0.10.2]: https://github.com/tombino104/PersonalOS/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/tombino104/PersonalOS/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/tombino104/PersonalOS/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/tombino104/PersonalOS/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/tombino104/PersonalOS/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/tombino104/PersonalOS/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/tombino104/PersonalOS/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/tombino104/PersonalOS/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/tombino104/PersonalOS/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/tombino104/PersonalOS/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/tombino104/PersonalOS/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/tombino104/PersonalOS/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/tombino104/PersonalOS/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/tombino104/PersonalOS/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tombino104/PersonalOS/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tombino104/PersonalOS/compare/v0.0.0...v0.1.0
[0.0.0]: https://github.com/tombino104/PersonalOS/releases/tag/v0.0.0
