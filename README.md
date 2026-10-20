# Personal OS

A personal growth system for one person: six life areas, a relative score and an evening questionnaire. Lightweight, plugin-based, designed to run in a docker container (expecially on UmbrelOS), behind Tailscale.

> **Status: v0.1.0, skeleton.** A minimal server runs in Docker; there are no features yet.

## Guiding ideas

- A mirror, not a judge. It is not a game.
- It measures behaviors, never results.
- A day left blank is empty, not 0%.
- Your data stays yours: the database and backups live outside the repo.

## Run

Requires Docker.

```bash
docker compose up -d --build
curl http://127.0.0.1:3100/health
```

Data lives in `./data` (mounted as a volume, ignored by git). The host port can be changed with `HOST_PORT`.

## Versioning

[Semantic Versioning](https://semver.org/): `0.x.y` until v1. Changes are listed in [CHANGELOG.md](CHANGELOG.md). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).

## License

[PolyForm Noncommercial 1.0.0](LICENSE): you may read, use, modify and share the code for **noncommercial** purposes. Commercial use is not allowed without the author's permission.
