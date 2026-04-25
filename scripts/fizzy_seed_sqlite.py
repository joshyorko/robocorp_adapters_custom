#!/usr/bin/env python3
"""Seed Fizzy cards into a SQLite-backed work item queue."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from robocorp_adapters_custom.fizzy_orchestration import (  # noqa: E402
    enqueue_fizzy_cards,
    list_fizzy_cards,
)
from robocorp_adapters_custom.workitems_integration import initialize_adapter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="devdata/env-fizzy-sqlite-producer.json")
    parser.add_argument("--board", default="")
    parser.add_argument("--column", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    board_id, column_id = _resolve_runtime_options(args)
    if not board_id:
        raise SystemExit("FIZZY_BOARD_ID or --board is required")

    cards = list_fizzy_cards(board_id)
    if column_id:
        cards = [
            card
            for card in cards
            if (card.get("column") or {}).get("id") == column_id
            or card.get("column_id") == column_id
        ]

    adapter = initialize_adapter()
    workflow = {
        "prompt_template": os.getenv(
            "FIZZY_PROMPT_TEMPLATE",
            "Complete this Fizzy card and return concise proof of the result.",
        ),
        "allowed_paths": _json_env("FIZZY_ALLOWED_PATHS", []),
        "handoff_column": os.getenv("FIZZY_HANDOFF_COLUMN", "Synthesize & Verify"),
        "handoff_column_id": os.getenv("FIZZY_HANDOFF_COLUMN_ID", ""),
    }
    runner = {
        "kind": os.getenv("FIZZY_RUNNER_KIND", "codex"),
        "command": os.getenv("FIZZY_RUNNER_COMMAND", "codex exec --json"),
    }

    results = enqueue_fizzy_cards(
        adapter,
        cards,
        workflow=workflow,
        runner=runner,
        force=args.force,
    )
    print(json.dumps({"board_id": board_id, "results": results}, indent=2))
    return 0


def _resolve_runtime_options(args: argparse.Namespace) -> tuple[str, str]:
    _load_env(args.env)
    board_id = args.board or os.getenv("FIZZY_BOARD_ID", "")
    column_id = args.column or os.getenv("FIZZY_SOURCE_COLUMN_ID", "")
    return board_id, column_id


def _load_env(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    data = json.loads(env_path.read_text())
    for key, value in data.items():
        os.environ.setdefault(key, str(value))


def _json_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    data = json.loads(value)
    if not isinstance(data, list):
        raise ValueError(f"{name} must be a JSON list")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
