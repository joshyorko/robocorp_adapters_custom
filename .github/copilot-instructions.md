# Robocorp Adapters Custom - AI Agent Instructions

## Project Overview
Custom work item adapters for Robocorp's workitems library, implementing pluggable backends (SQLite, Redis, Amazon DocumentDB) for producer-consumer automation workflows. All adapters implement the 9-method `BaseAdapter` interface from `robocorp.workitems._adapters._base`.

## Architecture & Core Patterns

### Adapter Pattern
Three adapters share identical interface but different storage strategies:
- **SQLiteAdapter**: File-based DB, filesystem files, WAL mode for concurrency
- **RedisAdapter**: In-memory queues, hybrid file storage (<1MB inline, >1MB disk)  
- **DocumentDBAdapter**: MongoDB-compatible, GridFS for large files, AWS TLS/SSL

**Critical**: All adapters implement these 9 methods exactly as specified in `BaseAdapter`:
```python
reserve_input() -> str                    # Atomic queue pop (BRPOPLPUSH for Redis, UPDATE...RETURNING for SQLite)
release_input(item_id, state, exception)  # Mark DONE/FAILED
create_output(parent_id, payload) -> str  # New work item in {queue}_output queue
load_payload(item_id) -> dict             # JSON deserialization
save_payload(item_id, payload)            # JSON serialization
list_files(item_id) -> list[str]
get_file(item_id, name) -> bytes
add_file(item_id, name, content)
remove_file(item_id, name)
```

### Queue Separation Strategy
**Input queue**: `{RC_WORKITEM_QUEUE_NAME}` (e.g., "qa_forms")  
**Output queue**: `{RC_WORKITEM_QUEUE_NAME}_output` (e.g., "qa_forms_output")

This prevents outputs from being immediately re-queued as inputs, matching FileAdapter behavior. See `create_output()` implementations.

### State Transitions
Internal states stored in DB:
- `PENDING` → `RESERVED` (via `reserve_input()`)
- `RESERVED` → `COMPLETED` or `FAILED` (via `release_input()`)

**Important**: Robocorp's `State.DONE` enum value is `"COMPLETED"`, not `"DONE"`. See SQLite migration v4.

### Configuration Loading
All config via environment variables (no file parsing). See `scripts/config.py`:
- Common: `RC_WORKITEM_ADAPTER`, `RC_WORKITEM_QUEUE_NAME`, `RC_WORKITEM_FILES_DIR`
- SQLite: `RC_WORKITEM_DB_PATH`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_MAX_CONNECTIONS`
- DocumentDB: `DOCDB_URI` or `DOCDB_HOSTNAME`+`DOCDB_USERNAME`+`DOCDB_PASSWORD`, `DOCDB_TLS_CERT` for AWS

## Key Implementation Details

### Database Schema Migrations (SQLiteAdapter)
Incremental migrations tracked in `schema_version` table. Current version: 4
- v1: Initial schema (work_items, work_item_files tables)
- v2: Exception tracking (exception_type, exception_code, exception_message)
- v3: Timestamps + orphan recovery index (reserved_at, released_at)
- v4: State constraint fix (DONE → COMPLETED)

Apply migrations in `_init_database()` using `apply_migration()` helper from `_utils.py`.

### Thread Safety
- **SQLiteAdapter**: Uses `ThreadLocalConnectionPool` (see `_utils.py`) + WAL mode
- **RedisAdapter**: Connection pooling via `redis.ConnectionPool`, max_connections configurable
- **DocumentDBAdapter**: PyMongo's internal pooling, replica set support

### File Storage Strategies
**SQLite**: Always filesystem (`{files_dir}/{work_item_id}/{filename}`)  
**Redis**: Hybrid - inline if <1MB, filesystem if >1MB (see `INLINE_FILE_THRESHOLD`)  
**DocumentDB**: Hybrid - inline base64 if <1MB, GridFS if >1MB (see `GRIDFS_THRESHOLD`)

### Error Handling & Retries
Use `@with_retry` decorator from `_utils.py` for transient failures:
```python
@with_retry(max_retries=3, exceptions=(sqlite3.OperationalError, DatabaseTemporarilyUnavailable))
def reserve_input(self) -> str:
    ...
```
Custom exceptions in `exceptions.py`: `AdapterError`, `DatabaseTemporarilyUnavailable`, `ConnectionPoolExhausted`

### Orphan Recovery
All adapters support recovery via `recover_orphaned_work_items()`. Items stuck in RESERVED state beyond `RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES` (default: 30) are reset to PENDING.

## Testing & Development Workflow

### Running Tasks with RCC
```bash
# Producer creates work items
rcc run -t Producer -e devdata/env-sqlite-producer.json

