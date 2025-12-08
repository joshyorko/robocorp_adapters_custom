# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Custom Work Item Adapters for Robocorp's producer-consumer automation workflows. Provides pluggable backend support (SQLite, Redis, DocumentDB/MongoDB, Yorko Control Room) with environment-variable-based adapter selection.

## Common Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest workitems_tests/

# Run a single test file
pytest workitems_tests/test_adapters.py

# Run a specific test
pytest workitems_tests/test_adapters.py::test_function_name -v

# Lint
ruff check .

# Format
black .
```

## Architecture

### Adapter Pattern
The package uses a pluggable adapter pattern where the active adapter is selected via the `RC_WORKITEM_ADAPTER` environment variable:
- `robocorp_adapters_custom._sqlite.SQLiteAdapter`
- `robocorp_adapters_custom._redis.RedisAdapter`
- `robocorp_adapters_custom._docdb.DocumentDBAdapter`
- `robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter`

### Module Injection
The `__init__.py` performs module injection to provide drop-in compatibility with `robocorp.workitems`. It injects local modules (`_support`, `_types`, `_utils`) into `sys.modules` under `robocorp.workitems._adapters.*` namespaces, allowing adapters to import from `robocorp.workitems` seamlessly.

### Core Modules
- `_sqlite.py`, `_redis.py`, `_docdb.py`, `_yorko_control_room.py`: Adapter implementations
- `workitems_integration.py`: Dynamic adapter loader (`load_adapter_class`, `get_adapter_instance`)
- `_types.py`, `_utils.py`, `_support.py`: Shared utilities injected into robocorp.workitems namespace
- `exceptions.py`: Custom exception types (`AdapterError`, `DatabaseTemporarilyUnavailable`, etc.)

### Running with RCC
Tasks are defined in `yamls/robot.yaml`. Environment configs in `devdata/env-*.json`:
```bash
rcc run -t Producer -e devdata/env-sqlite-producer.json
rcc run -t Consumer -e devdata/env-sqlite-consumer.json
```

## Code Style
- Line length: 100 characters (black and ruff)
- Target Python: 3.10+
- Ruff rules: E, W, F, I, B, C4 (ignores E501, B008)
