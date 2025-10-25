# PR Strategy and Codebase Assessment

**Date:** October 25, 2025  
**Target:** robocorp/robocorp workitems library  
**Status:** Mapping Exercise - DO NOT SUBMIT YET

---

## Executive Summary

This document maps out a strategic, phased approach for contributing custom work item adapters to the Robocorp ecosystem. Based on analysis of the `robocorp/robocorp` repository structure and testing patterns, we've identified a minimal viable PR scope and complementary repository requirements.

---

## 1. Robocorp Workitems Repository Analysis

### 1.1 Core Structure

```
robocorp/robocorp/workitems/
├── src/robocorp/workitems/
│   ├── _adapters/
│   │   ├── __init__.py          # Adapter discovery and loading
│   │   ├── _base.py             # BaseAdapter abstract class
│   │   ├── _file.py             # FileAdapter (local dev)
│   │   └── _robocorp.py         # RobocorpAdapter (Control Room)
│   ├── _exceptions.py           # EmptyQueue, BusinessException, etc.
│   ├── _types.py                # State, JSONType, Email, etc.
│   ├── _utils.py                # Utility functions
│   └── __init__.py              # Public API
├── tests/
│   ├── conftest.py              # pytest fixtures
│   └── workitems_tests/
│       ├── fixtures.py          # Test fixtures
│       ├── mocks.py             # Mock adapters
│       ├── test_adapters.py     # Adapter tests ⭐
│       ├── test_workitems.py    # Integration tests
│       └── test_email.py        # Email functionality
├── docs/                        # User documentation
├── pyproject.toml               # Poetry dependencies
└── README.md
```

### 1.2 Key Integration Points

#### Adapter Discovery (`_adapters/__init__.py`)
```python
def create_adapter() -> BaseAdapter:
    """Resolve adapter from environment or auto-detect."""
    adapter = os.getenv("RC_WORKITEM_ADAPTER")
    if adapter:
        return _import_adapter(adapter)  # ← Our entry point
    else:
        return _detect_adapter()  # FileAdapter or RobocorpAdapter
```

**Finding:** Our adapters integrate via `RC_WORKITEM_ADAPTER` environment variable. No changes needed to Robocorp code.

#### Testing Pattern (`tests/workitems_tests/test_adapters.py`)
```python
class TestFileAdapter:
    @pytest.fixture
    def adapter(self, monkeypatch):
        # Sets up temp directories and env vars
        yield FileAdapter()
    
    def test_load_data(self, adapter):
        item_id = adapter.reserve_input()
        data = adapter.load_payload(item_id)
        assert data == {"a-key": "a-value"}
```

**Finding:** Tests use pytest fixtures with monkeypatch for environment variables. Our tests should follow this pattern.

#### Dependencies (`pyproject.toml`)
```toml
[tool.poetry.dependencies]
python = "^3.9.2"
robocorp-tasks = ">=1,<5"
requests = "^2.28.2"
tenacity = "^8.0.1"
dataclasses-json = "^0.6.1"
python-dateutil = "^2.8.2"
```

**Finding:** Core library has minimal dependencies. Our adapters add:
- SQLite: None (stdlib)
- Redis: `redis>=4.0.0`
- DocumentDB: `pymongo>=4.0.0`, `gridfs`

---

## 2. Current Codebase Inventory

### 2.1 Core Adapter Files (Essential for PR)

**Must Include:**
```
✅ sqlite_adapter.py              # 748 lines - Core SQLite implementation
✅ redis_adapter.py                # 813 lines - Core Redis implementation
✅ docdb_adapter.py                # 942 lines - Core DocumentDB implementation
✅ exceptions.py                   # 72 lines - Custom exceptions
✅ _utils.py                       # 230 lines - Shared utilities
```

**Status:** ✅ All aligned with Robocorp patterns (completed in previous phase)

### 2.2 Integration & Configuration (Essential for PR)

**Review Needed:**
```
⚠️  workitems_integration.py      # 184 lines - Dynamic adapter loading
⚠️  scripts/config.py              # Configuration utilities
```

