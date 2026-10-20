# Personal OS

A personal growth system for one person: six life areas, a relative score and an evening questionnaire. Lightweight, plugin-based, designed to run in a docker container (especially on UmbrelOS), behind Tailscale.

> **Status: v0.5.1.** Core API, password login and the web interface are in place (login, questionnaire, home, star, past reports, settings). Plugins, backups, reminders and agents come next.

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

On the first run there is no account yet. Open `http://127.0.0.1:47213`: the setup page asks for a one-time setup code. The code is saved in `data/setup-code.txt` (and printed in the container logs); a new code is generated at every start until an account exists. After five wrong codes the page locks for 15 minutes. Nothing else is reachable without logging in.

You can also create the first user from the command line:

```bash
docker compose exec personal-os python -m app.cli create-user --name <your-name>
```

If you forget the password, or the account is locked after too many failed attempts, set a new one:

```bash
docker compose exec personal-os python -m app.cli reset-password
```

Other settings (see `.env.example`): `COOKIE_SECURE` (`auto`, `1` or `0`), `ALLOWED_ORIGINS` (extra hosts allowed for write requests, comma separated), `ENABLE_DOCS=1` to serve the interactive API docs at `/docs`.

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

Texts live in `web/src/locales/` (English is the source, Italian is a translation). Colors come only from the theme tokens in `web/src/app.css`.

## Versioning

[Semantic Versioning](https://semver.org/): `0.x.y` until v1. Changes are listed in [CHANGELOG.md](CHANGELOG.md). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).

## License

[PolyForm Noncommercial 1.0.0](LICENSE): you may read, use, modify and share the code for **noncommercial** purposes. Commercial use is not allowed without the author's permission.
