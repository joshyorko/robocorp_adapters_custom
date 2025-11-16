# Usage Examples

This document provides practical examples of using `robocorp-adapters-custom` in various scenarios.

## Table of Contents

- [Basic Setup](#basic-setup)
- [SQLite Adapter Examples](#sqlite-adapter-examples)
- [Redis Adapter Examples](#redis-adapter-examples)
- [MongoDB/DocumentDB Adapter Examples](#mongodbdocumentdb-adapter-examples)
- [Integration with Robocorp Work Items](#integration-with-robocorp-work-items)
- [Producer-Consumer Patterns](#producer-consumer-patterns)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)

---

## Basic Setup

### Installing the Package

```bash
# Install with all optional dependencies
pip install robocorp-adapters-custom[all]

# Or install specific adapters
pip install robocorp-adapters-custom[redis]
pip install robocorp-adapters-custom[mongodb]
```

### Importing the Package

```python
from robocorp_adapters_custom import (
    get_adapter_instance,
    SQLiteAdapter,
    RedisAdapter,
    DocumentDBAdapter,
    State,
)
```

---

## SQLite Adapter Examples

### Example 1: Basic SQLite Setup

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

# Configure SQLite adapter
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "processing_queue"
os.environ["RC_WORKITEM_FILES_DIR"] = "./work_item_files"

# Get adapter instance
adapter = get_adapter_instance()

# Create a work item
payload = {"customer_id": "12345", "order_id": "ORD-001"}
item_id = adapter.create_output(parent_id=None, payload=payload)
print(f"Created work item: {item_id}")

# Reserve and process a work item
try:
    item_id = adapter.reserve_input()
    payload = adapter.load_payload(item_id)
    print(f"Processing: {payload}")
    
    # Process the item...
    
    # Mark as done
    adapter.release_input(item_id, State.DONE)
except Exception as e:
    # Mark as failed
    adapter.release_input(item_id, State.FAILED, exception={
        "type": type(e).__name__,
        "code": "PROCESSING_ERROR",
        "message": str(e)
    })
```

### Example 2: Working with File Attachments

```python
import os
from robocorp_adapters_custom import get_adapter_instance

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "file_queue"

adapter = get_adapter_instance()

# Create work item with file
item_id = adapter.create_output(None, {"description": "Invoice processing"})

# Add a file
with open("invoice.pdf", "rb") as f:
    adapter.add_file(item_id, "invoice.pdf", f.read())

# List files
files = adapter.list_files(item_id)
print(f"Attached files: {files}")

# Get file content
content = adapter.get_file(item_id, "invoice.pdf")
print(f"File size: {len(content)} bytes")
```

### Example 3: Orphan Recovery

```python
import os
from robocorp_adapters_custom import get_adapter_instance

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES"] = "30"

adapter = get_adapter_instance()

# Recover orphaned work items (reserved but not completed/failed)
recovered = adapter.recover_orphaned_work_items()
print(f"Recovered {recovered} orphaned work items")
```

---

## Redis Adapter Examples

### Example 1: Basic Redis Setup

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

# Configure Redis adapter
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_DB"] = "0"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "redis_queue"
os.environ["RC_WORKITEM_FILES_DIR"] = "./redis_files"

# Get adapter instance
adapter = get_adapter_instance()

# Create work items
for i in range(10):
    payload = {"task_id": i, "data": f"Task {i}"}
    adapter.create_output(None, payload)
    print(f"Created task {i}")
```

### Example 2: Redis with Password Authentication

```python
import os
from robocorp_adapters_custom import get_adapter_instance

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "redis.example.com"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_PASSWORD"] = "your_secure_password"
os.environ["REDIS_MAX_CONNECTIONS"] = "100"

adapter = get_adapter_instance()
print("Connected to Redis with authentication")
```

### Example 3: High-Throughput Processing

```python
import os
from concurrent.futures import ThreadPoolExecutor
from robocorp_adapters_custom import get_adapter_instance, State

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_MAX_CONNECTIONS"] = "50"

def process_work_item():
    """Worker function for processing items."""
    adapter = get_adapter_instance()
    try:
        item_id = adapter.reserve_input()
        payload = adapter.load_payload(item_id)
        
        # Process the item
        print(f"Processing: {payload}")
        
        adapter.release_input(item_id, State.DONE)
    except Exception as e:
        print(f"Error: {e}")

# Process items with multiple workers
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(process_work_item) for _ in range(10)]
    for future in futures:
        future.result()
```

---

## MongoDB/DocumentDB Adapter Examples

### Example 1: Basic DocumentDB Setup

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

# Configure DocumentDB adapter
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._docdb.DocumentDBAdapter"
os.environ["DOCDB_HOSTNAME"] = "docdb.example.com"
os.environ["DOCDB_PORT"] = "27017"
os.environ["DOCDB_USERNAME"] = "admin"
os.environ["DOCDB_PASSWORD"] = "password"
os.environ["DOCDB_DATABASE"] = "workitems"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "docdb_queue"

adapter = get_adapter_instance()

# Create and process work items
payload = {"document_id": "DOC-123", "status": "pending"}
item_id = adapter.create_output(None, payload)
print(f"Created item in DocumentDB: {item_id}")
```

### Example 2: AWS DocumentDB with TLS

```python
import os
from robocorp_adapters_custom import get_adapter_instance

# Configure for AWS DocumentDB
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._docdb.DocumentDBAdapter"
os.environ["DOCDB_URI"] = "mongodb://user:pass@docdb-cluster.cluster-xxx.us-east-1.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=rds-combined-ca-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "production_queue"

adapter = get_adapter_instance()
print("Connected to AWS DocumentDB with TLS")
```

### Example 3: Large File Storage with GridFS

```python
import os
from robocorp_adapters_custom import get_adapter_instance

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._docdb.DocumentDBAdapter"
os.environ["DOCDB_URI"] = "mongodb://localhost:27017/"
os.environ["DOCDB_DATABASE"] = "workitems"

adapter = get_adapter_instance()

# Create work item with large file (>1MB will use GridFS)
item_id = adapter.create_output(None, {"type": "large_file_processing"})

# Add a large file (e.g., 5MB)
large_data = b"x" * (5 * 1024 * 1024)  # 5MB of data
adapter.add_file(item_id, "large_file.bin", large_data)

print(f"Stored 5MB file in GridFS for item {item_id}")

# Retrieve the file
retrieved_data = adapter.get_file(item_id, "large_file.bin")
assert len(retrieved_data) == len(large_data)
print("File retrieved successfully from GridFS")
```

---

## Integration with Robocorp Work Items

### Example 1: Drop-in Replacement

```python
import os

# Configure custom adapter before importing robocorp
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"

# Use standard Robocorp work items API
from robocorp import workitems

# Producer code
def produce_items():
    for i in range(10):
        item = workitems.outputs.create(
            payload={"task_id": i, "data": f"Task {i}"}
        )
        item.save()

# Consumer code
def consume_items():
    for item in workitems.inputs:
        print(f"Processing: {item.payload}")
        # Process the item...
        item.done()
```

### Example 2: Explicit Adapter Usage

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "localhost"

# Get adapter directly
adapter = get_adapter_instance()

# Use adapter methods directly for more control
item_id = adapter.reserve_input()
payload = adapter.load_payload(item_id)

# Custom processing logic
result = process_custom_task(payload)

# Update payload
payload["result"] = result
adapter.save_payload(item_id, payload)

# Mark as done
adapter.release_input(item_id, State.DONE)
```

---

## Producer-Consumer Patterns

### Example 1: Simple Producer

```python
import os
from robocorp_adapters_custom import get_adapter_instance

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "tasks"

def produce_work_items():
    """Producer that creates work items."""
    adapter = get_adapter_instance()
    
    tasks = [
        {"type": "email", "recipient": "user@example.com"},
        {"type": "report", "report_id": "RPT-001"},
        {"type": "notification", "user_id": 123},
    ]
    
    for task in tasks:
        item_id = adapter.create_output(None, task)
        print(f"Created work item {item_id}: {task}")

if __name__ == "__main__":
    produce_work_items()
```

### Example 2: Simple Consumer

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State
from robocorp.workitems._exceptions import EmptyQueue

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "tasks"

def consume_work_items():
    """Consumer that processes work items."""
    adapter = get_adapter_instance()
    
    while True:
        try:
            item_id = adapter.reserve_input()
            payload = adapter.load_payload(item_id)
            
            print(f"Processing {payload['type']}: {payload}")
            
            # Process based on type
            if payload['type'] == 'email':
                send_email(payload['recipient'])
            elif payload['type'] == 'report':
                generate_report(payload['report_id'])
            
            adapter.release_input(item_id, State.DONE)
            
        except EmptyQueue:
            print("No more work items to process")
            break
        except Exception as e:
            print(f"Error processing item: {e}")
            adapter.release_input(item_id, State.FAILED, exception={
                "type": type(e).__name__,
                "code": "PROCESSING_ERROR",
                "message": str(e)
            })

if __name__ == "__main__":
    consume_work_items()
```

### Example 3: Multi-Stage Pipeline

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

# Stage 1: Data Collection
os.environ["RC_WORKITEM_QUEUE_NAME"] = "stage1_collect"
adapter = get_adapter_instance()

def collect_data():
    """Collect data and create work items for processing."""
    data_sources = ["source1", "source2", "source3"]
    for source in data_sources:
        payload = {"source": source, "stage": "collect"}
        adapter.create_output(None, payload)

# Stage 2: Data Processing
os.environ["RC_WORKITEM_QUEUE_NAME"] = "stage1_collect"
adapter_in = get_adapter_instance()
os.environ["RC_WORKITEM_QUEUE_NAME"] = "stage2_process"
adapter_out = get_adapter_instance(reinitialize=True)

def process_data():
    """Process collected data and pass to next stage."""
    item_id = adapter_in.reserve_input()
    payload = adapter_in.load_payload(item_id)
    
    # Process data
    processed_payload = {
        "source": payload["source"],
        "stage": "process",
        "processed": True
    }
    
    # Create output for next stage
    adapter_out.create_output(item_id, processed_payload)
    adapter_in.release_input(item_id, State.DONE)
```

---

## Error Handling

### Example 1: Retry Logic

```python
import os
import time
from robocorp_adapters_custom import get_adapter_instance, State
from robocorp.workitems._exceptions import EmptyQueue

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "localhost"

adapter = get_adapter_instance()

def process_with_retry(max_retries=3):
    """Process work items with retry logic."""
    try:
        item_id = adapter.reserve_input()
        payload = adapter.load_payload(item_id)
        
        for attempt in range(max_retries):
            try:
                # Attempt to process
                result = risky_operation(payload)
                
                # Success - mark as done
                adapter.release_input(item_id, State.DONE)
                return result
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Final attempt failed
                    adapter.release_input(item_id, State.FAILED, exception={
                        "type": type(e).__name__,
                        "code": "MAX_RETRIES_EXCEEDED",
                        "message": f"Failed after {max_retries} attempts: {e}"
                    })
                    raise
                    
    except EmptyQueue:
        print("No work items available")
```

### Example 2: Graceful Degradation

```python
import os
from robocorp_adapters_custom import get_adapter_instance, State

def process_with_fallback():
    """Process work items with fallback behavior."""
    try:
        adapter = get_adapter_instance()
        item_id = adapter.reserve_input()
        payload = adapter.load_payload(item_id)
        
        try:
            # Try primary processing method
            result = primary_processor(payload)
        except Exception as primary_error:
            print(f"Primary processing failed: {primary_error}")
            try:
                # Try fallback method
                result = fallback_processor(payload)
                payload["processing_method"] = "fallback"
            except Exception as fallback_error:
                # Both methods failed
                adapter.release_input(item_id, State.FAILED, exception={
                    "type": "ProcessingError",
                    "code": "ALL_METHODS_FAILED",
                    "message": f"Primary: {primary_error}, Fallback: {fallback_error}"
                })
                return
        
        adapter.release_input(item_id, State.DONE)
        
    except Exception as e:
        print(f"Fatal error: {e}")
```

---

## Advanced Usage

### Example 1: Custom Adapter Configuration

```python
import os
from robocorp_adapters_custom import load_adapter_class

# Dynamically load adapter based on environment
environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
    os.environ["REDIS_HOST"] = "redis-prod.example.com"
elif environment == "staging":
    os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._docdb.DocumentDBAdapter"
    os.environ["DOCDB_URI"] = "mongodb://staging-db.example.com/"
else:
    os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
    os.environ["RC_WORKITEM_DB_PATH"] = "dev_work_items.db"

# Load the configured adapter
adapter_class = load_adapter_class(os.environ["RC_WORKITEM_ADAPTER"])
adapter = adapter_class()

print(f"Using {adapter.__class__.__name__} for {environment} environment")
```

### Example 2: Monitoring and Metrics

```python
import os
import time
from robocorp_adapters_custom import get_adapter_instance, State
from robocorp.workitems._exceptions import EmptyQueue

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._redis.RedisAdapter"
os.environ["REDIS_HOST"] = "localhost"

class WorkItemProcessor:
    def __init__(self):
        self.adapter = get_adapter_instance()
        self.processed_count = 0
        self.failed_count = 0
        self.total_time = 0
    
    def process_item(self):
        """Process a single work item with metrics."""
        start_time = time.time()
        
        try:
            item_id = self.adapter.reserve_input()
            payload = self.adapter.load_payload(item_id)
            
            # Process the item
            result = self._do_processing(payload)
            
            self.adapter.release_input(item_id, State.DONE)
            self.processed_count += 1
            
        except EmptyQueue:
            raise
        except Exception as e:
            self.adapter.release_input(item_id, State.FAILED, exception={
                "type": type(e).__name__,
                "code": "PROCESSING_ERROR",
                "message": str(e)
            })
            self.failed_count += 1
        finally:
            elapsed = time.time() - start_time
            self.total_time += elapsed
    
    def print_metrics(self):
        """Print processing metrics."""
        total_items = self.processed_count + self.failed_count
        avg_time = self.total_time / total_items if total_items > 0 else 0
        success_rate = (self.processed_count / total_items * 100) if total_items > 0 else 0
        
        print(f"Processed: {self.processed_count}")
        print(f"Failed: {self.failed_count}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Time: {avg_time:.2f}s")

# Usage
processor = WorkItemProcessor()
while True:
    try:
        processor.process_item()
    except EmptyQueue:
        break

processor.print_metrics()
```

---

## Best Practices

1. **Always handle EmptyQueue exceptions** when processing work items
2. **Use environment variables** for configuration to keep code portable
3. **Implement proper error handling** and mark items as failed when appropriate
4. **Use connection pooling** (configured automatically in adapters) for better performance
5. **Monitor orphaned items** and run recovery periodically in production
6. **Choose the right adapter** based on your deployment environment
7. **Test locally with SQLite** before deploying with Redis/DocumentDB
8. **Use proper State values** (State.DONE, State.FAILED) when releasing items

---

For more information, see:
- [Installation Guide](INSTALLATION.md)
- [README](README.md)
- [Documentation](docs/)
