# Personal OS

A personal growth system for one person: six life areas, a relative score and an evening questionnaire. Lightweight, plugin-based, designed to run in a docker container (especially on UmbrelOS), behind Tailscale.

> **Status: v0.2.0.** Data model and scoring engine are in place; there is no user interface yet.

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

Data lives in `./data` (mounted as a volume, ignored by git). The host port (47213 by default) can be changed with `HOST_PORT`.

## Develop

Python 3.13+ and FastAPI, with SQLite for storage.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest
```

Database changes are numbered SQL files in `migrations/`, applied automatically at startup.

## Versioning

[Semantic Versioning](https://semver.org/): `0.x.y` until v1. Changes are listed in [CHANGELOG.md](CHANGELOG.md). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).

## License

[PolyForm Noncommercial 1.0.0](LICENSE): you may read, use, modify and share the code for **noncommercial** purposes. Commercial use is not allowed without the author's permission.
