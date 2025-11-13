# Yorko Control Room Adapter Guide

## Overview

The `YorkoControlRoomAdapter` enables Robocorp robots to connect to your self-hosted Yorko Control Room backend via HTTP REST API. This adapter provides the same interface as Robocorp's official `RobocorpAdapter` but connects to your custom Control Room implementation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                YORKO CONTROL ROOM BACKEND                   │
│  (FastAPI + PostgreSQL + Redis)                            │
│                                                             │
│  APIs:                                                      │
│  - GET  /api/v1/workspaces/{id}/work-items/next           │
│  - POST /api/v1/workspaces/{id}/work-items/{id}/complete  │
│  - POST /api/v1/workspaces/{id}/work-items/{id}/fail      │
│  - GET  /api/v1/workspaces/{id}/work-items/{id}           │
│  - PATCH /api/v1/workspaces/{id}/work-items/{id}          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                            │ HTTP/REST + Bearer Token Auth
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    ┌───────┐           ┌───────┐          ┌───────┐
    │Robot 1│           │Robot 2│          │Robot 3│
    └───────┘           └───────┘          └───────┘
    YorkoControlRoomAdapter  ↑              ↑
    in each robot           │              │
```

## Features

- ✅ **RESTful API Integration**: Communicates with Yorko Control Room via HTTP
- ✅ **Authentication**: Bearer token authentication for secure access
- ✅ **Work Item Lifecycle**: Complete support for reserve, load, save, release
- ✅ **Output Work Items**: Create output work items linked to parent inputs
- ✅ **File Attachments**: Upload/download files (requires backend implementation)
- ✅ **Error Handling**: Automatic retries for transient failures
- ✅ **Multi-Workspace**: Support for multiple isolated workspaces
- ✅ **Worker Identification**: Each robot instance has unique worker ID

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `RC_WORKITEM_ADAPTER` | Full path to adapter class | `robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter` |
| `YORKO_API_URL` | Base URL of Yorko Control Room | `https://control-room.example.com` or `http://localhost:8000` |
| `YORKO_API_TOKEN` | API authentication token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `YORKO_WORKSPACE_ID` | Workspace UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `YORKO_WORKER_ID` | Unique worker/robot identifier | `robot-prod-worker-1` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `YORKO_PROCESS_RUN_ID` | Process run UUID for tracking | None |
| `YORKO_REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `30` |

## Quick Start

### 1. Install Dependencies

```bash
pip install robocorp-workitems requests
```

### 2. Configure Environment

Create a file `devdata/env-yorko.json`:

```json
{
  "RC_WORKITEM_ADAPTER": "robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter",
  "YORKO_API_URL": "http://localhost:8000",
  "YORKO_API_TOKEN": "your-api-token",
  "YORKO_WORKSPACE_ID": "your-workspace-id",
  "YORKO_WORKER_ID": "my-robot-1"
}
```

### 3. Use in Robot Code

```python
from robocorp.workitems import Inputs, Outputs

def process_work_items():
    """Process work items from Yorko Control Room."""
    for item in Inputs:
        # Get payload data
        data = item.payload
        
        print(f"Processing work item: {data}")
        
        # Do your work here
        result = process_data(data)
        
        # Save results to payload
        item.payload["result"] = result
        item.save()
        
        # Create output work item
        Outputs.create(payload={"processed": True, "result": result})

if __name__ == "__main__":
    process_work_items()
