# ![Project Logo](docs/logo.png)
# robocorp_adapters_custom

Custom Work Item Adapters for Robocorp Producer-Consumer Automation

---

## Overview
This repository provides custom adapters for Robocorp's workitems library, enabling scalable producer-consumer automation workflows with pluggable backend support (SQLite, Redis, PostgreSQL, etc.). The architecture is designed for easy backend switching via environment variables, supporting both local development and distributed production deployments.

## Features
- **Pluggable Adapter Pattern**: Easily switch between SQLite, Redis, and other backends by changing environment variables.
- **Producer-Consumer Workflows**: Modular tasks for producing, consuming, and reporting on work items.
- **Orphan Recovery**: Built-in scripts and adapter logic for recovering orphaned work items.
- **File Attachments**: Hybrid storage (inline for small files, filesystem for large files).
- **Automatic Schema Migration**: SQLite adapter supports seamless schema upgrades.
- **Distributed Processing**: Redis adapter enables high-throughput, multi-worker scaling.

## Key Components
- `sqlite_adapter.py`, `redis_adapter.py`: Custom adapters implementing the `BaseAdapter` interface.
- `workitems_integration.py`: Dynamic adapter loader for seamless backend switching.
- `scripts/config.py`: Loads and validates environment-based configuration.
- `scripts/seed_sqlite_db.py`, `scripts/seed_redis_db.py`: Seed scripts for populating test data.
- `yamls/robot.yaml`, `yamls/conda.yaml`: Task and environment definitions for RCC workflows.
- `devdata/`: Environment configs, input/output data, and test artifacts.
- `docs/`: Implementation guides and architecture documentation.

## Getting Started

### Quick Integration
To use these adapters in your own Robocorp project:

1. **Clone this repository** into your project or workspace.
2. **Change your adapter class name** to one of the provided adapters (e.g., `robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter` or `robocorp_adapters_custom.redis_adapter.RedisAdapter`).
	- Set the `RC_WORKITEM_ADAPTER` environment variable accordingly.
3. **Alternatively**, use one of the pre-configured environment JSON files in `devdata/` to set all required variables for SQLite or Redis. Simply reference the desired file when running RCC or your robot tasks.

No code changes are required—just update your environment configuration and you're ready to go!
### 1. Environment Setup
- Clone the repository and install dependencies using the provided `conda.yaml`.
- Configure environment variables for your chosen adapter (see below).

### 2. Adapter Selection
Set the `RC_WORKITEM_ADAPTER` environment variable to select your backend:
- SQLite: `robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter`
- Redis: `robocorp_adapters_custom.redis_adapter.RedisAdapter`

Other required variables:
- SQLite: `RC_WORKITEM_DB_PATH=devdata/work_items.db`
- Redis: `REDIS_HOST=localhost`

### 3. Running Tasks
Use RCC or the `robot.yaml` tasks:
```sh
rcc run -t Producer -e devdata/env-sqlite-producer.json
rcc run -t Consumer -e devdata/env-sqlite-consumer.json
rcc run -t Reporter -e devdata/env-sqlite-for-reporter.json
```
Or for Redis:
```sh
rcc run -t Producer -e devdata/env-redis-producer.json
rcc run -t Consumer -e devdata/env-redis-consumer.json
```

### 4. Seeding and Debugging
- Seed SQLite: `python scripts/seed_sqlite_db.py`
- Seed Redis: `python scripts/seed_redis_db.py`
- Check DB: `python scripts/check_sqlite_db.py`
- Recover Orphans: `python scripts/recover_orphaned_items.py`
- Diagnose Reporter: `python scripts/diagnose_reporter_issue.py`

## Project Conventions
- All configuration is via environment variables (see `scripts/config.py`).
- Queue names are set by `RC_WORKITEM_QUEUE_NAME`.
- File attachments: Large files stored on disk, small files inline.
- Adapters must implement 9 methods (see `docs/ADAPTER_RESEARCH_SUMMARY.md`).
- Switching backends requires only env var changes—no code changes.

## References & Documentation
- Adapter implementation: `docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md`
- Adapter interface: `docs/ADAPTER_RESEARCH_SUMMARY.md`
- Producer-consumer architecture: `docs/# Producer-Consumer Architecture Migrati.md`
- Task definitions: `yamls/robot.yaml`
- Environment setup: `yamls/conda.yaml`, `devdata/`

## License
[MIT](LICENSE) (or project-specific license)

---
**Tip:** Always check the relevant YAML and devdata files for environment setup and test data before running tasks or debugging issues.
