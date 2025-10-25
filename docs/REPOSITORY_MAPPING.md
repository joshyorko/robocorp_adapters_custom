# Repository Structure Mapping

## Current State (All-in-One)

```
robocorp_adapters_custom/ (This Repo)
├── Core Adapters (For PR) ✅
│   ├── sqlite_adapter.py
│   ├── redis_adapter.py
│   ├── docdb_adapter.py
│   ├── exceptions.py
│   └── _utils.py
│
├── Integration (Review Needed) ⚠️
│   ├── workitems_integration.py
│   └── scripts/config.py
│
├── Testing Tools (Move to Examples) ❌
│   └── scripts/
│       ├── seed_sqlite_db.py
│       ├── seed_redis_db.py
│       ├── seed_docdb_db.py
│       ├── check_sqlite_db.py
│       ├── recover_orphaned_items.py
│       └── diagnose_reporter_issue.py
│
├── Environment Configs (Move to Examples) ❌
│   └── devdata/
│       ├── env-sqlite-producer.json
│       ├── env-sqlite-consumer.json
│       └── ... (14 files total)
│
├── Workflow Definitions (Move to Examples) ❌
│   └── yamls/
│       ├── robot.yaml
│       └── conda.yaml
│
└── Documentation ℹ️
    ├── README.md
    ├── ROBOCORP_ALIGNMENT.md
    ├── PR_CHECKLIST.md
    ├── PR_STRATEGY.md
    └── docs/
        ├── ADAPTER_RESEARCH_SUMMARY.md
        ├── CUSTOM_WORKITEM_ADAPTER_GUIDE.md
        └── # Producer-Consumer Architecture Migrati.md
```

---

## Future State (Multi-Repo Strategy)

### Repository 1: robocorp/robocorp (Core Library)

```
workitems/
├── src/robocorp/workitems/_adapters/
│   ├── _base.py
│   ├── _file.py
│   ├── _robocorp.py
│   ├── _sqlite.py        ← NEW
│   ├── _redis.py         ← NEW
│   ├── _docdb.py         ← NEW
│   └── _utils.py         ← NEW (or merged)
│
├── src/robocorp/workitems/
│   └── _exceptions.py    ← Add custom exceptions
│
├── tests/workitems_tests/
│   ├── test_sqlite_adapter.py  ← NEW
│   ├── test_redis_adapter.py   ← NEW
│   └── test_docdb_adapter.py   ← NEW
│
├── docs/guides/
│   └── custom-adapters.md      ← NEW
│
└── pyproject.toml        ← Add optional dependencies
```

**Content:** Pure library code, minimal dependencies

---

### Repository 2: robocorp-adapter-examples

```
robocorp-adapter-examples/
├── sqlite-producer-consumer/
│   ├── robot.yaml
│   ├── conda.yaml
│   ├── tasks.py
│   ├── config.py
│   ├── devdata/
│   │   ├── env-sqlite-producer.json
│   │   ├── env-sqlite-consumer.json
│   │   └── work-items-in/
│   ├── scripts/
│   │   ├── seed_db.py
│   │   ├── check_db.py
│   │   └── recover_orphans.py
│   └── README.md
│
├── redis-distributed-processing/
│   ├── robot.yaml
│   ├── tasks.py
│   ├── docker-compose.yml
│   ├── devdata/
│   └── README.md
│
├── documentdb-aws-deployment/
│   ├── robot.yaml
│   ├── tasks.py
│   ├── terraform/
│   ├── devdata/
│   └── README.md
│
└── README.md
```

**Content:** Complete working examples, deployment configs

---

### Repository 3: robocorp-adapter-templates

```
robocorp-adapter-templates/
├── cookiecutter-sqlite/
│   └── {{cookiecutter.project_name}}/
│       ├── robot.yaml
│       ├── tasks.py
│       └── ...
│
├── cookiecutter-redis/
└── cookiecutter-docdb/
```

**Content:** Project templates for quick starts

---

### Repository 4: robocorp-adapter-benchmarks

```
robocorp-adapter-benchmarks/
├── benchmarks/
│   ├── throughput_test.py
│   ├── latency_test.py
│   └── concurrency_test.py
├── results/
└── README.md
```

**Content:** Performance testing and comparisons

---

## File Migration Map

### From robocorp_adapters_custom → robocorp/robocorp

| Source File | Destination | Action |
|-------------|-------------|--------|
| `sqlite_adapter.py` | `_adapters/_sqlite.py` | Rename, update imports |
| `redis_adapter.py` | `_adapters/_redis.py` | Rename, update imports |
| `docdb_adapter.py` | `_adapters/_docdb.py` | Rename, update imports |
| `_utils.py` | `_adapters/_utils.py` | Copy or merge |
| `exceptions.py` | `_exceptions.py` | Merge |
| Unit tests (new) | `tests/workitems_tests/` | Create new |
| Docs (new) | `docs/guides/` | Create new |

### From robocorp_adapters_custom → robocorp-adapter-examples

