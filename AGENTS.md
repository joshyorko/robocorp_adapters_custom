# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python package for custom Robocorp Work Item adapters. Core code lives in `robocorp_adapters_custom/`; adapter implementations are internal modules such as `_sqlite.py`, `_redis.py`, `_docdb.py`, and `_yorko_control_room.py`. The dynamic adapter entry point is `workitems_integration.py`.

Tests live in `workitems_tests/` and use shared fixtures in `fixtures.py` and `mocks.py`. Development environment examples and work item data live in `devdata/`. RCC task definitions are in `yamls/`. Helper scripts live in `scripts/`, and architecture notes live in `docs/`.

## Build, Test, and Development Commands

- `python -m pip install -e ".[dev]"`: install the package with test, lint, and formatting tools.
- `pytest`: run the configured test suite in `workitems_tests/` with coverage for `robocorp_adapters_custom`.
- `pytest workitems_tests/test_workitems.py`: run one test module while iterating.
- `black robocorp_adapters_custom workitems_tests scripts`: format Python files using the project line length.
- `ruff check robocorp_adapters_custom workitems_tests scripts`: run lint and import-order checks.
- `python -m build`: build package distributions for release.
- `rcc run -t Producer -e devdata/env-sqlite-producer.json`: run an RCC task with a sample backend environment.

## Coding Style & Naming Conventions

Use Python 3.10+ syntax and type hints for public and adapter-facing code. Black and Ruff use a 100-character line length. Keep adapter modules named with a leading underscore and adapter classes named by backend, for example `SQLiteAdapter`.

Configuration is environment-variable driven. When adding a setting, update `scripts/config.py` and add a representative `devdata/env-*.json` example when useful.

## Testing Guidelines

Tests use `pytest` with `pytest-cov`. Name test files `test_*.py`, test classes `Test*`, and test functions `test_*`. Prefer fixtures and `monkeypatch` for environment-variable behavior. Add focused tests for every backend behavior change, especially queue naming, state transitions, file handling, and empty-queue/error paths.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects, sometimes Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, and `chore:`. Keep commits scoped and descriptive, for example `fix: update DocumentDB queue naming`.

Pull requests should include a concise summary, test evidence (`pytest`, Ruff/Black when relevant), linked issues, and notes for changed environment variables or RCC/devdata examples. Include screenshots only for documentation or UI-adjacent changes.

## Security & Configuration Tips

Do not commit real credentials, API tokens, database passwords, or private TLS material. Keep sample values in `devdata/` clearly non-secret. Prefer local SQLite examples for quick validation; use Redis, DocumentDB, or Yorko Control Room configs only when that backend is intentionally under test.