**Analysis:**
- `workitems_integration.py` - Provides `get_adapter_instance()` helper
  - **Question:** Is this needed in Robocorp repo or user-facing?
  - **Recommendation:** Move to examples/templates repository
  
- `scripts/config.py` - Environment variable validation
  - **Question:** Needed for core library?
  - **Recommendation:** Keep minimal version, move comprehensive validation to examples

### 2.3 Testing & Validation (Not for Initial PR)

**Move to Separate Repositories:**
```
❌ scripts/seed_sqlite_db.py      # Test data seeding
❌ scripts/seed_redis_db.py        # Test data seeding
❌ scripts/seed_docdb_db.py        # Test data seeding
❌ scripts/check_sqlite_db.py     # Database diagnostics
❌ scripts/recover_orphaned_items.py  # Maintenance utility
❌ scripts/diagnose_reporter_issue.py # Debugging tool
```

**Rationale:** These are developer/ops tools, not library code. Better suited for example repositories.

### 2.4 Environment Configuration (Not for Initial PR)

**Move to Example Repositories:**
```
❌ devdata/                        # All env-*.json files
   ├── env-sqlite-producer.json
   ├── env-sqlite-consumer.json
   ├── env-redis-producer.json
   └── ... (14 total files)
```

**Rationale:** Environment configs are deployment-specific, not library code.

### 2.5 Workflow Definitions (Not for Initial PR)

**Move to Example Repositories:**
```
❌ yamls/robot.yaml                # RCC task definitions
❌ yamls/conda.yaml                # Python environment
```

**Rationale:** Task definitions belong in sample repositories, not core library.

### 2.6 Documentation (Mixed)

**Include in PR:**
```
✅ docs/ADAPTER_RESEARCH_SUMMARY.md      # Technical deep-dive
✅ docs/CUSTOM_WORKITEM_ADAPTER_GUIDE.md # Implementation guide
✅ ROBOCORP_ALIGNMENT.md                  # Alignment report (for review)
```

**Move to Examples:**
```
❌ docs/# Producer-Consumer Architecture Migrati.md  # Migration guide
```

---

## 3. Minimal PR Scope (Core Library Contribution)

### 3.1 Files for robocorp/robocorp PR

**Target Location:** `workitems/src/robocorp/workitems/_adapters/`

```
PR Files (Core Adapters):
├── _sqlite.py              # Renamed from sqlite_adapter.py
├── _redis.py               # Renamed from redis_adapter.py  
├── _docdb.py               # Renamed from docdb_adapter.py
└── _utils.py               # Shared utilities (merge or append)
```

**Additional Changes:**
```
workitems/src/robocorp/workitems/
├── _adapters/__init__.py   # Add imports (optional, for convenience)
└── _exceptions.py          # Potentially add our custom exceptions
```

**Documentation:**
```
workitems/docs/guides/
└── custom-adapters.md      # New: Usage guide for custom adapters
```

**Tests:**
```
workitems/tests/workitems_tests/
├── test_sqlite_adapter.py  # New: SQLite adapter tests
├── test_redis_adapter.py   # New: Redis adapter tests
└── test_docdb_adapter.py   # New: DocumentDB adapter tests
```

**Dependencies (pyproject.toml):**
```toml
[tool.poetry.group.dev.dependencies]
redis = {version = "^4.0.0", optional = true}
pymongo = {version = "^4.0.0", optional = true}
```

### 3.2 File Modifications Needed

#### File Renaming (Follow Robocorp Convention)
```bash
sqlite_adapter.py  →  _sqlite.py
redis_adapter.py   →  _redis.py
docdb_adapter.py   →  _docdb.py
```

**Rationale:** Prefix with `_` matches Robocorp's pattern (`_file.py`, `_robocorp.py`)

#### Import Path Updates
```python
# Before
from robocorp_adapters_custom.sqlite_adapter import SQLiteAdapter

# After (in robocorp repo)
from robocorp.workitems._adapters._sqlite import SQLiteAdapter
```

