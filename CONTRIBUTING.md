# Contributing to noisekit

Thanks for your interest in contributing!

## Quick start

```bash
git clone https://github.com/Karamouche/noisekit
cd noisekit
uv sync --dev
uv run pre-commit install
```

Run tests:

```bash
uv run pytest
```

## How to contribute

- **Bug reports** — open an issue with a minimal reproducer (dataset, preset, command run)
- **Feature requests** — open an issue first to discuss before coding
- **Pull requests** — keep PRs focused; one concern per PR is easiest to review

## Code style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting, enforced via pre-commit. Run `uv run ruff check .` and `uv run ruff format .` before pushing.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.), enforced by commitlint.

## Adding a preset

Drop a YAML file in `noisekit/presets/` following the format in `CLAUDE.md`. Include a row in the preset table in `README.md` and a short note in `CLAUDE.md`.

## License

By contributing you agree that your work is released under the [MIT License](LICENSE).
