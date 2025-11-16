# Installation Guide

## Overview

`robocorp-adapters-custom` is a Python package that provides custom work item adapters for Robocorp's automation framework. It enables scalable producer-consumer workflows with pluggable backend support (SQLite, Redis, MongoDB/DocumentDB).

## Requirements

- Python 3.9 or higher
- `robocorp` package (automatically installed as dependency)

## Installation Methods

### 1. Install from Source (Development)

Clone the repository and install in development mode:

```bash
git clone https://github.com/joshyorko/robocorp_adapters_custom.git
cd robocorp_adapters_custom
pip install -e .
```

This creates an editable installation, allowing you to modify the code and see changes immediately.

### 2. Install from Wheel (Production)

Build and install the wheel package:

```bash
# Build the package
python -m pip install build
python -m build

# Install the wheel
pip install dist/robocorp_adapters_custom-1.0.0-py3-none-any.whl
```

### 3. Install with Optional Dependencies

The package supports optional dependencies for different adapters:

```bash
# Install with Redis support
pip install robocorp-adapters-custom[redis]

# Install with MongoDB/DocumentDB support
pip install robocorp-adapters-custom[mongodb]

# Install with PostgreSQL support
pip install robocorp-adapters-custom[postgresql]

# Install with all optional dependencies
pip install robocorp-adapters-custom[all]

# Install with development dependencies
pip install robocorp-adapters-custom[dev]
```

## Quick Start

### Basic Usage

```python
import os
from robocorp_adapters_custom import get_adapter_instance

# Configure adapter via environment variables
os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "work_items.db"
os.environ["RC_WORKITEM_QUEUE_NAME"] = "my_queue"

# Get adapter instance
adapter = get_adapter_instance()

# Use adapter for work item operations
item_id = adapter.reserve_input()
payload = adapter.load_payload(item_id)
# ... process work item ...
adapter.release_input(item_id, State.DONE)
```

### Using as Drop-in Replacement

The package is designed to work seamlessly with existing Robocorp work item code:

```python
# Original Robocorp code
from robocorp import workitems

for item in workitems.inputs:
    payload = item.payload
    # ... process work item ...
    item.done()

# When using custom adapters, set the environment variable:
# RC_WORKITEM_ADAPTER=robocorp_adapters_custom._sqlite.SQLiteAdapter
# The code remains the same!
```

## Configuration

All adapters are configured via environment variables:

### Common Configuration (All Adapters)

```bash
RC_WORKITEM_ADAPTER=<adapter_class_path>
RC_WORKITEM_QUEUE_NAME=<queue_name>  # Default: "default"
RC_WORKITEM_FILES_DIR=<files_directory>  # Default: "devdata/work_item_files"
RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES=<minutes>  # Default: 30
```

### SQLite Adapter

```bash
RC_WORKITEM_ADAPTER=robocorp_adapters_custom._sqlite.SQLiteAdapter
RC_WORKITEM_DB_PATH=work_items.db
```

### Redis Adapter

```bash
RC_WORKITEM_ADAPTER=robocorp_adapters_custom._redis.RedisAdapter
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<optional>
REDIS_MAX_CONNECTIONS=50
```

### MongoDB/DocumentDB Adapter

```bash
RC_WORKITEM_ADAPTER=robocorp_adapters_custom._docdb.DocumentDBAdapter
DOCDB_URI=mongodb://user:pass@host:port/database
# OR
DOCDB_HOSTNAME=localhost
DOCDB_PORT=27017
DOCDB_USERNAME=<username>
DOCDB_PASSWORD=<password>
DOCDB_DATABASE=<database_name>
DOCDB_TLS_CERT=<path_to_cert>  # For AWS DocumentDB
```

## Adapter Selection

Choose the right adapter for your use case:

| Adapter | Best For | Scalability | Dependencies |
|---------|----------|-------------|--------------|
| **SQLite** | Local development, single-worker | Single process | None (stdlib) |
| **Redis** | High-throughput, multi-worker | Horizontal scaling | redis>=5.0.0 |
| **MongoDB/DocumentDB** | AWS-native, distributed processing | Horizontal scaling | pymongo>=4.0.0 |

## Verifying Installation

Test that the package is correctly installed:

```python
import robocorp_adapters_custom

# Check version
print(f"Package version: {robocorp_adapters_custom.__version__}")

# Test imports
from robocorp_adapters_custom import (
    SQLiteAdapter,
    RedisAdapter,
    DocumentDBAdapter,
    get_adapter_instance,
)

print("Installation successful!")
```

## Troubleshooting

### Import Errors

If you encounter import errors:

```bash
# Verify installation
pip show robocorp-adapters-custom

# Reinstall if needed
pip uninstall robocorp-adapters-custom
pip install robocorp-adapters-custom
```

### Missing Optional Dependencies

If you get errors about missing Redis or MongoDB:

```bash
# Install the required optional dependencies
pip install robocorp-adapters-custom[redis]
pip install robocorp-adapters-custom[mongodb]
```

### Environment Variable Issues

Ensure all required environment variables are set:

```python
import os

# Check configuration
print("Adapter:", os.getenv("RC_WORKITEM_ADAPTER"))
print("DB Path:", os.getenv("RC_WORKITEM_DB_PATH"))
print("Queue Name:", os.getenv("RC_WORKITEM_QUEUE_NAME"))
```

## Uninstallation

To remove the package:

```bash
pip uninstall robocorp-adapters-custom
```

## Next Steps

- Read the [README.md](README.md) for architecture details
- Check [docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md](docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md) for implementation details
- See example configurations in `devdata/` directory

## Support

For issues and questions:
- GitHub Issues: https://github.com/joshyorko/robocorp_adapters_custom/issues
- Documentation: https://github.com/joshyorko/robocorp_adapters_custom
