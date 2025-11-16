# ![Project Logo](https://raw.githubusercontent.com/joshyorko/robocorp_adapters_custom/main/docs/logo.png)
# robocorp_adapters_custom

Custom Work Item Adapters for Robocorp Producer-Consumer Automation

---

## Overview
This repository provides custom adapters for Robocorp's workitems library, enabling scalable producer-consumer automation workflows with pluggable backend support (SQLite, Redis, Amazon DocumentDB/MongoDB, Yorko Control Room, etc.). The architecture is designed for easy backend switching via environment variables, supporting both local development and distributed cloud deployments.

## Features
- **Pluggable Adapter Pattern**: Easily switch between SQLite, Redis, Amazon DocumentDB/MongoDB, Yorko Control Room, and other backends by changing environment variables.
- **Producer-Consumer Workflows**: Modular tasks for producing, consuming, and reporting on work items.
- **Control Room Integration**: Connect robots to self-hosted Yorko Control Room via REST API.
- **Orphan Recovery**: Built-in scripts and adapter logic for recovering orphaned work items.
- **File Attachments**: Hybrid storage (inline for small files, GridFS for large files in DocumentDB, filesystem for other adapters).
- **Automatic Schema Migration**: SQLite adapter supports seamless schema upgrades.
- **Distributed Processing**: Redis and DocumentDB adapters enable high-throughput, multi-worker scaling.
- **Cloud-Native Support**: DocumentDB adapter optimized for AWS environments with TLS/SSL encryption and replica set support.

## Key Components
- `_sqlite.py`, `_redis.py`, `_docdb.py`, `_yorko_control_room.py`: Custom adapters implementing the `BaseAdapter` interface.
- `workitems_integration.py`: Dynamic adapter loader for seamless backend switching.
- `scripts/config.py`: Loads and validates environment-based configuration.
- `scripts/seed_sqlite_db.py`, `scripts/seed_redis_db.py`, `scripts/seed_docdb_db.py`: Seed scripts for populating test data.
- `yamls/robot.yaml`, `yamls/conda.yaml`: Task and environment definitions for RCC workflows.
- `devdata/`: Environment configs, input/output data, and test artifacts.
- `docs/`: Implementation guides and architecture documentation.

## Getting Started

### Quick Integration
To use these adapters in your own Robocorp project:

1. **Clone this repository** into your project or workspace.
2. **Change your adapter class name** to one of the provided adapters:
   - SQLite: `robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter`
   - Redis: `robocorp_adapters_custom.redis_adapter.RedisAdapter`
   - DocumentDB/MongoDB: `robocorp_adapters_custom.docdb_adapter.DocumentDBAdapter`
	- Set the `RC_WORKITEM_ADAPTER` environment variable accordingly.
3. **Alternatively**, use one of the pre-configured environment JSON files in `devdata/` to set all required variables for your chosen backend. Simply reference the desired file when running RCC or your robot tasks.

No code changes are required—just update your environment configuration and you're ready to go!
### 1. Environment Setup
- Clone the repository and install dependencies using the provided `conda.yaml`.
- Configure environment variables for your chosen adapter (see below).

### 2. Adapter Selection
Set the `RC_WORKITEM_ADAPTER` environment variable to select your backend:
- **SQLite**: `robocorp_adapters_custom._sqlite.SQLiteAdapter`
- **Redis**: `robocorp_adapters_custom._redis.RedisAdapter`
- **DocumentDB/MongoDB**: `robocorp_adapters_custom._docdb.DocumentDBAdapter`
- **Yorko Control Room**: `robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter`

Other required variables:
- **SQLite**: `RC_WORKITEM_DB_PATH=devdata/work_items.db`
- **Redis**: `REDIS_HOST=localhost`
- **DocumentDB**: `DOCDB_HOSTNAME=localhost`, `DOCDB_PORT=27017`, `DOCDB_USERNAME=<user>`, `DOCDB_PASSWORD=<pass>`, `DOCDB_DATABASE=<dbname>`
  - For AWS DocumentDB: Also set `DOCDB_TLS_CERT=<path/to/rds-combined-ca-bundle.pem>`
  - Alternatively, use: `DOCDB_URI=mongodb://<user>:<pass>@<host>:<port>/?ssl=true`
