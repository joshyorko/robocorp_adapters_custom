# Custom Work Item Adapter Implementation Guide

## Executive Summary

This guide documents how to create custom work item adapters for the Robocorp workitems library. Custom adapters allow you to integrate with any backend system (RabbitMQ, Redis, PostgreSQL, Celery, etc.) while maintaining compatibility with the existing producer-consumer workflow pattern.

**Research Date**: October 11, 2025  
**Source**: [robocorp/robocorp GitHub repository](https://github.com/robocorp/robocorp)  
**Workitems Library**: `robocorp-workitems==1.4.7`

---

## Table of Contents

1. [Available Adapter Types](#available-adapter-types)
2. [BaseAdapter Interface](#baseadapter-interface)
3. [Custom Adapter Implementation](#custom-adapter-implementation)
4. [Integration Examples](#integration-examples)
5. [Testing Custom Adapters](#testing-custom-adapters)
6. [Production Deployment](#production-deployment)

---

## Available Adapter Types

Robocorp provides two built-in adapters:

### 1. FileAdapter (Local Development)

**Location**: `robocorp/workitems/_adapters/_file.py`

**Purpose**: Local file-based work item simulation for development and testing

**Configuration**:
```json
{
  "RC_WORKITEM_ADAPTER": "FileAdapter",
  "RC_WORKITEM_INPUT_PATH": "devdata/work-items-in/work-items.json",
  "RC_WORKITEM_OUTPUT_PATH": "devdata/work-items-out/work-items.json"
}
```

**Features**:
- Stores work items as JSON files
- Simulates queue behavior with list index
- Supports file attachments in same directory
- Auto-generates default paths if not specified
- Perfect for local development and CI/CD testing

### 2. RobocorpAdapter (Production)

**Location**: `robocorp/workitems/_adapters/_robocorp.py`

**Purpose**: Production adapter for Robocorp Control Room

**Configuration**:
```python
# Auto-detected when running in Control Room
# Requires these environment variables:
# - RC_API_WORKITEM_HOST
# - RC_API_WORKITEM_TOKEN
# - RC_API_PROCESS_HOST  
# - RC_API_PROCESS_TOKEN
# - RC_WORKSPACE_ID
# - RC_PROCESS_RUN_ID
# - RC_ACTIVITY_RUN_ID
# - RC_WORKITEM_ID
```

**Features**:
- RESTful API integration with Control Room
- S3-backed file storage
- Built-in work item state management
- Automatic queue management
- Production-ready error handling

---

## BaseAdapter Interface

All custom adapters must inherit from `BaseAdapter` and implement these abstract methods:

### Source Code

```python
from abc import ABC, abstractmethod
from typing import Optional
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType


class BaseAdapter(ABC):
    """Abstract base class for work item adapters."""

    @abstractmethod
    def reserve_input(self) -> str:
        """Get next work item ID from the input queue and reserve it.
        
        Returns:
            str: Work item ID
            
        Raises:
            EmptyQueue: When no more work items available
        """
        raise NotImplementedError

    @abstractmethod
    def release_input(
        self, item_id: str, state: State, exception: Optional[dict] = None
    ):
        """Release the lastly retrieved input work item and set state.
        
        Args:
            item_id: Work item ID to release
            state: Final state (State.DONE or State.FAILED)
            exception: Optional exception details if state is FAILED
        """
        raise NotImplementedError

    @abstractmethod
    def create_output(self, parent_id: str, payload: Optional[JSONType] = None) -> str:
        """Create new output for work item, and return created ID.
        
        Args:
            parent_id: Parent work item ID
            payload: Optional JSON payload for the new work item
            
        Returns:
            str: New work item ID
        """
        raise NotImplementedError

    @abstractmethod
    def load_payload(self, item_id: str) -> JSONType:
        """Load JSON payload from work item.
        
        Args:
            item_id: Work item ID
            
        Returns:
            JSONType: JSON-serializable payload data
        """
        raise NotImplementedError

    @abstractmethod
    def save_payload(self, item_id: str, payload: JSONType):
        """Save JSON payload to work item.
        
        Args:
            item_id: Work item ID
            payload: JSON-serializable payload data
        """
        raise NotImplementedError

    @abstractmethod
    def list_files(self, item_id: str) -> list[str]:
        """List attached files in work item.
        
        Args:
            item_id: Work item ID
            
        Returns:
            list[str]: List of filenames
        """
        raise NotImplementedError

    @abstractmethod
    def get_file(self, item_id: str, name: str) -> bytes:
        """Read file's contents from work item.
        
        Args:
            item_id: Work item ID
            name: Filename
            
        Returns:
            bytes: File content
        """
        raise NotImplementedError

    @abstractmethod
    def add_file(self, item_id: str, name: str, content: bytes):
        """Attach file to work item.
        
        Args:
            item_id: Work item ID
            name: Filename
            content: File content as bytes
        """
        raise NotImplementedError

    @abstractmethod
    def remove_file(self, item_id: str, name: str):
        """Remove attached file from work item.
        
        Args:
            item_id: Work item ID
            name: Filename
        """
        raise NotImplementedError
```

### State Enum

```python
from enum import Enum

class State(str, Enum):
    """Work item state."""
    DONE = "DONE"      # Successfully processed
    FAILED = "FAILED"  # Processing failed
```

---

## Custom Adapter Implementation

### Example: SQLite Database Adapter

This adapter stores work items in SQLite with file attachments on disk.

#### Step 1: Create Adapter Class

```python
# src/robocorp_adapters_custom/sqlite_adapter.py

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType

LOGGER = logging.getLogger(__name__)


class SQLiteAdapter(BaseAdapter):
    """Work item adapter using SQLite database backend.
    
    Environment variables:
        RC_WORKITEM_DB_PATH: Path to SQLite database file
        RC_WORKITEM_FILES_DIR: Directory for file attachments
        RC_WORKITEM_QUEUE_NAME: Queue name to process (default: 'default')
    """
    
    def __init__(self):
        self.db_path = os.getenv(
            "RC_WORKITEM_DB_PATH", 
            "work_items.db"
        )
        self.files_dir = Path(os.getenv(
            "RC_WORKITEM_FILES_DIR",
            "work_item_files"
        ))
        self.queue_name = os.getenv(
            "RC_WORKITEM_QUEUE_NAME",
            "default"
        )
        
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        LOGGER.info(
            "SQLiteAdapter initialized: db=%s, files=%s, queue=%s",
            self.db_path, self.files_dir, self.queue_name
        )
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_items (
                    id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    parent_id TEXT,
                    payload TEXT,
                    state TEXT DEFAULT 'PENDING',
                    exception_type TEXT,
                    exception_code TEXT,
                    exception_message TEXT,
                    reserved_at TIMESTAMP,
                    released_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_queue_state (queue_name, state),
                    INDEX idx_parent (parent_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_item_files (
                    work_item_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (work_item_id, filename),
                    FOREIGN KEY (work_item_id) REFERENCES work_items(id)
                )
            """)
            
            conn.commit()
    
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def reserve_input(self) -> str:
        """Reserve next available work item from queue."""
        with self._get_connection() as conn:
            # Find and reserve next pending work item
            cursor = conn.execute("""
                UPDATE work_items
                SET state = 'RESERVED',
                    reserved_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM work_items
                    WHERE queue_name = ?
                    AND state = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING id
            """, (self.queue_name,))
            
            row = cursor.fetchone()
            
            if not row:
                raise EmptyQueue(f"No work items in queue: {self.queue_name}")
            
            item_id = row[0]
            conn.commit()
            
            LOGGER.info("Reserved work item: %s", item_id)
            return item_id
    
    def release_input(
        self,
        item_id: str,
        state: State,
        exception: Optional[dict] = None
    ):
        """Release work item with final state."""
        with self._get_connection() as conn:
            if exception:
                conn.execute("""
                    UPDATE work_items
                    SET state = ?,
                        released_at = CURRENT_TIMESTAMP,
                        exception_type = ?,
                        exception_code = ?,
                        exception_message = ?
                    WHERE id = ?
                """, (
                    state.value,
                    exception.get("type"),
                    exception.get("code"),
                    exception.get("message"),
                    item_id
                ))
            else:
                conn.execute("""
                    UPDATE work_items
                    SET state = ?,
                        released_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (state.value, item_id))
            
            conn.commit()
            
            LOGGER.info(
                "Released work item %s with state %s",
                item_id, state.value
            )
    
    def create_output(
        self,
        parent_id: str,
        payload: Optional[JSONType] = None
    ) -> str:
        """Create new output work item."""
        item_id = str(uuid.uuid4())
        payload_json = json.dumps(payload) if payload else None
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO work_items (id, queue_name, parent_id, payload, state)
                VALUES (?, ?, ?, ?, 'PENDING')
            """, (item_id, self.queue_name, parent_id, payload_json))
            
            conn.commit()
        
        LOGGER.info("Created output work item: %s (parent: %s)", item_id, parent_id)
        return item_id
    
    def load_payload(self, item_id: str) -> JSONType:
        """Load work item payload."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT payload FROM work_items WHERE id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Work item not found: {item_id}")
            
            payload_json = row["payload"]
            return json.loads(payload_json) if payload_json else {}
    
    def save_payload(self, item_id: str, payload: JSONType):
        """Save work item payload."""
        payload_json = json.dumps(payload)
        
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE work_items SET payload = ? WHERE id = ?",
                (payload_json, item_id)
            )
            conn.commit()
        
        LOGGER.info("Saved payload for work item: %s", item_id)
    
    def list_files(self, item_id: str) -> list[str]:
        """List attached files."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT filename FROM work_item_files WHERE work_item_id = ?",
                (item_id,)
            )
            return [row["filename"] for row in cursor.fetchall()]
    
    def get_file(self, item_id: str, name: str) -> bytes:
        """Get file content."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT filepath FROM work_item_files
                WHERE work_item_id = ? AND filename = ?
            """, (item_id, name))
            
            row = cursor.fetchone()
            if not row:
                raise FileNotFoundError(
                    f"File '{name}' not found in work item {item_id}"
                )
            
            filepath = Path(row["filepath"])
            return filepath.read_bytes()
    
    def add_file(self, item_id: str, name: str, content: bytes):
        """Add file attachment."""
        # Save file to disk
        filepath = self.files_dir / item_id / name
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(content)
        
        # Record in database
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO work_item_files
                (work_item_id, filename, filepath)
                VALUES (?, ?, ?)
            """, (item_id, name, str(filepath)))
            conn.commit()
        
        LOGGER.info("Added file '%s' to work item %s", name, item_id)
    
    def remove_file(self, item_id: str, name: str):
        """Remove file attachment."""
        with self._get_connection() as conn:
            # Get filepath before deleting
            cursor = conn.execute("""
                SELECT filepath FROM work_item_files
                WHERE work_item_id = ? AND filename = ?
            """, (item_id, name))
            
            row = cursor.fetchone()
            if row:
                filepath = Path(row["filepath"])
                if filepath.exists():
                    filepath.unlink()
            
            # Delete from database
            conn.execute("""
                DELETE FROM work_item_files
                WHERE work_item_id = ? AND filename = ?
            """, (item_id, name))
            conn.commit()
        
        LOGGER.info("Removed file '%s' from work item %s", name, item_id)
```

#### Step 2: Register Custom Adapter

There are two ways to use a custom adapter:

**Option A: Environment Variable (Recommended)**

```json
{
  "RC_WORKITEM_ADAPTER": "robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter",
  "RC_WORKITEM_DB_PATH": "/path/to/work_items.db",
  "RC_WORKITEM_FILES_DIR": "/path/to/work_item_files",
  "RC_WORKITEM_QUEUE_NAME": "linkedin_jobs"
}
```

**Option B: Direct Import in Code**

```python
import os
from robocorp_adapters_custom.sqlite_adapter import SQLiteAdapter

# Set before importing workitems
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter"

from robocorp import workitems
from robocorp.tasks import task

@task
def consumer():
    for item in workitems.inputs:
        # Process work item
        print(item.payload)
        item.done()
```

#### Step 3: Update conda.yaml

```yaml
channels:
  - conda-forge

dependencies:
  - python=3.12.11
  - pip:
    - robocorp==3.0.0
    - robocorp-workitems==1.4.7
```

#### Step 4: Project Structure

```
linkedin-easy-apply/
├── src/
│   ├── robocorp_adapters_custom/
│   │   ├── __init__.py
│   │   └── sqlite_adapter.py
│   └── tasks.py
├── devdata/
│   ├── env-sqlite-producer.json
│   └── env-sqlite-consumer.json
├── robot.yaml
└── conda.yaml
```

---

## Integration Examples

### Example 1: Redis Queue Adapter

```python
# robocorp_adapters_custom/redis_adapter.py

import json
import logging
import os
import redis
from typing import Optional
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType

LOGGER = logging.getLogger(__name__)


class RedisAdapter(BaseAdapter):
    """Work item adapter using Redis for queue management.
    
    Environment variables:
        REDIS_HOST: Redis hostname (default: localhost)
        REDIS_PORT: Redis port (default: 6379)
        REDIS_DB: Redis database number (default: 0)
        REDIS_PASSWORD: Redis password (optional)
        RC_WORKITEM_QUEUE_NAME: Queue name (default: 'workitems')
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=False  # We handle bytes
        )
        self.queue_name = os.getenv("RC_WORKITEM_QUEUE_NAME", "workitems")
        
        LOGGER.info("RedisAdapter initialized: queue=%s", self.queue_name)
    
    def _make_key(self, key_type: str, item_id: str = None) -> str:
        """Generate Redis key."""
        if item_id:
            return f"{self.queue_name}:{key_type}:{item_id}"
        return f"{self.queue_name}:{key_type}"
    
    def reserve_input(self) -> str:
        """Pop next work item from queue."""
        # BRPOPLPUSH for atomic reserve with timeout
        queue_key = self._make_key("pending")
        processing_key = self._make_key("processing")
        
        item_id = self.redis_client.brpoplpush(
            queue_key,
            processing_key,
            timeout=0  # Block indefinitely
        )
        
        if not item_id:
            raise EmptyQueue(f"No work items in queue: {self.queue_name}")
        
        item_id = item_id.decode("utf-8")
        LOGGER.info("Reserved work item: %s", item_id)
        return item_id
    
    def release_input(
        self,
        item_id: str,
        state: State,
        exception: Optional[dict] = None
    ):
        """Release work item with final state."""
        processing_key = self._make_key("processing")
        
        # Remove from processing queue
        self.redis_client.lrem(processing_key, 0, item_id)
        
        # Update state
        state_key = self._make_key("state", item_id)
        self.redis_client.set(state_key, state.value)
        
        # Store exception if present
        if exception:
            exception_key = self._make_key("exception", item_id)
            self.redis_client.set(
                exception_key,
                json.dumps(exception),
                ex=86400  # Expire after 24 hours
            )
        
        LOGGER.info("Released work item %s with state %s", item_id, state.value)
    
    def create_output(
        self,
        parent_id: str,
        payload: Optional[JSONType] = None
    ) -> str:
        """Create new output work item."""
        import uuid
        item_id = str(uuid.uuid4())
        
        # Save payload
        if payload:
            self.save_payload(item_id, payload)
        
        # Add to queue
        queue_key = self._make_key("pending")
        self.redis_client.lpush(queue_key, item_id)
        
        # Store parent relationship
        parent_key = self._make_key("parent", item_id)
        self.redis_client.set(parent_key, parent_id)
        
        LOGGER.info("Created output work item: %s", item_id)
        return item_id
    
    def load_payload(self, item_id: str) -> JSONType:
        """Load work item payload from Redis."""
        payload_key = self._make_key("payload", item_id)
        data = self.redis_client.get(payload_key)
        
        if not data:
            return {}
        
        return json.loads(data)
    
    def save_payload(self, item_id: str, payload: JSONType):
        """Save work item payload to Redis."""
        payload_key = self._make_key("payload", item_id)
        self.redis_client.set(
            payload_key,
            json.dumps(payload),
            ex=604800  # Expire after 7 days
        )
    
    def list_files(self, item_id: str) -> list[str]:
        """List files attached to work item."""
        files_key = self._make_key("files", item_id)
        return [
            name.decode("utf-8")
            for name in self.redis_client.hkeys(files_key)
        ]
    
    def get_file(self, item_id: str, name: str) -> bytes:
        """Get file content from Redis."""
        files_key = self._make_key("files", item_id)
        content = self.redis_client.hget(files_key, name)
        
        if content is None:
            raise FileNotFoundError(f"File '{name}' not found")
        
        return content
    
    def add_file(self, item_id: str, name: str, content: bytes):
        """Add file to work item in Redis."""
        files_key = self._make_key("files", item_id)
        self.redis_client.hset(files_key, name, content)
        self.redis_client.expire(files_key, 604800)  # 7 days
    
    def remove_file(self, item_id: str, name: str):
        """Remove file from work item."""
        files_key = self._make_key("files", item_id)
        self.redis_client.hdel(files_key, name)
```

### Example 2: RabbitMQ with Celery Integration

```python
# robocorp_adapters_custom/celery_adapter.py

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from celery import Celery
from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType

LOGGER = logging.getLogger(__name__)


class CeleryAdapter(BaseAdapter):
    """Work item adapter using Celery/RabbitMQ for distributed processing.
    
    Environment variables:
        CELERY_BROKER_URL: Celery broker URL (e.g., amqp://guest@localhost//)
        CELERY_RESULT_BACKEND: Result backend URL (e.g., redis://localhost:6379/0)
        RC_WORKITEM_QUEUE_NAME: Queue name (default: 'workitems')
        RC_WORKITEM_FILES_DIR: Directory for file storage
    """
    
    def __init__(self):
        broker_url = os.getenv(
            "CELERY_BROKER_URL",
            "amqp://guest:guest@localhost:5672//"
        )
        result_backend = os.getenv(
            "CELERY_RESULT_BACKEND",
            "redis://localhost:6379/0"
        )
        
        self.celery_app = Celery(
            "workitems",
            broker=broker_url,
            backend=result_backend
        )
        
        self.queue_name = os.getenv("RC_WORKITEM_QUEUE_NAME", "workitems")
        self.files_dir = Path(os.getenv(
            "RC_WORKITEM_FILES_DIR",
            "work_item_files"
        ))
        self.files_dir.mkdir(parents=True, exist_ok=True)
        
        # Task definition for work item processing
        @self.celery_app.task(name="workitem.process", queue=self.queue_name)
        def process_workitem(item_id: str, payload: dict):
            """Celery task for processing work item."""
            LOGGER.info("Processing work item %s via Celery", item_id)
            return {"item_id": item_id, "status": "processed"}
        
        self.process_task = process_workitem
        self._current_task = None
        
        LOGGER.info("CeleryAdapter initialized: queue=%s", self.queue_name)
    
    def reserve_input(self) -> str:
        """Reserve next work item from Celery queue.
        
        Note: In a real Celery integration, this would typically be
        handled by the Celery worker itself. This implementation
        simulates the behavior for compatibility.
        """
        # In practice, Celery workers pull tasks automatically
        # This is a simplified implementation
        if self._current_task:
            return self._current_task["id"]
        
        raise EmptyQueue("No work items available (Celery mode)")
    
    def release_input(
        self,
        item_id: str,
        state: State,
        exception: Optional[dict] = None
    ):
        """Release work item with result."""
        # Store result in Celery backend
        result = {
            "item_id": item_id,
            "state": state.value,
            "exception": exception
        }
        
        # In a real implementation, this would update the task result
        LOGGER.info("Released work item %s: %s", item_id, state.value)
        self._current_task = None
    
    def create_output(
        self,
        parent_id: str,
        payload: Optional[JSONType] = None
    ) -> str:
        """Create new output work item and submit to Celery."""
        item_id = str(uuid.uuid4())
        
        # Submit task to Celery
        task = self.process_task.apply_async(
            args=[item_id, payload or {}],
            queue=self.queue_name,
            task_id=item_id
        )
        
        LOGGER.info(
            "Created output work item %s (Celery task: %s)",
            item_id, task.id
        )
        return item_id
    
    def load_payload(self, item_id: str) -> JSONType:
        """Load payload from Celery result backend."""
        # Retrieve task result
        task_result = self.celery_app.AsyncResult(item_id)
        
        if task_result.state == "PENDING":
            # Task not yet available, return empty
            return {}
        
        return task_result.result or {}
    
    def save_payload(self, item_id: str, payload: JSONType):
        """Save payload (stored in task result)."""
        # In Celery, payloads are typically part of task args
        # This could update metadata or use a separate store
        LOGGER.info("Payload save requested for %s", item_id)
    
    def list_files(self, item_id: str) -> list[str]:
        """List files for work item."""
        item_dir = self.files_dir / item_id
        if not item_dir.exists():
            return []
        return [f.name for f in item_dir.iterdir() if f.is_file()]
    
    def get_file(self, item_id: str, name: str) -> bytes:
        """Get file content."""
        filepath = self.files_dir / item_id / name
        if not filepath.exists():
            raise FileNotFoundError(f"File '{name}' not found")
        return filepath.read_bytes()
    
    def add_file(self, item_id: str, name: str, content: bytes):
        """Add file attachment."""
        item_dir = self.files_dir / item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        filepath = item_dir / name
        filepath.write_bytes(content)
    
    def remove_file(self, item_id: str, name: str):
        """Remove file attachment."""
        filepath = self.files_dir / item_id / name
        if filepath.exists():
            filepath.unlink()
```

---

## Testing Custom Adapters

### Unit Test Example

```python
# tests/test_sqlite_adapter.py

import pytest
import tempfile
from pathlib import Path
from robocorp_adapters_custom.sqlite_adapter import SQLiteAdapter
from robocorp.workitems._types import State


@pytest.fixture
def adapter():
    """Create adapter with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        files_dir = Path(tmpdir) / "files"
        
        import os
        os.environ["RC_WORKITEM_DB_PATH"] = str(db_path)
        os.environ["RC_WORKITEM_FILES_DIR"] = str(files_dir)
        os.environ["RC_WORKITEM_QUEUE_NAME"] = "test_queue"
        
        yield SQLiteAdapter()


def test_create_and_reserve_work_item(adapter):
    """Test creating and reserving work items."""
    # Create a work item
    item_id = adapter.create_output(
        parent_id="root",
        payload={"test": "data"}
    )
    
    assert item_id is not None
    
    # Reserve it
    reserved_id = adapter.reserve_input()
    assert reserved_id == item_id
    
    # Load payload
    payload = adapter.load_payload(reserved_id)
    assert payload["test"] == "data"


def test_release_work_item(adapter):
    """Test releasing work items with different states."""
    item_id = adapter.create_output(parent_id="root", payload={})
    reserved_id = adapter.reserve_input()
    
    # Release as done
    adapter.release_input(reserved_id, State.DONE)
    
    # Verify state (would need to add a method to check state)
    # In practice, you'd query the database directly


def test_file_operations(adapter):
    """Test file attachment operations."""
    item_id = adapter.create_output(parent_id="root", payload={})
    
    # Add file
    content = b"test file content"
    adapter.add_file(item_id, "test.txt", content)
    
    # List files
    files = adapter.list_files(item_id)
    assert "test.txt" in files
    
    # Get file
    retrieved = adapter.get_file(item_id, "test.txt")
    assert retrieved == content
    
    # Remove file
    adapter.remove_file(item_id, "test.txt")
    files = adapter.list_files(item_id)
    assert "test.txt" not in files


def test_empty_queue(adapter):
    """Test EmptyQueue exception."""
    from robocorp.workitems._exceptions import EmptyQueue
    
    with pytest.raises(EmptyQueue):
        adapter.reserve_input()
```

### Integration Test with Robot

```python
# tests/test_producer_consumer_sqlite.py

import os
import tempfile
from pathlib import Path


def test_producer_consumer_workflow():
    """Test full producer-consumer workflow with SQLite adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Set environment
        os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter"
        os.environ["RC_WORKITEM_DB_PATH"] = str(db_path)
        os.environ["RC_WORKITEM_FILES_DIR"] = str(Path(tmpdir) / "files")
        os.environ["RC_WORKITEM_QUEUE_NAME"] = "test_queue"
        
        # Import after setting environment
        from robocorp import workitems
        from robocorp.tasks import task
        
        # Producer: Create work items
        @task
        def producer():
            for i in range(5):
                payload = {"index": i, "data": f"item_{i}"}
                workitems.outputs.create(payload)
        
        # Consumer: Process work items
        @task
        def consumer():
            processed = []
            for item in workitems.inputs:
                processed.append(item.payload["index"])
                item.done()
            return processed
        
        # Run producer
        producer()
        
        # Run consumer
        results = consumer()
        
        assert len(results) == 5
        assert results == [0, 1, 2, 3, 4]
```

---

## Production Deployment

### Configuration Management

#### Environment Configuration

```json
{
  "RC_WORKITEM_ADAPTER": "robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter",
  "RC_WORKITEM_DB_PATH": "/data/work_items.db",
  "RC_WORKITEM_FILES_DIR": "/data/work_item_files",
  "RC_WORKITEM_QUEUE_NAME": "linkedin_jobs",
  "LOG_LEVEL": "INFO"
}
```

### Docker Deployment

#### Dockerfile

```dockerfile
FROM robocorp/rcc:latest

WORKDIR /robot

# Copy robot files
COPY . .

# Install dependencies
RUN rcc holotree vars --silent

# Set adapter configuration
ENV RC_WORKITEM_ADAPTER=robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter
ENV RC_WORKITEM_DB_PATH=/data/work_items.db
ENV RC_WORKITEM_FILES_DIR=/data/files

# Run robot
CMD ["rcc", "task", "run", "--task", "Consumer"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  producer:
    build: .
    environment:
      RC_WORKITEM_ADAPTER: robocorp_adapters_custom.redis_adapter.RedisAdapter
      REDIS_HOST: redis
      RC_WORKITEM_QUEUE_NAME: linkedin_jobs
    depends_on:
      - redis
    command: ["rcc", "task", "run", "--task", "Producer"]

  consumer:
    build: .
    environment:
      RC_WORKITEM_ADAPTER: robocorp_adapters_custom.redis_adapter.RedisAdapter
      REDIS_HOST: redis
      RC_WORKITEM_QUEUE_NAME: linkedin_jobs
    depends_on:
      - redis
      - producer
    deploy:
      replicas: 3
    command: ["rcc", "task", "run", "--task", "Consumer"]

volumes:
  redis_data:
  rabbitmq_data:
```

### Scaling Considerations

1. **Database Connections**: Use connection pooling
2. **File Storage**: Consider S3/MinIO for distributed systems
3. **Concurrency**: Implement proper locking for `reserve_input()`
4. **Monitoring**: Add metrics and health checks
5. **Error Handling**: Implement retry logic and dead-letter queues

---

## Summary

### Key Takeaways

1. **BaseAdapter Interface**: All custom adapters must implement 9 abstract methods
2. **Built-in Adapters**: FileAdapter (local) and RobocorpAdapter (Cloud)
3. **Registration**: Set `RC_WORKITEM_ADAPTER` environment variable to your adapter class path
4. **Testing**: Write unit and integration tests before production use
5. **Scalability**: Design adapters with concurrency and distribution in mind

### Adapter Comparison

| Feature | FileAdapter | RobocorpAdapter | SQLiteAdapter | RedisAdapter | CeleryAdapter |
|---------|-------------|-----------------|---------------|--------------|---------------|
| **Use Case** | Local dev | Production Cloud | Local/Small | Distributed | Enterprise |
| **Queue Type** | File-based | Cloud API | Database | In-memory | Message broker |
| **Concurrency** | Limited | High | Medium | High | Very High |
| **Persistence** | Files | Cloud storage | Database | Optional | Message queue |
| **Complexity** | Low | Low | Medium | Medium | High |
| **Setup Time** | Instant | Requires Control Room | Minutes | Minutes | Hours |

### Next Steps

1. Choose the adapter that matches your infrastructure
2. Implement the `BaseAdapter` interface
3. Test thoroughly with unit and integration tests
4. Deploy with proper configuration management
5. Monitor and scale as needed

---

## References

- [Robocorp GitHub Repository](https://github.com/robocorp/robocorp)
- [Work Items Documentation](https://robocorp.com/docs/development-guide/control-room/work-items)
- [Producer-Consumer Template](https://github.com/robocorp/template-python-workitems)
- [BaseAdapter Source Code](https://github.com/robocorp/robocorp/blob/master/workitems/src/robocorp/workitems/_adapters/_base.py)
