# Work Item Adapter Research Summary

**Date**: October 11, 2025  
**Objective**: Research Robocorp workitems adapter architecture for custom backend integration

---

## Key Findings

### 1. Adapter Architecture

Robocorp workitems library uses a **pluggable adapter pattern** allowing custom backend integration:

```python
from robocorp.workitems._adapters._base import BaseAdapter

class CustomAdapter(BaseAdapter):
    # Implement 9 required methods
    pass
```

### 2. Built-in Adapters

| Adapter | Purpose | Location |
|---------|---------|----------|
| **FileAdapter** | Local file-based simulation | `_adapters/_file.py` |
| **RobocorpAdapter** | Production Control Room integration | `_adapters/_robocorp.py` |

### 3. Required Interface Methods

All custom adapters must implement these 9 methods:

1. `reserve_input()` - Get next work item from queue
2. `release_input()` - Release work item with status
3. `create_output()` - Create new output work item
4. `load_payload()` - Load JSON payload
5. `save_payload()` - Save JSON payload
6. `list_files()` - List attached files
7. `get_file()` - Get file content
8. `add_file()` - Add file attachment
9. `remove_file()` - Remove file attachment

### 4. Adapter Registration

**Method 1: Environment Variable** (Recommended)
```json
{
  "RC_WORKITEM_ADAPTER": "module.path.YourAdapter"
}
```

**Method 2: Direct Import**
```python
import os
os.environ["RC_WORKITEM_ADAPTER"] = "module.path.YourAdapter"
from robocorp import workitems
```

### 5. Backend Options for LinkedIn Bot

Based on the research, here are viable backends ranked by complexity:

#### Tier 1: Simple (Start Here)
- **SQLite**: Single file database, perfect for local/small scale
- **FileAdapter**: Already working, continue using for development

#### Tier 2: Distributed
- **Redis**: In-memory queue, excellent for speed
- **PostgreSQL**: Robust SQL database with ACID guarantees
- **MongoDB**: Document store, good for flexible schemas

#### Tier 3: Enterprise
- **RabbitMQ + Celery**: Full-featured message broker
- **AWS SQS/SNS**: Cloud-native queuing
- **Apache Kafka**: High-throughput event streaming

---

## Implementation Roadmap

### Phase 1: Proof of Concept (Current - Week 1)
- ✅ **FileAdapter** working with local JSON files
- ✅ Documented producer-consumer pattern
- ✅ Researched adapter architecture
- 🔲 Implement SQLiteAdapter for local persistence

### Phase 2: Database Integration (Week 2)
- 🔲 Create SQLiteAdapter with full BaseAdapter interface
- 🔲 Migrate existing SQLite schema to work with adapter
- 🔲 Test producer-consumer with SQLite backend
- 🔲 Add connection pooling and error handling

### Phase 3: Distributed Queue (Week 3-4)
- 🔲 Implement RedisAdapter for distributed processing
- 🔲 Add Redis to docker-compose
- 🔲 Test parallel consumer workers
- 🔲 Benchmark performance vs SQLite

### Phase 4: Production Ready (Week 5-6)
- 🔲 Choose final backend (Redis or PostgreSQL)
- 🔲 Implement retry logic and dead-letter queues
- 🔲 Add monitoring and metrics
- 🔲 Docker deployment with scaling
- 🔲 CI/CD integration

---

## Recommended: SQLiteAdapter First

**Why SQLite?**
1. ✅ Already using SQLite for job storage
2. ✅ No additional infrastructure needed
3. ✅ ACID transactions for reliability
4. ✅ Can handle 10k+ work items easily
5. ✅ Easy to migrate to PostgreSQL later
6. ✅ Supports concurrent reads
7. ✅ File-based = easy backup/restore

**Implementation Plan:**

```python
# robocorp_adapters_custom/sqlite_adapter.py

class SQLiteAdapter(BaseAdapter):
    def __init__(self):
        self.db = sqlite3.connect("linkedin_jobs.db")
        self._init_work_items_table()
    
    def _init_work_items_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                queue TEXT,
                payload JSON,
                state TEXT,
                created_at TIMESTAMP
            )
        """)
```

**Usage:**

```json
{
  "RC_WORKITEM_ADAPTER": "robocorp_adapters_custom.sqlite_adapter.SQLiteAdapter",
  "RC_WORKITEM_DB_PATH": "src/linkedin_jobs.sqlite",
  "RC_WORKITEM_QUEUE_NAME": "linkedin_jobs"
}
```

---

## Code Examples Created

1. **SQLiteAdapter** - Full implementation with file storage
2. **RedisAdapter** - Redis-based queue with pub/sub
3. **CeleryAdapter** - RabbitMQ + Celery integration
4. **Unit tests** - pytest fixtures and test cases
5. **Docker compose** - Multi-service deployment

All examples are in: `/docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md`

---

## Next Actions

1. **Create SQLiteAdapter** in `src/robocorp_adapters_custom/`
2. **Test with existing workflow**: SearchProducer → AIConsumer
3. **Benchmark performance**: Compare FileAdapter vs SQLiteAdapter
4. **Update documentation**: Add adapter usage to main README
5. **Prepare for Redis**: Research connection pooling and clustering

---

## Resources

- 📚 [Custom Adapter Guide](./CUSTOM_WORKITEM_ADAPTER_GUIDE.md) - Full implementation details
- 📚 [File Adapter Spec](./PRODUCER_CONSUMER_FILE_ADAPTER_SPEC.md) - Current working pattern
- 🔗 [Robocorp Repository](https://github.com/robocorp/robocorp/tree/master/workitems)
- 🔗 [BaseAdapter Source](https://github.com/robocorp/robocorp/blob/master/workitems/src/robocorp/workitems/_adapters/_base.py)

---

## Questions Answered

✅ **How does Robocorp handle different backends?**
- Pluggable adapter pattern via BaseAdapter interface

✅ **What adapters are available?**
- FileAdapter (local), RobocorpAdapter (cloud), custom (implement BaseAdapter)

✅ **How to create custom adapter?**
- Inherit BaseAdapter, implement 9 methods, register via env var

✅ **Best backend for LinkedIn bot?**
- Start: SQLite (simple, integrated)
- Scale: Redis (distributed, fast)
- Enterprise: RabbitMQ + Celery

✅ **How to integrate with existing DB?**
- SQLiteAdapter can use existing `linkedin_jobs.sqlite` database

---

## Success Criteria

- [x] Understand adapter architecture
- [x] Identify available adapters
- [x] Document BaseAdapter interface
- [x] Create implementation examples
- [ ] Implement SQLiteAdapter
- [ ] Test with LinkedIn workflow
- [ ] Deploy with RCC

**Status**: Research Complete ✅  
**Next Step**: Implement SQLiteAdapter
