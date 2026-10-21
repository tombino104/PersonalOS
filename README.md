# Personal OS

A personal growth system for one person: six life areas, a relative score and an evening questionnaire. Lightweight, plugin-based, designed to run in a docker container (especially on UmbrelOS), behind Tailscale.

> **Status: v0.11.0.** Core API, password login, the web interface, a profile with a photo, the plugin system, a built-in calendar, a daily quote and a mood tracker plugin, and backups are in place. Backups, reminders and agents come next.

## Screenshots

Taken with generated demo data.

| | |
| --- | --- |
| ![Home: trends per area and a six-month heatmap](docs/screenshots/home.png) | ![The evening questionnaire](docs/screenshots/questionnaire.png) |
| ![The star: the six areas together](docs/screenshots/star.png) | ![Past reports](docs/screenshots/past-reports.png) |
| ![The calendar plugin](docs/screenshots/calendar.png) | ![Home in the dark theme](docs/screenshots/home-dark.png) |

## Backups

Everything lives in the data folder, so a backup is a copy of it. The app also does it for you: a backup is made every day (at a time you choose, 03:00 by default; if the device was off, as soon as it is on again; the last 7 are kept) in `data/backups`, and **Settings > Backups** lets you make one now and download it, or restore from a saved backup or an uploaded `.zip`. Before a restore the app backs up the current state first. Backups never contain the setup code.

## Guiding ideas

- A mirror, not a judge. It is not a game.
- It measures behaviors, never results.
- A day left blank is empty, not 0%.
- Your data stays yours: the database and backups live outside the repo.

## Run

Requires Docker.

```bash
docker compose up -d --build
curl http://127.0.0.1:47213/health
```

The server listens on `127.0.0.1` only. Data lives in `./data` (mounted as a volume, ignored by git). The host port (47213 by default) can be changed with `HOST_PORT`.

The image builds the web interface too (Svelte + Vite) and the server serves it, so there is only one container.

On the first run there is no account yet. Open `http://127.0.0.1:47213`: the setup page asks for a one-time setup code. The code is saved in `data/setup-code.txt` (and printed in the container logs while no account exists); a new code is generated at every start and every time it is used. After five wrong codes the page locks for 15 minutes. Nothing else is reachable without logging in.

If you forget the password and want to start from scratch, the login page has a "start over" link: with the code from `data/setup-code.txt` and a new name and password (typed twice) it **erases all data** and creates a fresh account.

You can also create the first user from the command line:

```bash
docker compose exec personal-os python -m app.cli create-user --name <your-name>
```

If you forget the password, or the account is locked after too many failed attempts, set a new one:

```bash
docker compose exec personal-os python -m app.cli reset-password
```

Other settings (see `.env.example`): `COOKIE_SECURE` (`auto`, `1` or `0`), `ALLOWED_ORIGINS` (extra hosts allowed for write requests, comma separated), `SETUP_CODE_REQUIRED=0` to create the first account without the setup code (only safe when something else already protects the app, like the umbrelOS login), `ENABLE_DOCS=1` to serve the interactive API docs at `/docs`, `PLUGINS_DIR` (where plugins are loaded from), `PLUGIN_HANDLER_TIMEOUT` (seconds a plugin may take to react to an event, 5 by default).

## Develop

Python 3.13+ and FastAPI, with SQLite for storage.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest
```

Database changes are numbered SQL files in `migrations/`, applied automatically at startup.

The web interface lives in `web/` (Svelte 5 + Vite). Node 24 or newer:

```bash
cd web
npm install
npm test          # unit tests for dates, charts and translations
npm run dev       # dev server; proxies /api to http://127.0.0.1:47213 (change with BACKEND_URL)
npm run build     # writes web/dist, which the server serves
```

Texts live in `web/src/locales/` (English is the source and the default, Italian is a translation you can pick in the settings). Colors come only from the theme tokens in `web/src/app.css`.

## Plugins

Features beyond the core are plugins: a folder in `plugins/` with a manifest, a Python backend and a Svelte interface. Turn them on and off in Settings > Plugins; each one lists the permissions it asks for. `plugins/calendar` (a calendar with repeating events) is on from the start and shows in the dock, `plugins/quotes` (a famous quote under the date on Home, off until you turn it on) and `plugins/mood` (a mood tracker) are other real plugins, and [docs/plugins.md](docs/plugins.md) explains how to write your own.

## Umbrel

The image is published to `ghcr.io/tombino104/personalos` at every release, and `umbrel-store/` is a community app store for umbrelOS. See [docs/umbrel.md](docs/umbrel.md).

## Contributing

Issues and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). To report a security problem, see [SECURITY.md](SECURITY.md).

## Versioning

[Semantic Versioning](https://semver.org/): `0.x.y` until v1. Changes are listed in [CHANGELOG.md](CHANGELOG.md). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).

## License

Copyright (C) 2026 Lorenzo (tombino104). Released under the [GNU Affero General Public License v3.0](LICENSE): you can use, study, modify and share it, including commercially, as long as you share your changes under the same license, also when you offer the app as a service over a network.

Versions up to v0.10.2 were published under PolyForm Noncommercial 1.0.0; from v0.11.0 on the license is the AGPL-3.0.
