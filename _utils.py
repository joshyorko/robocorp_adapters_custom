"""Shared utility functions for custom adapters.

This module provides:
- Connection pooling utilities
- Retry logic with exponential backoff
- Schema migration helpers
- Environment variable utilities
- Type aliases
"""

import functools
import logging
import os
import random
import threading
import time
from typing import Callable, Any, TypeVar

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")

# Type alias for JSON-serializable data (matches robocorp.workitems._utils.JSONType)
JSONType = dict[str, Any] | list | str | int | float | bool | None


def required_env(key: str) -> str:
    """Get required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        KeyError: If environment variable is not set
        
    Example:
        db_path = required_env("RC_WORKITEM_DB_PATH")
    """
    value = os.getenv(key)
    if value is None:
        raise KeyError(
            f"Required environment variable '{key}' is not set. "
            f"Please set it before using this adapter."
        )
    return value


# T009: Connection pooling utility functions
class ThreadLocalConnectionPool:
    """Thread-local connection manager for SQLite.

    SQLite connections cannot be shared across threads. This manager
    ensures each thread gets its own connection instance.

    Usage:
        pool = ThreadLocalConnectionPool(connection_factory)
        conn = pool.get_connection()
    """

    def __init__(self, connection_factory: Callable[[], Any]):
        """Initialize thread-local connection pool.

        Args:
            connection_factory: Function that creates new connections
        """
        self._local = threading.local()
        self._connection_factory = connection_factory

    def get_connection(self) -> Any:
        """Get connection for current thread.

        Returns:
            Connection instance (thread-local)
        """
        if not hasattr(self._local, "connection"):
            self._local.connection = self._connection_factory()
            LOGGER.debug(
                "Created new connection for thread %s", threading.current_thread().name
            )
        return self._local.connection

    def close_all(self):
        """Close connection for current thread (if exists)."""
        if hasattr(self._local, "connection"):
            try:
                self._local.connection.close()
                LOGGER.debug(
                    "Closed connection for thread %s", threading.current_thread().name
                )
            except Exception as e:
                LOGGER.warning("Error closing connection: %s", e)
            finally:
                delattr(self._local, "connection")


# T010: Exponential backoff retry decorator
def with_retry(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
    exponential_base: int = 2,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 0.1)
        max_delay: Maximum delay in seconds (default: 10.0)
        exponential_base: Base for exponential calculation (default: 2)
        exceptions: Tuple of exception types to retry (default: all exceptions)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_retries=3, base_delay=0.1)
        def unstable_operation():
            # May fail temporarily
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        # Final attempt failed, re-raise
                        LOGGER.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries,
                            e,
                        )
                        raise

                    # Calculate delay with exponential backoff + jitter
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    jitter = random.uniform(0, 0.1 * delay)
                    total_delay = delay + jitter

                    LOGGER.warning(
                        "Function %s attempt %d/%d failed: %s. Retrying in %.2fs",
                        func.__name__,
                        attempt + 1,
                        max_retries,
                        e,
                        total_delay,
                    )
                    time.sleep(total_delay)

            # Should never reach here, but mypy requires return
            raise RuntimeError(f"{func.__name__} exhausted all retries")

        return wrapper

    return decorator


# T013: Migration utility functions
def detect_schema_version(conn: Any, version_table: str = "schema_version") -> int:
    """Detect current schema version from database.

    Args:
        conn: Database connection
        version_table: Name of version tracking table

    Returns:
        Current schema version (0 if no version table exists)
    """
    try:
        cursor = conn.execute(f"SELECT MAX(version) FROM {version_table}")
        result = cursor.fetchone()
        version = result[0] if result and result[0] is not None else 0
        LOGGER.info("Detected schema version: %d", version)
        return version
    except Exception as e:
        LOGGER.info("No schema version table found, assuming version 0: %s", e)
        return 0


def apply_migration(
    conn: Any,
    target_version: int,
    migration_func: Callable[[Any], None],
    version_table: str = "schema_version",
):
    """Apply a schema migration within a transaction.

    Args:
        conn: Database connection
        target_version: Version number being migrated to
        migration_func: Function that performs migration (takes connection)
        version_table: Name of version tracking table

    Raises:
        Exception: If migration fails (transaction rolled back)
    """
    try:
        LOGGER.info("Applying migration to version %d", target_version)

        # Execute migration
        migration_func(conn)

        # Record version
        conn.execute(
            f"INSERT INTO {version_table} (version, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
            (target_version,),
        )

        conn.commit()
        LOGGER.info("Successfully migrated to version %d", target_version)
    except Exception as e:
        LOGGER.error("Migration to version %d failed: %s", target_version, e)
        conn.rollback()
        raise


def run_migrations(
    conn: Any,
    current_version: int,
    target_version: int,
    migration_functions: dict[int, Callable[[Any], None]],
    version_table: str = "schema_version",
):
    """Run all pending migrations from current to target version.

    Args:
        conn: Database connection
        current_version: Current schema version
        target_version: Target schema version
        migration_functions: Dict mapping version -> migration function
        version_table: Name of version tracking table

    Example:
        migrations = {
            1: _migrate_to_v1,
            2: _migrate_to_v2,
            3: _migrate_to_v3
        }
        run_migrations(conn, 0, 3, migrations)
    """
    if current_version >= target_version:
        LOGGER.info("Schema is up to date (version %d)", current_version)
        return

    LOGGER.info(
        "Running migrations from version %d to %d", current_version, target_version
    )

    for version in range(current_version + 1, target_version + 1):
        if version not in migration_functions:
            raise ValueError(f"No migration function defined for version {version}")

        apply_migration(conn, version, migration_functions[version], version_table)

    LOGGER.info("All migrations completed successfully")