#### Remove Custom Integration Module
- Remove `workitems_integration.py` from core PR
- Users call adapters directly:
  ```python
  from robocorp.workitems._adapters._sqlite import SQLiteAdapter
  adapter = SQLiteAdapter()
  ```

### 3.3 What's NOT in Core PR

**Excluded from robocorp/robocorp:**
- ❌ All `scripts/` directory
- ❌ All `devdata/` directory  
- ❌ All `yamls/` directory
- ❌ `workitems_integration.py` (keep in examples)
- ❌ Migration guides (keep in examples)

---

## 4. Complementary Repository Strategy

### 4.1 Repository: `robocorp-adapter-examples`

**Purpose:** Complete working examples for each adapter type

**Structure:**
```
robocorp-adapter-examples/
├── sqlite-producer-consumer/
│   ├── robot.yaml
│   ├── conda.yaml
│   ├── tasks.py                 # Producer, Consumer, Reporter
│   ├── config.py                # Environment setup
│   ├── devdata/
│   │   ├── env-sqlite-producer.json
│   │   ├── env-sqlite-consumer.json
│   │   └── work-items-in/
│   ├── scripts/
│   │   ├── seed_db.py
│   │   ├── check_db.py
│   │   └── recover_orphans.py
│   └── README.md                # Complete setup guide
│
├── redis-distributed-processing/
│   ├── robot.yaml
│   ├── conda.yaml
│   ├── tasks.py
│   ├── docker-compose.yml       # Redis setup
│   ├── devdata/
│   └── README.md
│
├── documentdb-aws-deployment/
│   ├── robot.yaml
│   ├── conda.yaml
│   ├── tasks.py
│   ├── terraform/               # AWS infrastructure
│   ├── devdata/
│   └── README.md
│
└── README.md                    # Overview of all examples
```

**Content per Adapter:**
- Complete producer-consumer workflow
- Environment setup scripts
- Database seeding/maintenance tools
- Docker/cloud deployment configs
- Troubleshooting guides
- Performance tuning examples

### 4.2 Repository: `robocorp-adapter-templates`

**Purpose:** Quick-start templates for new projects

**Structure:**
```
robocorp-adapter-templates/
├── cookiecutter-sqlite/
│   ├── cookiecutter.json
│   └── {{cookiecutter.project_name}}/
│       ├── robot.yaml
│       ├── tasks.py
│       └── ...
│
├── cookiecutter-redis/
└── cookiecutter-docdb/
```

### 4.3 Repository: `robocorp-adapter-benchmarks`

**Purpose:** Performance comparison and optimization

**Structure:**
```
robocorp-adapter-benchmarks/
├── benchmarks/
│   ├── throughput_test.py
│   ├── latency_test.py
│   └── concurrency_test.py
├── results/
│   ├── 2025-10-25-results.json
│   └── comparison.md
└── README.md
```

---

## 5. Testing Strategy

### 5.1 Tests for Core PR (robocorp/robocorp)

