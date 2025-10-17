"""Custom exceptions for work item adapters.

This module defines custom exception types used by custom adapters.
The base adapter classes (BaseAdapter, State, etc.) are imported directly
from robocorp.workitems, not defined here.

Version: 1.0.0
Date: 2025-10-17
"""


class AdapterError(Exception):
    """Base exception for adapter-specific errors.

    Subclass this for adapter-specific error conditions:
        - DatabaseTemporarilyUnavailable
        - ConnectionPoolExhausted
        - SchemaVersionMismatch
    """

    pass


class DatabaseTemporarilyUnavailable(AdapterError):
    """Database is temporarily unavailable.

    Indicates a transient database error that may succeed if retried.
    Examples:
        - Connection timeout
        - Database locked (SQLite)
        - Network interruption
        - Too many connections

    Consumers should retry with exponential backoff.
    """

    pass


class ConnectionPoolExhausted(AdapterError):
    """Connection pool has no available connections.

    Indicates all connections in the pool are in use and max_overflow
    has been reached. This typically happens under extreme load.

    Solutions:
        - Increase pool size
        - Increase max_overflow
        - Reduce connection hold time
        - Add more workers
    """

    pass


class SchemaVersionMismatch(AdapterError):
    """Schema version is incompatible with adapter.

    Raised when the database schema version is newer than the adapter
    supports, indicating a downgrade attempt or version drift.

    Example:
        Database schema: v5
        Adapter supports: up to v3
        Result: SchemaVersionMismatch

    Solutions:
        - Upgrade adapter code
        - Run database migration
        - Use correct adapter version
    """

    pass
