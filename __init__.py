"""Custom Work Item Adapters for Robocorp Producer-Consumer Automation.

This package provides custom adapters for the Robocorp workitems library, enabling
scalable producer-consumer automation workflows with pluggable backend support.

Supported Adapters:
    - SQLiteAdapter: Local/embedded database backend
    - RedisAdapter: Distributed Redis backend with clustering support
    - DocumentDBAdapter: AWS DocumentDB/MongoDB backend
    - YorkoControlRoomAdapter: HTTP REST API adapter for Yorko Control Room

Usage:
    Set RC_WORKITEM_ADAPTER environment variable to select your backend:
    - robocorp_adapters_custom._sqlite.SQLiteAdapter
    - robocorp_adapters_custom._redis.RedisAdapter
    - robocorp_adapters_custom._docdb.DocumentDBAdapter
    - robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter
"""

__version__ = "0.1.0"

__all__ = [
    "exceptions",
    "workitems_integration",
]

# ruff: noqa: E402
# Note: Module-level imports must occur after attribute injection to ensure
# drop-in compatibility with robocorp.workitems package

import sys

__version__ = "1.0.0"

# Inject our local utilities into robocorp.workitems modules to enable drop-in compatibility
# This allows adapters to work seamlessly with the existing robocorp.workitems package

# Import robocorp.workitems modules first to ensure they're loaded
try:
    from robocorp.workitems import _types as robocorp_types
    from robocorp.workitems import _utils as robocorp_utils
    from robocorp.workitems._adapters import _base as robocorp_base
except ImportError:
    # If robocorp.workitems is not installed, that's fine - adapters will use local modules
    robocorp_types = None
    robocorp_utils = None
    robocorp_base = None

# Import our local modules
from . import _support as _support_module
from . import _types as _types_module
from . import _utils as _utils_module

# Inject missing attributes into robocorp.workitems modules if they exist
if robocorp_types is not None:
    # Add TTL_WEEK_SECONDS to robocorp.workitems._types if missing
    if not hasattr(robocorp_types, 'TTL_WEEK_SECONDS'):
        robocorp_types.TTL_WEEK_SECONDS = _types_module.TTL_WEEK_SECONDS
        
if robocorp_utils is not None:
    # Add JSONType and required_env to robocorp.workitems._utils if missing
    if not hasattr(robocorp_utils, 'JSONType'):
        robocorp_utils.JSONType = _utils_module.JSONType
    if not hasattr(robocorp_utils, 'required_env'):
        robocorp_utils.required_env = _utils_module.required_env

# Map our _support module to robocorp.workitems._adapters._support
sys.modules.setdefault(
    "robocorp.workitems._adapters._support", _support_module
)

# Also provide fallback mappings for our local modules
sys.modules.setdefault(
    "robocorp.workitems._types", _types_module
)
sys.modules.setdefault(
    "robocorp.workitems._utils", _utils_module
)

# T032: Export adapters from robocorp.workitems
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue

# Import State from our local _types module
from ._types import State

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