- **Yorko Control Room**: `YORKO_API_URL=http://localhost:8000`, `YORKO_API_TOKEN=<token>`, `YORKO_WORKSPACE_ID=<uuid>`, `YORKO_WORKER_ID=<worker-id>`

### 3. Running Tasks
Use RCC or the `robot.yaml` tasks:

**SQLite:**
```sh
rcc run -t Producer -e devdata/env-sqlite-producer.json
rcc run -t Consumer -e devdata/env-sqlite-consumer.json
rcc run -t Reporter -e devdata/env-sqlite-for-reporter.json
```

**Redis:**
```sh
rcc run -t Producer -e devdata/env-redis-producer.json
rcc run -t Consumer -e devdata/env-redis-consumer.json
rcc run -t Reporter -e devdata/env-redis-reporter.json
```

**DocumentDB/MongoDB:**
```sh
rcc run -t Producer -e devdata/env-docdb-local-producer.json
rcc run -t Consumer -e devdata/env-docdb-local-consumer.json
rcc run -t Reporter -e devdata/env-docdb-local-reporter.json
```

**Yorko Control Room:**
```sh
rcc run -t Producer -e devdata/env-yorko-control-room-producer.json
rcc run -t Consumer -e devdata/env-yorko-control-room-consumer.json
```
See [Yorko Control Room Adapter Guide](docs/YORKO_CONTROL_ROOM_ADAPTER.md) for detailed setup.

### 4. Seeding and Debugging
- Seed SQLite: `python scripts/seed_sqlite_db.py`
- Seed Redis: `python scripts/seed_redis_db.py`
- Seed DocumentDB: `python scripts/seed_docdb_db.py` (or with custom env: `python scripts/seed_docdb_db.py --env devdata/env-docdb-local-producer.json`)
- Check DB: `python scripts/check_sqlite_db.py`
- Recover Orphans: `python scripts/recover_orphaned_items.py`
- Diagnose Reporter: `python scripts/diagnose_reporter_issue.py`

## Project Conventions
- All configuration is via environment variables (see `scripts/config.py`).
- Queue names are set by `RC_WORKITEM_QUEUE_NAME`.
- File attachments:
  - SQLite/Redis: Large files stored on disk, small files inline
  - DocumentDB: Large files stored in GridFS (>1MB), small files inline (base64)
- Adapters must implement 9 methods (see `docs/ADAPTER_RESEARCH_SUMMARY.md`).
- Switching backends requires only env var changes—no code changes.

## Adapter Comparison

| Feature | SQLite | Redis | DocumentDB/MongoDB |
|---------|--------|-------|-------------------|
| **Best For** | Local development, single-worker | High-throughput, multi-worker | AWS-native, distributed processing |
| **Scalability** | Single process | Horizontal scaling | Horizontal scaling with replica sets |
| **Persistence** | File-based | In-memory (optional persistence) | Durable, replicated storage |
| **File Storage** | Filesystem | Filesystem | GridFS (integrated) |
| **Cloud Integration** | N/A | ElastiCache support | Native AWS DocumentDB |
| **TLS/SSL** | N/A | Supported | Required for AWS DocumentDB |
| **Setup Complexity** | Low | Medium | Medium-High |
| **Dependencies** | None (stdlib) | `redis-py` | `pymongo` |

### When to Use DocumentDB/MongoDB Adapter
- **AWS Environments**: Native integration with Amazon DocumentDB clusters
- **Multi-Region Deployments**: Replica set support for high availability
- **Large File Handling**: Built-in GridFS for efficient large file storage (>1MB)
- **Enterprise Features**: TLS/SSL encryption, connection pooling, and automatic failover
- **MongoDB Compatibility**: Drop-in replacement for existing MongoDB-based workflows

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