**Follow Existing Pattern:**
```python
# workitems/tests/workitems_tests/test_sqlite_adapter.py

import tempfile
import pytest
from pathlib import Path

from robocorp.workitems._adapters._sqlite import SQLiteAdapter
from robocorp.workitems._exceptions import EmptyQueue


class TestSQLiteAdapter:
    @pytest.fixture
    def adapter(self, monkeypatch, tmp_path):
        db_path = tmp_path / "test.db"
        files_dir = tmp_path / "files"
        
        monkeypatch.setenv("RC_WORKITEM_DB_PATH", str(db_path))
        monkeypatch.setenv("RC_WORKITEM_FILES_DIR", str(files_dir))
        monkeypatch.setenv("RC_WORKITEM_QUEUE_NAME", "test_queue")
        
        yield SQLiteAdapter()
    
    def test_reserve_input_empty_queue(self, adapter):
        with pytest.raises(EmptyQueue):
            adapter.reserve_input()
    
    def test_create_and_reserve_input(self, adapter):
        # Create work item using seed_input (test helper)
        payload = {"test": "data"}
        item_id = adapter.seed_input(payload=payload)
        
        # Reserve it
        reserved_id = adapter.reserve_input()
        assert reserved_id == item_id
        
        # Load payload
        loaded = adapter.load_payload(reserved_id)
        assert loaded == payload
    
    def test_file_operations(self, adapter):
        item_id = adapter.seed_input(payload={})
        
        # Add file
        content = b"test content"
        adapter.add_file(item_id, "test.txt", content)
        
        # List files
        files = adapter.list_files(item_id)
        assert files == ["test.txt"]
        
        # Get file
        retrieved = adapter.get_file(item_id, "test.txt")
        assert retrieved == content
        
        # Remove file
        adapter.remove_file(item_id, "test.txt")
        assert adapter.list_files(item_id) == []
    
    def test_state_transitions(self, adapter):
        from robocorp.workitems._types import State
        
        item_id = adapter.seed_input(payload={})
        reserved_id = adapter.reserve_input()
        
        # Release as done
        adapter.release_input(reserved_id, State.DONE)
        
        # Should not be reservable again
        with pytest.raises(EmptyQueue):
            adapter.reserve_input()
```

**Test Coverage:**
- Basic CRUD operations
- State transitions
- File operations (add, get, remove)
- Empty queue handling
- Exception handling
- Concurrent access (SQLite WAL mode)
- Orphan recovery

### 5.2 Tests for Example Repositories

**Integration Tests:**
- Full producer-consumer workflows
- Multi-worker scenarios
- Failure recovery
- Performance benchmarks

---

## 6. Documentation Strategy

### 6.1 Core Library Documentation (in PR)

**File:** `workitems/docs/guides/custom-adapters.md`

**Content:**
```markdown
# Custom Work Item Adapters

## Overview
Work item adapters allow you to customize how robocorp-workitems stores and
retrieves work items. Three additional adapters are included:

- **SQLiteAdapter** - Local persistence
- **RedisAdapter** - Distributed processing
- **DocumentDBAdapter** - AWS-native storage

## Basic Usage

### SQLite Adapter
```python
import os
from robocorp.workitems._adapters._sqlite import SQLiteAdapter

os.environ["RC_WORKITEM_ADAPTER"] = "robocorp.workitems._adapters._sqlite.SQLiteAdapter"
os.environ["RC_WORKITEM_DB_PATH"] = "path/to/db.sqlite"

# Now use robocorp.workitems normally
from robocorp import workitems
for item in workitems.inputs:
    print(item.payload)
```

### Configuration

#### SQLite
- `RC_WORKITEM_DB_PATH` - Database file path (required)
- `RC_WORKITEM_FILES_DIR` - File storage directory
- `RC_WORKITEM_QUEUE_NAME` - Queue identifier

#### Redis
- `REDIS_HOST` - Redis server (default: localhost)
- `REDIS_PORT` - Port (default: 6379)
- `REDIS_PASSWORD` - Authentication

#### DocumentDB
- `DOCDB_URI` - Connection string
- `DOCDB_DATABASE` - Database name
- `DOCDB_TLS_CERT` - TLS certificate path

## Examples

For complete working examples, see:
- https://github.com/robocorp/robocorp-adapter-examples

## API Reference

All adapters implement the `BaseAdapter` interface...
```

### 6.2 Example Repository Documentation

**More Detailed:**
- Step-by-step setup
- Environment preparation
- Docker/cloud deployment
- Troubleshooting
- Performance tuning
- Migration from FileAdapter

---

## 7. Phased Rollout Plan

### Phase 1: Core Library PR (Week 1-2)

**Deliverables:**
- [ ] Rename adapter files with `_` prefix
- [ ] Update import paths
- [ ] Write unit tests matching Robocorp patterns
- [ ] Add custom-adapters.md documentation
- [ ] Update pyproject.toml with optional dependencies
- [ ] Submit PR to robocorp/robocorp