# Consumer processes work items
rcc run -t Consumer -e devdata/env-sqlite-consumer.json

# Reporter reads completed outputs
rcc run -t Reporter -e devdata/env-sqlite-for-reporter.json
```

Task definitions in `yamls/robot.yaml`, environment in `yamls/conda.yaml`.

### Database Seeding Scripts
```bash
python scripts/seed_sqlite_db.py                          # SQLite
python scripts/seed_redis_db.py                           # Redis
python scripts/seed_docdb_db.py                           # DocumentDB (local)
python scripts/seed_docdb_db.py --env devdata/env.json   # DocumentDB (custom config)
```

Scripts use `seed_input()` method (test helper, not in BaseAdapter interface).

### Diagnostic Scripts
- `scripts/check_sqlite_db.py`: Inspect SQLite database state
- `scripts/recover_orphaned_items.py`: Manually trigger orphan recovery
- `scripts/diagnose_reporter_issue.py`: Debug reporter problems

### Environment Files
14 pre-configured environments in `devdata/`:
- `env-{adapter}-{role}.json` pattern (e.g., `env-sqlite-producer.json`)
- Special configs: `env-redis-cluster.json`, `env-redis-sentinel.json`, `env-docdb-local-*.json`

## Code Style & Conventions

### Import Order (Robocorp-aligned)
```python
# Standard library
import json
import logging
from pathlib import Path

# Third-party
import redis
from pymongo import MongoClient

# Robocorp
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue
from robocorp.workitems._types import State

# Local
from ._utils import with_retry
from .exceptions import AdapterError
```

### Type Hints
Use Python 3.9+ style (built-in generics):
- `list[str]` not `List[str]`
- `dict[str, Any]` not `Dict[str, Any]`
- `Optional[dict]` still uses typing module

### Docstrings
- Class docstrings end with `lazydocs: ignore` to exclude from auto-docs
- Method docstrings follow Google style with Args/Returns/Raises sections
- Include environment variable references in class docstrings

### Logging
Use module-level logger:
```python
LOGGER = logging.getLogger(__name__)

LOGGER.info("Reserved work item %s from queue %s", item_id, self.queue_name)
LOGGER.error("Failed to connect: %s", e)
```

## Common Pitfalls

1. **State Enum Mismatch**: Use `State.DONE.value` which equals `"COMPLETED"`, not `"DONE"`
2. **Output Queue**: Always append `_output` to queue name in `create_output()` 
3. **File Paths**: SQLite/Redis use absolute paths from `self.files_dir`; DocumentDB uses GridFS `_id`
4. **Thread Safety**: Never share connections across threads; use `_get_connection()` pattern
5. **Empty Queue**: Must raise `EmptyQueue` exception, not return None
6. **Exception Dict**: When `state=FAILED`, exception dict must have keys: `type`, `code`, `message`

## Integration with Robocorp

### Dynamic Adapter Loading
`workitems_integration.py` provides `get_adapter_instance()` for dynamic loading:
```python
from robocorp_adapters_custom.workitems_integration import get_adapter_instance
adapter = get_adapter_instance()  # Loads from RC_WORKITEM_ADAPTER env var
```

### Upstream Contribution Path
See `docs/PR_STRATEGY.md` for planned contribution to `robocorp/robocorp`:
- Rename: `sqlite_adapter.py` → `_sqlite.py` (match Robocorp convention)
- Target location: `workitems/src/robocorp/workitems/_adapters/`
- Core adapters only (exclude scripts, devdata, yamls from PR)

## Quick Reference

**Start new adapter**: Copy `sqlite_adapter.py` structure, implement 9 BaseAdapter methods  
**Add migration**: Increment `SCHEMA_VERSION`, add `_migrate_to_vX()` method  
**Debug connection**: Check `_create_connection()` and `_get_connection()` methods  
**Test locally**: Use `devdata/env-{adapter}-{role}.json` with `rcc run`  
**Check schema**: Run `scripts/check_sqlite_db.py` or inspect Redis keys with `redis-cli KEYS '*'`

## Documentation Resources
- `docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md`: Complete implementation guide with examples
- `docs/ADAPTER_RESEARCH_SUMMARY.md`: BaseAdapter interface specification
- `docs/ROBOCORP_ALIGNMENT.md`: Code style alignment with Robocorp patterns
- `docs/PR_STRATEGY.md`: Contribution roadmap and repository structure
