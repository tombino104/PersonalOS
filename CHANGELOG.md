# Changelog

All notable changes to this project are listed here, newest first.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/tombino104/PersonalOS/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/tombino104/PersonalOS/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tombino104/PersonalOS/compare/v0.0.0...v0.1.0
[0.0.0]: https://github.com/tombino104/PersonalOS/releases/tag/v0.0.0