**Success Criteria:**
- All tests pass
- No breaking changes
- Code review approved
- CI/CD passes

### Phase 2: Example Repositories (Week 3-4)

**Deliverables:**
- [ ] Create `robocorp-adapter-examples` repo
- [ ] SQLite producer-consumer example
- [ ] Redis distributed processing example
- [ ] DocumentDB AWS deployment example
- [ ] Each with complete README and setup scripts

**Success Criteria:**
- Examples run successfully
- Clear documentation
- Reproducible setup

### Phase 3: Templates & Tools (Week 5-6)

**Deliverables:**
- [ ] Cookiecutter templates
- [ ] Benchmarking suite
- [ ] Migration tools
- [ ] Best practices guide

**Success Criteria:**
- Templates generate working projects
- Benchmarks provide actionable insights

### Phase 4: Community & Support (Ongoing)

**Deliverables:**
- [ ] Blog posts / tutorials
- [ ] Video walkthroughs
- [ ] Community forum support
- [ ] Gather feedback and iterate

---

## 8. Key Decisions & Questions

### 8.1 For Robocorp Team Discussion

**Q1: Custom Exceptions**
- Should `AdapterError`, `DatabaseTemporarilyUnavailable`, etc. be added to `_exceptions.py`?
- Or keep them adapter-specific in `_sqlite.py`, `_redis.py`?

**Recommendation:** Add to `_exceptions.py` as they're useful for any backend adapter.

**Q2: Utility Functions**
- Merge `_utils.py` content into existing `workitems/_utils.py`?
- Or keep separate as `_adapters/_utils.py`?

**Recommendation:** Keep separate as `_adapters/_utils.py` - these are adapter-specific utilities.

**Q3: seed_input() Method**
- This is a test helper not in BaseAdapter interface
- Keep it? Document as private (`_seed_input`)?

**Recommendation:** Keep as public method for developer testing, document clearly it's for testing only.

**Q4: Optional Dependencies**
- Make redis/pymongo optional dependencies?
- Or require them?

**Recommendation:** Optional - users only install what they need:
```bash
pip install robocorp-workitems[redis]
pip install robocorp-workitems[documentdb]
```

### 8.2 For Example Repository

**Q1: Where to Host?**
- Under `robocorp/` organization?
- Or separate community organization?

**Recommendation:** Under `robocorp/` for official examples, community org for contributions.

**Q2: License?**
- Same Apache 2.0 as core library?

**Recommendation:** Yes, consistent licensing.

---

## 9. Risk Assessment

### 9.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes in future Robocorp releases | High | Pin to specific robocorp-workitems version, comprehensive tests |
| Performance issues with large workloads | Medium | Benchmarking suite, performance documentation |
| Database migration failures | Medium | Robust migration testing, rollback procedures |
| Optional dependency conflicts | Low | Clear documentation, version pinning |

### 9.2 Adoption Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Developers prefer FileAdapter simplicity | Medium | Show concrete benefits in examples |
| Documentation insufficient | High | Comprehensive guides, video tutorials |
| Setup complexity | Medium | Templates and automation scripts |
| Limited Robocorp team capacity for review | High | Provide thorough documentation and tests |

---

## 10. Success Metrics

### 10.1 PR Acceptance
- [ ] Merged into robocorp/robocorp main branch
- [ ] No blocking issues in code review
- [ ] All CI/CD checks pass
- [ ] Documentation approved

### 10.2 Adoption (6 months post-release)
- [ ] 50+ GitHub stars on examples repository
- [ ] 10+ community contributions or issues
- [ ] 3+ blog posts or tutorials from community
- [ ] Featured in Robocorp documentation

### 10.3 Quality
- [ ] Zero critical bugs reported
- [ ] 95%+ test coverage
- [ ] Performance within 10% of FileAdapter
- [ ] Positive community feedback

---

## 11. Immediate Next Steps (This Week)

