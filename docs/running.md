# Running Personal OS

Requires Docker. Any Docker host works: a laptop, a home server, a Raspberry Pi, a VPS behind a private network.

```bash
docker compose up -d --build
curl http://127.0.0.1:47213/health
```

The server listens on `127.0.0.1` only. Data lives in `./data` (mounted as a volume, ignored by git). The host port (47213 by default) can be changed with `HOST_PORT`. The image builds the web interface too, so there is only one container.

## First run

There is no account yet. Open `http://127.0.0.1:47213`: the setup page asks for a one-time setup code. The code is saved in `data/setup-code.txt` (and printed in the container logs while no account exists); a new code is generated at every start and every time it is used. After five wrong codes the page locks for 15 minutes. Nothing else is reachable without logging in.

You can also create the first user from the command line:

```bash
docker compose exec personal-os python -m app.cli create-user --name <your-name>
```

## Forgotten password

If you forget the password, or the account is locked after too many failed attempts, set a new one:

```bash
docker compose exec personal-os python -m app.cli reset-password
```

To start from scratch, the login page has a "start over" link (also in Settings > Account): with the code from `data/setup-code.txt` it **erases all data**, and the app starts again from the welcome screens.

## Backups

Everything lives in the data folder, so a backup is a copy of it. The app also does it for you: a backup is made every day (at a time you choose, 03:00 by default; if the device was off, as soon as it is on again; the last 7 are kept) in `data/backups`. **Settings > Backups** lets you make one now and download it, or restore from a saved backup or an uploaded `.zip`. Before a restore the app backs up the current state first. Backups never contain the setup code.

## Settings

Environment variables (see `.env.example`):

- `COOKIE_SECURE`: `auto`, `1` or `0`.
- `ALLOWED_ORIGINS`: extra hosts allowed for write requests, comma separated.
- `SETUP_CODE_REQUIRED=0`: create the first account without the setup code. Only safe when something else already protects the app, like a login in front of it.
- `ENABLE_DOCS=1`: serve the interactive API docs at `/docs`.
- `PLUGINS_DIR`: where plugins are loaded from.
- `PLUGIN_HANDLER_TIMEOUT`: seconds a plugin may take to react to an event (5 by default).

## Development

Database changes are numbered SQL files in `migrations/`, applied automatically at startup.

```bash
cd web
npm install
npm test          # unit tests for dates, charts and translations
npm run dev       # dev server; proxies /api to http://127.0.0.1:47213 (change with BACKEND_URL)
npm run build     # writes web/dist, which the server serves
```

Texts live in `web/src/locales/` (English is the source and the default, Italian is a translation). Colors come only from the theme tokens in `web/src/app.css`.