```

### 4. Run with RCC

```bash
rcc run -t MyTask -e devdata/env-yorko.json
```

## API Mapping

The adapter translates `BaseAdapter` methods to Control Room API calls:

| Adapter Method | HTTP Request | Endpoint |
|----------------|--------------|----------|
| `reserve_input()` | `GET` | `/api/v1/workspaces/{id}/work-items/next?worker_id={worker}` |
| `load_payload(item_id)` | `GET` | `/api/v1/workspaces/{id}/work-items/{item_id}` |
| `save_payload(item_id, payload)` | `PATCH` | `/api/v1/workspaces/{id}/work-items/{item_id}` |
| `release_input(item_id, DONE)` | `POST` | `/api/v1/workspaces/{id}/work-items/{item_id}/complete` |
| `release_input(item_id, FAILED, exc)` | `POST` | `/api/v1/workspaces/{id}/work-items/{item_id}/fail` |
| `create_output(parent_id, payload)` | `POST` | `/api/v1/workspaces/{id}/work-items` |

## File Handling

File attachment support requires additional backend implementation. The adapter provides methods for:

- `list_files(item_id)` - List files attached to work item
- `get_file(item_id, name)` - Download a file
- `add_file(item_id, name, content)` - Upload a file
- `remove_file(item_id, name)` - Delete a file

**Note**: Your Control Room backend needs to implement file endpoints:
- `GET /api/v1/workspaces/{id}/work-items/{item_id}/files/{name}`
- `POST /api/v1/workspaces/{id}/work-items/{item_id}/files`
- `DELETE /api/v1/workspaces/{id}/work-items/{item_id}/files/{name}`

## Authentication

The adapter uses Bearer token authentication. Obtain an API token from your Control Room:

1. Log into Yorko Control Room web interface
2. Navigate to **Workspace Settings** → **API Keys**
3. Create a new API key with appropriate permissions
4. Copy the token and set it in `YORKO_API_TOKEN`

## Error Handling

The adapter includes automatic retry logic for transient failures:

- **Retry Strategy**: 3 attempts with exponential backoff
- **Retry Status Codes**: 429, 500, 502, 503, 504
- **Timeout**: Configurable via `YORKO_REQUEST_TIMEOUT` (default 30s)

## Production Deployment

### 1. Use HTTPS

Always use HTTPS in production:

```json
{
  "YORKO_API_URL": "https://control-room.example.com"
}
```

### 2. Secure Token Storage

Store API tokens securely:
- Use environment variables (not hardcoded)
- Use secret managers (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotate tokens regularly

### 3. Worker Identification

Use meaningful worker IDs for debugging:

```json
{
  "YORKO_WORKER_ID": "robot-prod-worker-1-us-east-1"
}
```

### 4. Monitoring

Monitor adapter health:
- Check HTTP response times
- Monitor error rates
- Track work item throughput
- Alert on queue backlogs

## Comparison with Other Adapters

| Feature | YorkoControlRoomAdapter | SQLiteAdapter | RedisAdapter | DocumentDBAdapter |
|---------|------------------------|---------------|--------------|-------------------|
| **Connection** | HTTP REST API | Local file | Redis protocol | MongoDB protocol |
| **Authentication** | Bearer token | None | Optional | Username/password |
| **Multi-workspace** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Distributed** | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Access Control** | ✅ Backend enforced | ❌ No | ❌ No | ⚠️ Database level |
| **Centralized Queue** | ✅ Yes | ❌ No | ⚠️ Shared Redis | ⚠️ Shared DB |
| **Use Case** | Production robots | Local dev | Distributed queue | AWS/cloud |

## Troubleshooting

### Connection Refused

```
ConnectionError: Failed to connect to http://localhost:8000
```

**Solution**: Verify Control Room backend is running and accessible.

### 401 Unauthorized

```
HTTPError: 401 Client Error: Unauthorized
```

**Solution**: Check `YORKO_API_TOKEN` is valid and not expired.

### 404 Workspace Not Found

```
HTTPError: 404 Client Error: Not Found
```

**Solution**: Verify `YORKO_WORKSPACE_ID` is correct.

### Empty Queue

```
EmptyQueue: No work items available in the queue
```

**Solution**: This is expected when queue is empty. Create work items in Control Room.

## Example: Complete Producer-Consumer

### Producer Robot

```python
# producer.py
from robocorp.workitems import Outputs

def produce_work_items():
    """Create work items for processing."""
    items = [
        {"order_id": "ORD-001", "customer": "Alice"},
        {"order_id": "ORD-002", "customer": "Bob"},
        {"order_id": "ORD-003", "customer": "Charlie"},
    ]
    
    for item_data in items:
        output = Outputs.create(payload=item_data)
        print(f"Created work item: {output.id}")

if __name__ == "__main__":
    produce_work_items()
```

### Consumer Robot

```python
# consumer.py
from robocorp.workitems import Inputs

def consume_work_items():
    """Process work items from queue."""
    for item in Inputs:
        try:
            payload = item.payload
            order_id = payload["order_id"]
            customer = payload["customer"]
            
            print(f"Processing order {order_id} for {customer}")
            
            # Do processing...
            result = process_order(order_id, customer)
            
            # Save result
            item.payload["status"] = "completed"
            item.payload["result"] = result
            item.save()
            
        except Exception as e:
            print(f"Failed to process item: {e}")
            item.fail(exception=str(e))

if __name__ == "__main__":
    consume_work_items()
```

## Next Steps

1. **Backend Implementation**: Ensure your Control Room backend implements all required endpoints
2. **File Support**: Add file upload/download endpoints if needed
3. **Testing**: Test with example producer-consumer workflows
4. **Monitoring**: Set up logging and metrics
5. **Production**: Deploy with HTTPS and secure token management

## References

- [Robocorp Workitems Documentation](https://robocorp.com/docs/development-guide/control-room/work-items)
- [BaseAdapter Interface](./CUSTOM_WORKITEM_ADAPTER_GUIDE.md#baseadapter-interface)
- [Yorko Control Room API Documentation](../../backend/python/README.md)