### Step 1: Prepare Core PR Files
```bash
# Create branch
git checkout -b feature/custom-adapters-core

# Rename files
mv sqlite_adapter.py _sqlite.py
mv redis_adapter.py _redis.py
mv docdb_adapter.py _docdb.py

# Update import statements in files
# sed commands or manual edits

# Move to correct location (simulate)
mkdir -p robocorp-pr-staging/workitems/src/robocorp/workitems/_adapters/
cp _sqlite.py _redis.py _docdb.py _utils.py exceptions.py \
   robocorp-pr-staging/workitems/src/robocorp/workitems/_adapters/
```

### Step 2: Write Unit Tests
```bash
# Create test files following Robocorp patterns
touch robocorp-pr-staging/workitems/tests/workitems_tests/test_sqlite_adapter.py
touch robocorp-pr-staging/workitems/tests/workitems_tests/test_redis_adapter.py
touch robocorp-pr-staging/workitems/tests/workitems_tests/test_docdb_adapter.py
```

### Step 3: Write Documentation
```bash
# Create custom adapters guide
touch robocorp-pr-staging/workitems/docs/guides/custom-adapters.md
```

### Step 4: Review with Team
- [ ] Internal code review
- [ ] Test coverage review
- [ ] Documentation review
- [ ] Alignment with Robocorp roadmap

### Step 5: Fork and PR (Next Week)
```bash
# Fork robocorp/robocorp
# Apply changes
# Submit PR with detailed description
```

---

## 12. Appendix: File-by-File Analysis

### Essential for PR ✅

| File | Lines | Purpose | Disposition |
|------|-------|---------|-------------|
| `sqlite_adapter.py` | 748 | SQLite adapter | Rename to `_sqlite.py`, include |
| `redis_adapter.py` | 813 | Redis adapter | Rename to `_redis.py`, include |
| `docdb_adapter.py` | 942 | DocumentDB adapter | Rename to `_docdb.py`, include |
| `exceptions.py` | 72 | Custom exceptions | Merge into `_exceptions.py` or keep separate |
| `_utils.py` | 230 | Shared utilities | Keep as `_adapters/_utils.py` |

### Move to Examples ⚠️

| File | Lines | Purpose | Disposition |
|------|-------|---------|-------------|
| `workitems_integration.py` | 184 | Adapter loading helper | Move to examples (not needed in core) |
| `scripts/config.py` | ~200 | Config validation | Move to examples |
| `scripts/seed_*.py` | ~150 each | Database seeding | Move to examples |
| `scripts/check_*.py` | ~100 each | Diagnostics | Move to examples |
| `scripts/recover_*.py` | ~150 | Maintenance | Move to examples |

### Not for PR ❌

| Directory/File | Count | Purpose | Disposition |
|----------------|-------|---------|-------------|
| `devdata/` | 14 files | Environment configs | Move to examples |
| `yamls/` | 2 files | RCC task definitions | Move to examples |
| `docs/migration.md` | 1 | Migration guide | Move to examples |

---

## Conclusion

**Core PR Scope:**
- ✅ 3 adapter files (~2,500 lines)
- ✅ Shared utilities (~300 lines)
- ✅ Unit tests (~1,000 lines)
- ✅ Documentation (~500 lines)
- **Total:** ~4,300 lines of well-tested, documented code

**Complementary Repositories:**
- ⚠️ robocorp-adapter-examples (complete workflows)
- ⚠️ robocorp-adapter-templates (quick-start)
- ⚠️ robocorp-adapter-benchmarks (performance)

**Timeline:**
- Week 1-2: Core PR preparation and submission
- Week 3-4: Example repositories
- Week 5-6: Templates and tools
- Ongoing: Community support

**Status:** ✅ Ready to proceed with core PR preparation

---

**Next Action:** Create `robocorp-pr-staging/` directory structure and begin file preparation.

**Author:** Adapter Development Team  
**Last Updated:** October 25, 2025  
**Review Status:** Awaiting team discussion on key decisions