| Source Files | Destination | Notes |
|-------------|-------------|-------|
| `scripts/seed_*.py` | `sqlite-producer-consumer/scripts/` | Per adapter |
| `scripts/check_*.py` | `*/scripts/` | Diagnostic tools |
| `scripts/recover_*.py` | `*/scripts/` | Maintenance |
| `devdata/*.json` | `*/devdata/` | Environment configs |
| `yamls/*.yaml` | `*/` | Task definitions |
| `docs/migration.md` | Root or per-adapter | Migration guides |

### Not Needed Anywhere

| Files | Reason |
|-------|--------|
| `workitems_integration.py` | Users call adapters directly |
| `scripts/config.py` | Validation logic in adapters |
| Development artifacts | CI/CD, IDE configs |

---

## Dependency Tree

```
robocorp-workitems (PyPI)
├── Core dependencies
│   ├── robocorp-tasks
│   ├── requests
│   ├── tenacity
│   └── dataclasses-json
│
└── Optional (extras)
    ├── [redis] → redis>=4.0.0
    ├── [documentdb] → pymongo>=4.0.0, gridfs
    └── [all] → all optional dependencies

Installation:
  pip install robocorp-workitems           # Core only
  pip install robocorp-workitems[redis]    # + Redis
  pip install robocorp-workitems[all]      # All adapters
```

---

## Integration Flow

```
User Project
    │
    ├─→ robot.yaml
    │   └─→ tasks: [Producer, Consumer, Reporter]
    │
    ├─→ Environment Variable
    │   └─→ RC_WORKITEM_ADAPTER="robocorp.workitems._adapters._sqlite.SQLiteAdapter"
    │
    ├─→ robocorp-workitems (from PyPI)
    │   └─→ _adapters/__init__.py
    │       └─→ create_adapter()
    │           └─→ _import_adapter()
    │               └─→ SQLiteAdapter()  ← Instantiated
    │
    └─→ tasks.py
        └─→ from robocorp import workitems
            └─→ for item in workitems.inputs:  ← Uses custom adapter
```

---

## Testing Strategy per Repository

### Core Library (robocorp/robocorp)
```
Unit Tests:
├── Adapter interface compliance
├── State transitions
├── File operations
├── Exception handling
└── Empty queue scenarios

Test Tools:
├── pytest fixtures
├── monkeypatch for env vars
├── tempfile for isolation
└── Mock for external services
```

### Example Repositories
```
Integration Tests:
├── Full producer-consumer flows
├── Multi-worker scenarios
├── Failure recovery
└── Performance benchmarks

Test Data:
├── Realistic payloads
├── File attachments
└── Edge cases
```

---

## PR Submission Sequence

```
Week 1-2: Core Library PR
    ├─→ Fork robocorp/robocorp
    ├─→ Create feature branch
    ├─→ Add adapter files
    ├─→ Write unit tests
    ├─→ Add documentation
    ├─→ Submit PR
    └─→ Address review feedback

Week 3-4: Examples Repository
    ├─→ Create robocorp-adapter-examples
    ├─→ SQLite example
    ├─→ Redis example
    ├─→ DocumentDB example
    └─→ Link from core library docs

Week 5-6: Templates & Benchmarks
    ├─→ Create template repositories
    └─→ Set up benchmark suite

Ongoing: Community Support
    ├─→ Answer issues
    ├─→ Merge contributions
    └─→ Update documentation
```

---

## Success Criteria Checklist

### Core Library PR
- [ ] All files follow Robocorp naming conventions
- [ ] Import paths use robocorp.workitems namespace
- [ ] Unit tests achieve 95%+ coverage
- [ ] Documentation is clear and complete
- [ ] No breaking changes to existing code
- [ ] CI/CD pipeline passes
- [ ] Code review approved

### Example Repositories
- [ ] Each example runs successfully
- [ ] Clear setup instructions
- [ ] Docker/cloud configs work
- [ ] READMEs are comprehensive
- [ ] Troubleshooting guides included

### Community Adoption
- [ ] GitHub stars/forks
- [ ] Community contributions
- [ ] Blog posts/tutorials
- [ ] Positive feedback

---

## Key Decision Points

### 1. File Naming
**Decision:** Use `_` prefix for adapter files  
**Rationale:** Matches Robocorp pattern (`_file.py`, `_robocorp.py`)

### 2. Import Strategy
**Decision:** Users import directly from `_adapters`  
**Rationale:** Simple, explicit, no magic

### 3. Exception Handling
**Decision:** Add custom exceptions to `_exceptions.py`  
**Rationale:** Reusable across adapters

### 4. Testing Approach
**Decision:** Follow FileAdapter test patterns  
**Rationale:** Consistency, easier review

### 5. Documentation Location
**Decision:** Core guide in library, detailed examples in separate repos  
**Rationale:** Keep library docs minimal, examples comprehensive

---

## Contact & Next Steps

**This Week:**
1. Review this mapping with team
2. Discuss key decisions
3. Create PR staging directory
4. Begin file preparation

**Questions?**
- See PR_STRATEGY.md for detailed analysis
- Check ROBOCORP_ALIGNMENT.md for code patterns
- Review PR_CHECKLIST.md for readiness status

**Status:** ✅ Mapping complete, ready for team review

**Last Updated:** October 25, 2025
