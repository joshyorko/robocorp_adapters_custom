# Copilot Coding Agent Instructions for robocorp_adapters_custom

## Project Overview
This repo implements custom work item adapters for Robocorp's producer-consumer automation workflows. Adapters allow integration with various backends (SQLite, Redis, PostgreSQL) for scalable queue management. The architecture is designed for plug-and-play backend switching via environment variables.

## Key Components
- **Adapters**: `sqlite_adapter.py`, `redis_adapter.py` (implement `BaseAdapter` interface)
- **Integration**: `workitems_integration.py` (dynamic adapter loading)
- **Config**: `scripts/config.py` (loads env vars for adapter selection)
- **Seeding Scripts**: `scripts/seed_sqlite_db.py`, `scripts/seed_redis_db.py` (populate test data)
- **YAMLs**: `yamls/robot.yaml`, `yamls/conda.yaml` (task and environment definitions)
- **Devdata**: `devdata/` (env configs, input/output data)

## Adapter Pattern
- All adapters inherit from `BaseAdapter` and must implement 9 methods (see `docs/ADAPTER_RESEARCH_SUMMARY.md`).
- Adapter selection is controlled by the `RC_WORKITEM_ADAPTER` env var (full class path).
- Example: `robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter` or `robocorp_adapters_custom.redis_adapter.RedisAdapter`

## Developer Workflows
- **Run tasks**: Use RCC or `robot.yaml` tasks (Producer, Consumer, Reporter)
- **Seed DB**: `python scripts/seed_sqlite_db.py` or `python scripts/seed_redis_db.py` (see devTasks in `robot.yaml`)
- **Check DB**: `python scripts/check_sqlite_db.py`
- **Recover Orphans**: `python scripts/recover_orphaned_items.py`
- **Diagnose Issues**: `python scripts/diagnose_reporter_issue.py`

## Environment Setup
- All configuration is via environment variables (see `scripts/config.py`).
- Example for SQLite:
  ```sh
  export RC_WORKITEM_ADAPTER=robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter
  export RC_WORKITEM_DB_PATH=devdata/work_items.db
  rcc run -t Producer -e devdata/env-sqlite-producer.json
  ```
- Example for Redis:
  ```sh
  export RC_WORKITEM_ADAPTER=robocorp_adapters_custom.redis_adapter.RedisAdapter
  export REDIS_HOST=localhost
  rcc run -t Producer -e devdata/env-redis-producer.json
  ```

## Project Conventions
- **File attachments**: Large files stored on disk, small files inline (see adapter docs)
- **Queue names**: Controlled by `RC_WORKITEM_QUEUE_NAME` env var
- **Orphan recovery**: Built-in to adapters and via scripts
- **Testing**: Seed scripts and devTasks provide test data and DB state

## Integration Points
- Adapters integrate with Robocorp's `robocorp-workitems` library
- Producer/Consumer workflows are orchestrated via RCC subprocess calls (see docs/# Producer-Consumer Architecture Migrati.md)
- All adapter logic is backend-agnostic; switching adapters requires only env var changes

## References
- See `docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md` and `docs/ADAPTER_RESEARCH_SUMMARY.md` for adapter implementation details
- See `yamls/robot.yaml` for task definitions and dev workflows
- See `scripts/config.py` for environment variable conventions

---
**Tip:** Always check the relevant YAML and devdata files for environment setup and test data before running tasks or debugging issues.
