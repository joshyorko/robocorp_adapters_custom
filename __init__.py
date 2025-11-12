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

import sys

__version__ = "1.0.0"

# Ensure support utilities are discoverable via robocorp.workitems namespace
from . import _support as _support_module

sys.modules.setdefault(
    "robocorp.workitems._adapters._support", _support_module
)

# T032: Export adapters from robocorp.workitems
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._types import State
from robocorp.workitems._exceptions import EmptyQueue

# Export our custom exception types
from .exceptions import (
    AdapterError,
    DatabaseTemporarilyUnavailable,
    ConnectionPoolExhausted,
    SchemaVersionMismatch,
)

from . import _sqlite as _sqlite_module

sys.modules.setdefault(
    "robocorp.workitems._adapters._sqlite", _sqlite_module
)

SQLiteAdapter = _sqlite_module.SQLiteAdapter

try:
    # RedisAdapter is optional for local/dev SQLite runs. Import lazily and
    # allow the package to be imported even when `redis` is not installed.
    from . import _redis as _redis_module  # T059
except Exception:  # pragma: no cover - optional dependency may be missing in some envs
    RedisAdapter = None
else:
    sys.modules.setdefault(
        "robocorp.workitems._adapters._redis", _redis_module
    )
    RedisAdapter = _redis_module.RedisAdapter

try:
    from . import _docdb as _docdb_module
except Exception:  # pragma: no cover - optional dependency may be missing
    DocumentDBAdapter = None
else:
    sys.modules.setdefault(
        "robocorp.workitems._adapters._docdb", _docdb_module
    )
    DocumentDBAdapter = _docdb_module.DocumentDBAdapter

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
    "DocumentDBAdapter",
    "get_adapter_instance",
    "initialize_adapter",
    "load_adapter_class",
    "is_custom_adapter_enabled",
]
