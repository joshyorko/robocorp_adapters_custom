# Fizzy/Codex Work Item Orchestration

This repository can use Robocorp work item adapters as a durable execution queue for Fizzy-backed coding work. Fizzy remains the board and source of truth. The adapter stores queued execution units. The worker runner is configurable and can be Codex or another command.

## Payload Contract

Each queued card is normalized into this payload shape:

```json
{
  "source": "fizzy",
  "card": {
    "id": "card-id",
    "number": 579,
    "title": "Implement feature",
    "description": "...",
    "url": "https://example.test/cards/579",
    "board_id": "board-id",
    "column_id": "column-id",
    "state": "Ready for Agents",
    "labels": [],
    "branch_name": ""
  },
  "workflow": {
    "prompt_template": "Complete this Fizzy card...",
    "allowed_paths": ["robocorp_adapters_custom/", "workitems_tests/"],
    "handoff_column": "Synthesize & Verify",
    "handoff_column_id": ""
  },
  "runner": {
    "kind": "codex",
    "command": "codex exec --json"
  }
}
```

The helper API is in `robocorp_adapters_custom.fizzy_orchestration`.

## Three-Stage Flow

1. Producer: calls the local `fizzy` CLI, normalizes cards, and seeds input work items.
2. Worker: reserves one work item, runs the configured command, stores stdout/stderr as attachments, and creates a result work item.
3. Reporter: consumes result work items, posts proof back through the local `fizzy` CLI, and optionally moves the card to a handoff column.

The integration intentionally does not call Fizzy HTTP APIs directly.

## SQLite Local Example

Install dev dependencies first:

```sh
python -m pip install -e ".[dev]"
```

Set real board values in your shell, not in committed sample files:

```sh
export FIZZY_BOARD_ID="<board-id>"
export FIZZY_SOURCE_COLUMN_ID="<ready-column-id>"
export FIZZY_HANDOFF_COLUMN_ID="<handoff-column-id>"
```

Seed cards into SQLite:

```sh
python scripts/fizzy_seed_sqlite.py --env devdata/env-fizzy-sqlite-producer.json
```

Run one worker locally with the safe placeholder command from the sample env:

```sh
python scripts/fizzy_worker_once.py --env devdata/env-fizzy-sqlite-worker.json
```

Report one result in dry-run mode:

```sh
python scripts/fizzy_reporter_once.py --env devdata/env-fizzy-sqlite-reporter.json --dry-run
```

Equivalent RCC tasks are available in `yamls/robot.yaml` as `FizzyProducer`, `FizzyWorker`, and `FizzyReporterDryRun`.

## Idempotency

For SQLite, `enqueue_fizzy_cards()` prevents duplicate queue entries by matching `source=fizzy`, `card.board_id`, and `card.number` in the current input queue. Use `--force` on `scripts/fizzy_seed_sqlite.py` only when intentionally re-queuing the same card.

## Result Propagation

Successful worker runs mark the reserved input as `COMPLETED`; failing runs mark it as `FAILED` with exception type `APPLICATION`, the runner return code, and a short stderr/stdout message. Both paths create a worker result output item so a reporter can publish proof back to Fizzy.
