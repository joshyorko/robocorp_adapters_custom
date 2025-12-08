# GitHub Copilot Instructions

## Project Overview
This repository (`robocorp_adapters_custom`) provides custom Work Item adapters for Robocorp's automation framework. It enables switching between backends (SQLite, Redis, DocumentDB, Yorko Control Room) via environment variables without changing robot code.

## Architecture & Patterns
- **Pluggable Adapters**: The core pattern is dynamic adapter loading. `workitems_integration.py` reads `RC_WORKITEM_ADAPTER` to instantiate the correct class (e.g., `robocorp_adapters_custom._sqlite.SQLiteAdapter`).
- **Base Class**: All adapters must inherit from `robocorp.workitems._adapters._base.BaseAdapter` and implement methods like `reserve_input`, `create_output`, etc.
- **Internal Modules**: Adapter implementations are prefixed with `_` (e.g., `_sqlite.py`, `_redis.py`) but exposed via the package.
- **Configuration**: Configuration is strictly driven by environment variables. See `devdata/` for example JSON configurations.

## Critical Workflows
- **Testing**: Run tests with `pytest`.
  ```bash
  pytest workitems_tests/
  ```
- **Running Robots**: Use `rcc` with environment files.
  ```bash
  rcc run -t Producer -e devdata/env-sqlite-producer.json
  ```
- **Data Seeding**: Use scripts in `scripts/` to populate backends for development.
  ```bash
  python scripts/seed_sqlite_db.py
  ```

## Key Files & Directories
- `robocorp_adapters_custom/workitems_integration.py`: Entry point for adapter loading.
- `robocorp_adapters_custom/_*.py`: Adapter implementations.
- `devdata/*.json`: Environment configuration files for different backends/roles.
- `docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md`: Detailed architectural guide.

## Development Guidelines
- **Type Hints**: Use Python type hints strictly.
- **Environment Variables**: When adding new configuration, add it to `scripts/config.py` validation logic.
- **Error Handling**: Adapters should raise `robocorp.workitems.EmptyQueue` when no items are available.
