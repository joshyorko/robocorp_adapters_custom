"""SQLite-based work item adapter.

This module implements a custom work item adapter using SQLite as the backend.
Perfect for local development and small-scale deployments.

Features:
- ACID transactions
- Concurrent read access (WAL mode)
- Filesystem-based file storage
- Automatic schema migrations
- Orphaned work item recovery

Usage:
    from custom_adapters.sqlite_adapter import SQLiteAdapter

    adapter = SQLiteAdapter()
    item_id = adapter.reserve_input()
    payload = adapter.load_payload(item_id)
    # Process work item...
    adapter.release_input(item_id, State.DONE)
"""

import json
import logging
import os
import sqlite3
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

# Import from robocorp.workitems for proper integration
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType
from robocorp.workitems._exceptions import EmptyQueue

from .exceptions import DatabaseTemporarilyUnavailable
from ._utils import (
    ThreadLocalConnectionPool,
    with_retry,
    detect_schema_version,
    apply_migration,
)

LOGGER = logging.getLogger(__name__)

# Current schema version
SCHEMA_VERSION = 4


class ProcessingState(str, Enum):
    """Lifecycle states persisted in the SQLite work_items table."""

    PENDING = "PENDING"
    RESERVED = "RESERVED"
    COMPLETED = State.DONE.value
    FAILED = State.FAILED.value


_STATE_VALUES = (
    ProcessingState.PENDING.value,
    ProcessingState.RESERVED.value,
    ProcessingState.COMPLETED.value,
    ProcessingState.FAILED.value,
)

_STATE_VALUES_FOR_CHECK = ", ".join(f"'{value}'" for value in _STATE_VALUES)


