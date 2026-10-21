# Contributing

Thanks for your interest in Personal OS. Bug reports, ideas and pull requests are welcome.

## Before you start

Personal OS is a mirror, not a judge. A few things are on purpose and will not change:

- it measures behaviors, never results;
- a day left blank is empty, not 0%;
- no notifications tied to points, no ranks or levels, no streaks;
- few activities per area.

If an idea works against these, it is probably not a fit for the core. Extra features are better as a [plugin](docs/plugins.md): plugins are small, optional and can be turned off.

## Reporting a bug or asking for a feature

Open an issue and fill in the template. Never paste your database, backups, tokens or the setup code. Describe what you did and what you expected; screenshots with demo data are welcome.

For questions and ideas that are not a bug yet, use Discussions.

## Pull requests

1. Open an issue first for anything bigger than a small fix, so we can agree on the direction.
2. Run the tests: `python -m pytest` (see the README for the setup) and `npm test` in `web/`.
3. Keep changes small and focused. Add or update tests; the scoring engine in particular must stay covered.
4. Everything in the repository is in English: code, names, messages, docs. Interface texts live in `web/src/locales/` (English is the source, Italian is a translation; both files must have the same keys). Avoid code comments unless they explain something that is not obvious.
5. Colors come only from the theme tokens in `web/src/app.css`.
6. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`), in English.
7. Never include personal data: databases, backups, keys, tokens, `.env` files. Example data must be fake and generic.

By contributing you agree that your contribution is licensed under the project's license, [PolyForm Noncommercial 1.0.0](LICENSE).
