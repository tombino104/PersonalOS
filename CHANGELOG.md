# Changelog

All notable changes to this project are listed here, newest first.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/tombino104/PersonalOS/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/tombino104/PersonalOS/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/tombino104/PersonalOS/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/tombino104/PersonalOS/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tombino104/PersonalOS/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tombino104/PersonalOS/compare/v0.0.0...v0.1.0
[0.0.0]: https://github.com/tombino104/PersonalOS/releases/tag/v0.0.0