class SQLiteAdapter(BaseAdapter):
    """SQLite-based work item adapter.

    This adapter stores work items in a SQLite database with support for:
    - Atomic work item reservation (PENDING → RESERVED)
    - State transitions (RESERVED → COMPLETED/FAILED)
    - JSON payload storage
    - File attachments (filesystem)
    - Automatic schema migrations
    - Orphaned work item recovery

    Environment Variables:
        RC_WORKITEM_DB_PATH: Path to SQLite database file (required)
        RC_WORKITEM_FILES_DIR: Directory for file attachments (default: devdata/work_item_files)
        RC_WORKITEM_QUEUE_NAME: Queue identifier (default: default)
        RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES: Orphan timeout (default: 30)
    """

    def __init__(self):
        """Initialize SQLite adapter.

        Loads configuration from environment variables, initializes database
        schema, and sets up connection pool.

        Raises:
            ValueError: If required configuration is missing
        """
        # T014: Load configuration
        self.db_path = os.getenv("RC_WORKITEM_DB_PATH")
        if not self.db_path:
            raise ValueError(
                "RC_WORKITEM_DB_PATH environment variable is required. "
                "Example: devdata/work_items.db"
            )

        self.files_dir = Path(os.getenv("RC_WORKITEM_FILES_DIR", "devdata/work_item_files"))
        self.queue_name = os.getenv("RC_WORKITEM_QUEUE_NAME", "default")
        self.orphan_timeout_minutes = int(os.getenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "30"))

        # Create directories
        self.files_dir.mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection pool
        self._pool = ThreadLocalConnectionPool(self._create_connection)

        # Initialize database schema
        self._init_database()

        LOGGER.info(
            "SQLiteAdapter initialized: db=%s, queue=%s, files_dir=%s",
            self.db_path, self.queue_name, self.files_dir
        )

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimized settings.

        Returns:
            sqlite3.Connection: Configured connection
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # T015: Configure WAL mode and optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")

        return conn

    # T016: Connection management
    def _get_connection(self) -> sqlite3.Connection:
        """Get connection for current thread.

        Returns:
            sqlite3.Connection: Thread-local connection
        """
        return self._pool.get_connection()

    # T015: Database initialization
    def _init_database(self):
        """Initialize database schema with migrations.

        Creates version table and applies all pending migrations.
        """
        conn = self._get_connection()

        # Create version table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Detect current version
        current_version = detect_schema_version(conn)

        # Check for version mismatch
        if current_version > SCHEMA_VERSION:
            raise ValueError(
                f"Database schema version ({current_version}) is newer than "
                f"adapter supports ({SCHEMA_VERSION}). Please upgrade adapter."
            )

        # Apply migrations
        migrations = {
            1: self._migrate_to_v1,
            2: self._migrate_to_v2,
            3: self._migrate_to_v3,
            4: self._migrate_to_v4,
        }

        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            LOGGER.info("Applying migration to version %d", version)
            apply_migration(conn, version, migrations[version])

        LOGGER.info("Database schema initialized (version %d)", SCHEMA_VERSION)

    # T017: Migration v1 - Initial schema
    def _migrate_to_v1(self, conn: sqlite3.Connection):
        """Migration v1: Create initial schema.

        Creates work_items table with:
        - id: Primary key (UUID)
        - queue_name: Queue identifier
        - parent_id: Parent work item ID (for outputs)
        - payload: JSON data (stored as TEXT)
        - state: Processing state (PENDING/RESERVED/COMPLETED/FAILED)
        - created_at: Creation timestamp
        """
        conn.execute(f"""
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                parent_id TEXT,
                payload TEXT,
                state TEXT DEFAULT '{ProcessingState.PENDING.value}' CHECK(state IN ({_STATE_VALUES_FOR_CHECK})),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES work_items(id)
            )
        """)

        conn.execute("""
            CREATE INDEX idx_queue_state ON work_items(queue_name, state, created_at)
        """)

        conn.execute("""
            CREATE INDEX idx_parent ON work_items(parent_id)
        """)

        conn.execute("""
            CREATE TABLE work_item_files (
                work_item_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (work_item_id, filename),
                FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE
            )
        """)

        LOGGER.info("Created initial schema (v1)")

    # T018: Migration v2 - Add exception tracking
    def _migrate_to_v2(self, conn: sqlite3.Connection):
        """Migration v2: Add exception tracking fields.

        Adds fields to record exceptions when work items fail:
        - exception_type: Exception class name
        - exception_code: Error code
        - exception_message: Error description
        """
        conn.execute("ALTER TABLE work_items ADD COLUMN exception_type TEXT")
        conn.execute("ALTER TABLE work_items ADD COLUMN exception_code TEXT")
        conn.execute("ALTER TABLE work_items ADD COLUMN exception_message TEXT")

        LOGGER.info("Added exception tracking fields (v2)")

    # T019: Migration v3 - Add timestamp fields
    def _migrate_to_v3(self, conn: sqlite3.Connection):
        """Migration v3: Add timestamp fields for orphan recovery.

        Adds timestamp fields to track work item lifecycle:
        - reserved_at: When work item was reserved
        - released_at: When work item was released (completed/failed)

        These enable orphaned work item detection and recovery.
        """
        conn.execute("ALTER TABLE work_items ADD COLUMN reserved_at TIMESTAMP")
        conn.execute("ALTER TABLE work_items ADD COLUMN released_at TIMESTAMP")

        # T029: Add partial index for orphan recovery queries
        conn.execute(f"""
            CREATE INDEX idx_orphan_check
            ON work_items(state, reserved_at)
            WHERE state='{ProcessingState.RESERVED.value}'
        """)

        LOGGER.info("Added timestamp fields and orphan index (v3)")

    # T020: Migration v4 - Update state constraint to use COMPLETED instead of DONE
    def _migrate_to_v4(self, conn: sqlite3.Connection):
        """Migration v4: Change state CHECK constraint from DONE to COMPLETED.

        Robocorp's State.DONE enum value is 'COMPLETED', not 'DONE'.
        This migration updates the CHECK constraint to match.

        Since SQLite doesn't support ALTER CONSTRAINT, we recreate the table.
        """
        # Create new table with updated constraint
        conn.execute(f"""
            CREATE TABLE work_items_new (
                id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                parent_id TEXT,
                payload TEXT,
                state TEXT DEFAULT '{ProcessingState.PENDING.value}' CHECK(state IN ({_STATE_VALUES_FOR_CHECK})),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exception_type TEXT,
                exception_code TEXT,
                exception_message TEXT,
                reserved_at TIMESTAMP,
                released_at TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES work_items_new(id)
            )
        """)

        # Copy data, mapping DONE -> COMPLETED
        conn.execute("""
            INSERT INTO work_items_new
            SELECT id, queue_name, parent_id, payload,
                   CASE WHEN state = 'DONE' THEN 'COMPLETED' ELSE state END,
                   created_at, exception_type, exception_code, exception_message,
                   reserved_at, released_at
            FROM work_items
        """)

        # Drop old indexes first (they reference the old table)
        conn.execute("DROP INDEX IF EXISTS idx_queue_state")
        conn.execute("DROP INDEX IF EXISTS idx_parent")
        conn.execute("DROP INDEX IF EXISTS idx_orphan_check")

        # Drop old table
        conn.execute("DROP TABLE work_items")

        # Rename new table
        conn.execute("ALTER TABLE work_items_new RENAME TO work_items")

        # Create indexes on new table
        conn.execute("""
            CREATE INDEX idx_queue_state ON work_items(queue_name, state, created_at)
        """)
        conn.execute("""
            CREATE INDEX idx_parent ON work_items(parent_id)
        """)
        conn.execute(f"""
            CREATE INDEX idx_orphan_check
            ON work_items(state, reserved_at)
            WHERE state='{ProcessingState.RESERVED.value}'
        """)

        LOGGER.info("Updated state constraint from DONE to COMPLETED (v4)")

    # T020: Reserve input work item
    @with_retry(max_retries=3, exceptions=(sqlite3.OperationalError, DatabaseTemporarilyUnavailable))
    def reserve_input(self) -> str:
        """Reserve next pending work item from queue.

        Atomically reserves the oldest PENDING work item using UPDATE...RETURNING.
        Updates state to RESERVED and sets reserved_at timestamp.

        Returns:
            str: Work item ID (UUID)

        Raises:
            EmptyQueue: If no pending work items available
            DatabaseTemporarilyUnavailable: If database is temporarily locked
        """
        conn = self._get_connection()

        try:
            LOGGER.info(
                "Reserving next input work item from SQLite queue: %s",
                self.queue_name,
            )
            # Atomic reservation with RETURNING clause
            cursor = conn.execute("""
                UPDATE work_items
                SET state = ?,
                    reserved_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM work_items
                    WHERE queue_name = ? AND state = ?
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING id
            """, (
                ProcessingState.RESERVED.value,
                self.queue_name,
                ProcessingState.PENDING.value,
            ))

            result = cursor.fetchone()
            conn.commit()

            if not result:
                raise EmptyQueue(f"No pending work items in queue: {self.queue_name}")

            item_id = result[0]
            LOGGER.info(
                "Reserved input work item %s from queue %s",
                item_id,
                self.queue_name,
            )
            return item_id

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                LOGGER.warning("Database locked, retrying: %s", e)
                raise DatabaseTemporarilyUnavailable(f"Database locked: {e}") from e
            raise

    # T021: Release work item
    def release_input(
        self,
        item_id: str,
        state: State,
        exception: Optional[dict] = None,
    ):
        """Release work item with terminal state.

        Updates work item state to COMPLETED or FAILED and records exception details if failed.

        Args:
            item_id: Work item ID
            state: Terminal state (State.DONE or State.FAILED)
            exception: Exception details dict with keys: type, code, message

        Raises:
            ValueError: If state is not terminal or exception details missing for FAILED state
        """
        if state not in (State.DONE, State.FAILED):
            raise ValueError(f"Release state must be DONE or FAILED, got {state}")

        # Extract exception details from dict
        exception_type = None
        exception_code = None
        exception_message = None

        if exception:
            exception_type = exception.get("type")
            exception_code = exception.get("code")
            exception_message = exception.get("message")

        if state == State.FAILED and not exception_message:
            raise ValueError("exception['message'] required when state=FAILED")

        conn = self._get_connection()

        conn.execute("""
            UPDATE work_items
            SET state = ?,
                released_at = CURRENT_TIMESTAMP,
                exception_type = ?,
                exception_code = ?,
                exception_message = ?
            WHERE id = ?
        """, (state.value, exception_type, exception_code, exception_message, item_id))

        conn.commit()

        log_func = LOGGER.error if state == State.FAILED else LOGGER.info
        log_func(
            "Releasing %s work item %s on queue %s with exception: %s",
            state.value,
            item_id,
            self.queue_name,
            exception,
        )

    # T022: Create output work item
    def create_output(
        self,
        parent_id: Optional[str],
        payload: Optional[dict] = None,
    ) -> str:
        """Create new output work item.

        Creates a work item in PENDING state with optional payload in a separate output queue.
        This prevents outputs from being immediately re-queued as inputs, matching FileAdapter behavior.

        Output Queue Strategy:
            - Input queue: {queue_name} (e.g., "qa_forms")
            - Output queue: {queue_name}_output (e.g., "qa_forms_output")
            - Outputs go to the output queue and are NOT reserved by reserve_input()
            - Reporter or next stage can consume from the output queue

        Args:
            parent_id: Parent work item ID (None for root items)
            payload: JSON payload data (default: empty dict)

        Returns:
            str: New work item ID (UUID)
        """
        item_id = str(uuid.uuid4())
        payload_json = json.dumps(payload or {})

        # Output queue name = input queue + "_output"
        output_queue = f"{self.queue_name}_output"

        LOGGER.info(
            "Creating SQLite output work item for parent %s in queue %s",
            parent_id or "None",
            output_queue,
        )

        conn = self._get_connection()

        conn.execute("""
            INSERT INTO work_items (id, queue_name, parent_id, payload, state, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (item_id, output_queue, parent_id, payload_json, ProcessingState.PENDING.value))

        conn.commit()

        LOGGER.info(
            "Created SQLite output work item %s in queue %s",
            item_id,
            output_queue,
        )

        return item_id

    # T023: Load payload
    def load_payload(self, item_id: str) -> dict:
        """Load JSON payload from work item.

        Args:
            item_id: Work item ID

        Returns:
            dict: JSON payload data

        Raises:
            ValueError: If work item not found
        """
        conn = self._get_connection()

        LOGGER.info("Loading work item payload from SQLite for: %s", item_id)
        cursor = conn.execute("SELECT payload FROM work_items WHERE id = ?", (item_id,))
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"Work item not found: {item_id}")

        payload = json.loads(result[0] or "{}")
        LOGGER.debug("Loaded payload for work item: %s", item_id)
        return payload

    # T024: Save payload
    def save_payload(self, item_id: str, payload: dict):
        """Save JSON payload to work item.

        Args:
            item_id: Work item ID
            payload: JSON payload data

        Raises:
            ValueError: If work item not found
        """
        payload_json = json.dumps(payload)

        conn = self._get_connection()

        LOGGER.info("Saving work item payload to SQLite for: %s", item_id)
        cursor = conn.execute(
            "UPDATE work_items SET payload = ? WHERE id = ?",
            (payload_json, item_id)
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Work item not found: {item_id}")

        conn.commit()
        LOGGER.debug("Saved payload for work item: %s", item_id)

    # T025: List files
    def list_files(self, item_id: str) -> list[str]:
        """List file attachments for work item.

        Args:
            item_id: Work item ID

        Returns:
            list[str]: List of filenames
        """
        conn = self._get_connection()

        LOGGER.info("Listing files for SQLite work item: %s", item_id)
        cursor = conn.execute(
            "SELECT filename FROM work_item_files WHERE work_item_id = ? ORDER BY filename",
            (item_id,)
        )

        files = [row[0] for row in cursor.fetchall()]
        LOGGER.debug("Listed %d files for work item: %s", len(files), item_id)
        return files

    # T026: Get file
    def get_file(self, item_id: str, name: str) -> bytes:
        """Retrieve file content from filesystem.

        Args:
            item_id: Work item ID
            name: Filename

        Returns:
            bytes: File content

        Raises:
            ValueError: If file not found
        """
        conn = self._get_connection()

        LOGGER.info("Loading file '%s' from SQLite work item: %s", name, item_id)
        cursor = conn.execute(
            "SELECT filepath FROM work_item_files WHERE work_item_id = ? AND filename = ?",
            (item_id, name)
        )
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"File not found: {name} (work item: {item_id})")

        filepath = Path(result[0])

        if not filepath.exists():
            raise ValueError(f"File missing from filesystem: {filepath}")

        content = filepath.read_bytes()
        LOGGER.debug("Retrieved file: %s (work item: %s, size: %d bytes)", name, item_id, len(content))
        return content

    # T027: Add file
    def add_file(self, item_id: str, name: str, content: bytes):
        """Attach file to work item.

        Stores file on filesystem and creates database reference.

        Args:
            item_id: Work item ID
            name: Filename
            content: File content

        Raises:
            ValueError: If file already exists
        """
        # T027: Create directory structure {files_dir}/{work_item_id}/{filename}
        item_dir = self.files_dir / item_id
        item_dir.mkdir(parents=True, exist_ok=True)

        filepath = item_dir / name

        LOGGER.info(
            "Adding file '%s' to SQLite work item %s (%d bytes)",
            name,
            item_id,
            len(content),
        )

        if filepath.exists():
            raise ValueError(f"File already exists: {name} (work item: {item_id})")

        # Write file to filesystem
        filepath.write_bytes(content)

        # Create database record
        conn = self._get_connection()

        try:
            conn.execute("""
                INSERT INTO work_item_files (work_item_id, filename, filepath)
                VALUES (?, ?, ?)
            """, (item_id, name, str(filepath)))

            conn.commit()
        except sqlite3.IntegrityError:
            # Cleanup file if database insert fails
            filepath.unlink(missing_ok=True)
            raise ValueError(f"File already exists: {name} (work item: {item_id})")

    # T028: Remove file
    def remove_file(self, item_id: str, name: str):
        """Remove file attachment.

        Deletes file from filesystem and removes database reference.

        Args:
            item_id: Work item ID
            name: Filename

        Raises:
            ValueError: If file not found
        """
        LOGGER.info("Removing file '%s' from SQLite work item %s", name, item_id)

        conn = self._get_connection()

        # Get filepath from database
        cursor = conn.execute(
            "SELECT filepath FROM work_item_files WHERE work_item_id = ? AND filename = ?",
            (item_id, name)
        )
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"File not found: {name} (work item: {item_id})")

        filepath = Path(result[0])

        # Delete from database
        conn.execute(
            "DELETE FROM work_item_files WHERE work_item_id = ? AND filename = ?",
            (item_id, name)
        )
        conn.commit()

        # Delete from filesystem
        filepath.unlink(missing_ok=True)

    # T030: Recover orphaned work items
    def recover_orphaned_work_items(self) -> list[str]:
        """Recover orphaned work items beyond timeout.

        Resets RESERVED work items to PENDING if they've been reserved longer
        than the configured timeout threshold.

        Returns:
            list[str]: List of recovered work item IDs

        Notes:
            - Timeout threshold configured via RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES
            - Default timeout: 30 minutes
            - Uses partial index idx_orphan_check for efficiency
        """
        conn = self._get_connection()

        cursor = conn.execute(
            f"""
                UPDATE work_items
                SET state = ?,
                    reserved_at = NULL
                WHERE state = ?
                AND datetime(reserved_at, '+{self.orphan_timeout_minutes} minutes') < datetime('now')
                RETURNING id
            """,
            (ProcessingState.PENDING.value, ProcessingState.RESERVED.value),
        )

        recovered_ids = [row[0] for row in cursor.fetchall()]
        conn.commit()

        if recovered_ids:
            LOGGER.warning(
                "Recovered %d orphaned work items (timeout: %d min): %s",
                len(recovered_ids), self.orphan_timeout_minutes, recovered_ids
            )
        else:
            LOGGER.debug("No orphaned work items found (timeout: %d min)", self.orphan_timeout_minutes)

        return recovered_ids
