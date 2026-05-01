# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python package for custom Robocorp Work Item adapters. Core code lives in `robocorp_adapters_custom/`; adapter implementations are internal modules such as `_sqlite.py`, `_redis.py`, `_docdb.py`, and `_yorko_control_room.py`. The dynamic adapter entry point is `workitems_integration.py`.
Fizzy/Codex orchestration helpers are in `fizzy_orchestration.py`, with CLI scripts in `scripts/` (`fizzy_seed_sqlite.py`, `fizzy_worker_once.py`, `fizzy_reporter_once.py`) and example env files in `devdata/env-fizzy-*.json`.

Tests live in `workitems_tests/` and use shared fixtures in `fixtures.py` and `mocks.py`. Development environment examples and work item data live in `devdata/`. RCC task definitions are in `yamls/`. Helper scripts live in `scripts/`, and architecture notes live in `docs/`.

## Build, Test, and Development Commands

- `python -m pip install -e ".[dev]"`: install the package with test, lint, and formatting tools.
- `pytest`: run the configured test suite in `workitems_tests/` with coverage for `robocorp_adapters_custom`.
- `pytest workitems_tests/test_workitems.py`: run one test module while iterating.
- `pytest workitems_tests/test_fizzy_orchestration.py`: validate Fizzy/Codex orchestration behaviors.
- `black robocorp_adapters_custom workitems_tests scripts`: format Python files using the project line length.
- `ruff check robocorp_adapters_custom workitems_tests scripts`: run lint and import-order checks.
- `python -m build`: build package distributions for release.
- `python scripts/fizzy_seed_sqlite.py --env devdata/env-fizzy-sqlite-producer.json`: seed Fizzy cards into SQLite.
- `python scripts/fizzy_worker_once.py --env devdata/env-fizzy-sqlite-worker.json`: run one worker execution for one queued Fizzy item.
- `python scripts/fizzy_reporter_once.py --env devdata/env-fizzy-sqlite-reporter.json --dry-run`: validate reporter output without touching Fizzy.
- `rcc run -t Producer -e devdata/env-sqlite-producer.json`: run an RCC task with a sample backend environment.
- `rcc run -t FizzyProducer -e devdata/env-fizzy-sqlite-producer.json`: run one-pass Fizzy producer flow.
- `rcc run -t FizzyWorker -e devdata/env-fizzy-sqlite-worker.json`: run one-pass Fizzy worker flow.
- `rcc run -t FizzyReporterDryRun -e devdata/env-fizzy-sqlite-reporter.json`: run reporter in dry-run mode.

## Coding Style & Naming Conventions

Use Python 3.10+ syntax and type hints for public and adapter-facing code. Black and Ruff use a 100-character line length. Keep adapter modules named with a leading underscore and adapter classes named by backend, for example `SQLiteAdapter`.

Configuration is environment-variable driven. When adding a setting, update `scripts/config.py` and add a representative `devdata/env-*.json` example when useful.

## Testing Guidelines

Tests use `pytest` with `pytest-cov`. Name test files `test_*.py`, test classes `Test*`, and test functions `test_*`. Prefer fixtures and `monkeypatch` for environment-variable behavior. Add focused tests for every backend behavior change, especially queue naming, state transitions, file handling, and empty-queue/error paths.
Add dedicated coverage for Fizzy orchestration paths in `workitems_tests/test_fizzy_orchestration.py` when changing payloads, duplicate-avoidance, worker result flows, or report formatting.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects, sometimes Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, and `chore:`. Keep commits scoped and descriptive, for example `fix: update DocumentDB queue naming`.

Pull requests should include a concise summary, test evidence (`pytest`, Ruff/Black when relevant), linked issues, and notes for changed environment variables or RCC/devdata examples. Include screenshots only for documentation or UI-adjacent changes.

## Security & Configuration Tips

Do not commit real credentials, API tokens, database passwords, or private TLS material. Keep sample values in `devdata/` clearly non-secret. Prefer local SQLite examples for quick validation; use Redis, DocumentDB, or Yorko Control Room configs only when that backend is intentionally under test.
When running Fizzy orchestration locally, keep real `FIZZY_BOARD_ID` and `FIZZY_SOURCE_COLUMN_ID` values out of committed data. Use environment variable overrides for real boards.
