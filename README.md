# Personal OS

**Discipline, without the dopamine tricks.**

A free, self-hosted daily check-in for six areas of your life. No streaks, no points, no subscription, no cloud.

**[Try the live demo](https://tombino104.github.io/PersonalOS/)** (made-up data, nothing leaves your browser)

| | |
| --- | --- |
| ![Home: trends per area and a six-month heatmap](docs/screenshots/home.png) | ![The evening questionnaire](docs/screenshots/questionnaire.png) |
| ![The star: the six areas together](docs/screenshots/star.png) | ![Past reports](docs/screenshots/past-reports.png) |
| ![The calendar plugin](docs/screenshots/calendar.png) | ![Home in the dark theme](docs/screenshots/home-dark.png) |

*Generated demo data.*

## Why

- **Free, really.** No paid tier, no ads. Open source (AGPL-3.0).
- **No toxic gamification.** No streaks, ranks or points to chase, no notifications tied to your score. A day you skip is empty, not a failure.
- **Pure discipline.** You note what you did, never what you achieved. A mirror, not a judge.
- **Your data, your machine.** One SQLite file, daily backups, no telemetry.

## Run

You need Docker.

```bash
docker compose up -d --build
```

Open `http://127.0.0.1:47213`. The first screen asks for a one-time setup code, which is in `data/setup-code.txt` (and in the container logs). Then the welcome screens end with the creation of your account.

The server listens on `127.0.0.1` only. To reach it from other devices, put it behind a reverse proxy or a private network such as Tailscale: it is not meant to face the public internet.

Prebuilt images (amd64 and arm64) are at `ghcr.io/tombino104/personalos`. [Run on umbrelOS](docs/umbrel.md) is supported too, through a community app store.

More about running it (settings, password reset, command line): [docs/running.md](docs/running.md).

## Features

- Six life areas, a few activities each, a relative score per area
- An evening questionnaire, with optional days of the week per activity and an optional time before which it stays closed
- Trends, a six-month heatmap, the "star" of the six areas, past reports
- Plugins: calendar, mood tracker, journal, daily quote; [write your own](docs/plugins.md)
- Light and dark theme, English and Italian
- Backups and restore from Settings, a built-in guide

## Develop

Python 3.13+ (FastAPI, SQLite) and Node 24+ (Svelte 5, Vite).

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest
cd web && npm install && npm test && npm run build
```

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [SECURITY.md](SECURITY.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

Copyright (C) 2026 Lorenzo (tombino104). Released under the [GNU Affero General Public License v3.0](LICENSE). Versions up to v0.10.2 were published under PolyForm Noncommercial 1.0.0.
