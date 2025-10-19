"""Custom work item adapters for Robocorp workitems library.

This package provides open-source database-backed adapters compatible with
robocorp-workitems>=1.4.7 as alternatives to proprietary Robocorp Control Room.

Available adapters:
- SQLiteAdapter: Local development and small-scale deployments
- RedisAdapter: Distributed processing with high throughput
- PostgresAdapter: Enterprise production with ACID compliance

Usage:
    Configure adapter via environment variable RC_WORKITEM_ADAPTER:
    export RC_WORKITEM_ADAPTER="robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter"

See quickstart.md for setup guides.
"""

__version__ = "1.0.0"

# T032: Export adapters from robocorp.workitems
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._types import State
from robocorp.workitems._exceptions import EmptyQueue

# Export our custom exception types
from .exceptions import AdapterError, DatabaseTemporarilyUnavailable, ConnectionPoolExhausted, SchemaVersionMismatch

from .sqlite_adapter import SQLiteAdapter
try:
    # RedisAdapter is optional for local/dev SQLite runs. Import lazily and
    # allow the package to be imported even when `redis` is not installed.
    from .redis_adapter import RedisAdapter  # T059
except Exception:  # pragma: no cover - optional dependency may be missing in some envs
    RedisAdapter = None

# T038-T040: Export adapter integration utilities
from .workitems_integration import (
    get_adapter_instance,
    initialize_adapter,
    load_adapter_class,
    is_custom_adapter_enabled,
)

__all__ = [
    "BaseAdapter",
    "State",
    "EmptyQueue",
    "AdapterError",
    "DatabaseTemporarilyUnavailable",
    "ConnectionPoolExhausted",
    "SchemaVersionMismatch",
    "SQLiteAdapter",
    "RedisAdapter",  # T059 (may be None if redis is not installed)
    "get_adapter_instance",
    "initialize_adapter",
    "load_adapter_class",
    "is_custom_adapter_enabled",
]
