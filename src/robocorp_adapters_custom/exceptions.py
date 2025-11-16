"""Custom exceptions for work item adapters.

This module defines custom exception types used by custom adapters.
These exceptions extend the base exception types from robocorp.workitems
to provide adapter-specific error handling.
"""


class AdapterError(RuntimeError):
    """Base exception for adapter-specific errors.

    Follows Robocorp's pattern of inheriting from RuntimeError for
    library-specific exceptions that indicate programming errors or
    unexpected runtime conditions.

    Subclass this for adapter-specific error conditions:
        - DatabaseTemporarilyUnavailable
        - ConnectionPoolExhausted
        - SchemaVersionMismatch
    """


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
