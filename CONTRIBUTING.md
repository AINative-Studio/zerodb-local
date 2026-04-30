# Contributing to zerodb-local

Thanks for contributing! Here's how to get started.

## Setup

```bash
git clone https://github.com/AINative-Studio/zerodb-local.git
cd zerodb-local/zerodb-local
pip install -e ".[lite,dev]"
```

## Running tests

```bash
python -m pytest tests/ -v --cov=zerodb_local --cov-report=term-missing
```

Coverage must be >= 70% for CI to pass.

## Linting

```bash
pip install ruff
ruff check zerodb_local/
```

## Branch naming

```
[type]/[issue-number]-[short-slug]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Commit format

```
[TYPE] Short description

- Detail
- Detail

Closes #123
```

Types: `[FEATURE]`, `[BUG]`, `[DOCS]`, `[REFACTOR]`, `[TEST]`, `[DEVOPS]`

## Releasing

Releases are automated. To cut a release:

1. Bump `version` in `zerodb-local/pyproject.toml`
2. Commit: `[DEVOPS] Bump version to x.y.z`
3. Tag: `git tag vx.y.z && git push origin vx.y.z`

The `publish.yml` workflow handles PyPI upload and GitHub Release creation.

## Questions?

Open an issue or email hello@ainative.studio.
