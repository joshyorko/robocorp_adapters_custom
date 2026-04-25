"""Fizzy/Codex orchestration helpers built on work item adapters.

The helpers in this module keep Fizzy, Robocorp work items, and runner
execution loosely coupled:

- Fizzy is accessed through the local ``fizzy`` CLI only.
- Work item adapters remain the durable queue boundary.
- The runner command is payload/config driven and is not Codex-specific.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from robocorp.workitems._adapters._base import BaseAdapter

from ._types import JSONType, State

DEFAULT_PROMPT_TEMPLATE = (
    "Use the Fizzy card title, description, and linked repository context to complete the task."
)
DEFAULT_RUNNER_COMMAND = "codex exec --json"
DEFAULT_RUNNER_KIND = "codex"


def build_fizzy_work_item_payload(
    card: dict[str, Any],
    *,
    workflow: Optional[dict[str, Any]] = None,
    runner: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Normalize a Fizzy card into the stable orchestration payload contract."""
    workflow_payload = {
        "prompt_template": DEFAULT_PROMPT_TEMPLATE,
        "allowed_paths": [],
        "handoff_column": "Synthesize & Verify",
    }
    workflow_payload.update(workflow or {})

    runner_payload = {
        "kind": DEFAULT_RUNNER_KIND,
        "command": DEFAULT_RUNNER_COMMAND,
    }
    runner_payload.update(runner or {})

    board = card.get("board") or {}
    column = card.get("column") or {}

    return {
        "source": "fizzy",
        "card": {
            "id": card.get("id", ""),
            "number": card.get("number"),
            "title": card.get("title", ""),
            "description": card.get("description", ""),
            "url": card.get("url", ""),
            "board_id": card.get("board_id") or board.get("id", ""),
            "column_id": card.get("column_id") or column.get("id", ""),
            "state": card.get("state") or column.get("name", ""),
            "labels": card.get("labels", []),
            "branch_name": card.get("branch_name", ""),
        },
        "workflow": workflow_payload,
        "runner": runner_payload,
    }


def list_fizzy_cards(board_id: str) -> list[dict[str, Any]]:
    """Return Fizzy cards for a board using the local Fizzy CLI contract."""
    output = _run_fizzy(["card", "list", "--board", board_id])
    data = json.loads(output or "[]")
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if not isinstance(data, list):
        raise ValueError("fizzy card list did not return a list")
    return data


def enqueue_fizzy_cards(
    adapter: BaseAdapter,
    cards: Iterable[dict[str, Any]],
    *,
    workflow: Optional[dict[str, Any]] = None,
    runner: Optional[dict[str, Any]] = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Seed Fizzy card payloads into an adapter input queue.

    Duplicate prevention is supported for the SQLite adapter by scanning JSON
    payloads in the current input queue. Other adapters can still enqueue
    payloads, but should use ``force=False`` only after adding backend-specific
    duplicate lookup support.
    """
    seed_input = getattr(adapter, "seed_input", None)
    if seed_input is None:
        raise TypeError("adapter must provide seed_input() to enqueue input work items")

    results = []
    for card in cards:
        payload = build_fizzy_work_item_payload(card, workflow=workflow, runner=runner)
        existing_id = find_existing_fizzy_work_item(adapter, payload)
        if existing_id and not force:
            results.append(
                {
                    "card_number": payload["card"]["number"],
                    "item_id": existing_id,
                    "created": False,
                    "duplicate": True,
                }
            )
            continue

        item_id = seed_input(payload)
        results.append(
            {
                "card_number": payload["card"]["number"],
                "item_id": item_id,
                "created": True,
                "duplicate": False,
            }
        )
    return results


def find_existing_fizzy_work_item(
    adapter: BaseAdapter,
    payload: dict[str, Any],
) -> Optional[str]:
    """Find an existing SQLite queued item for the same Fizzy board/card."""
    if not hasattr(adapter, "_pool") or not hasattr(adapter, "queue_name"):
        return None

    target = _card_identity(payload)
    if target is None:
        return None

    with adapter._pool.acquire() as conn:  # type: ignore[attr-defined]
        cursor = conn.execute(
            "SELECT id, payload FROM work_items WHERE queue_name = ? ORDER BY created_at",
            (adapter.queue_name,),  # type: ignore[attr-defined]
        )
        for row in cursor.fetchall():
            try:
                existing_payload = json.loads(row["payload"] or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if _card_identity(existing_payload) == target:
                return row["id"]
    return None


def run_worker_once(
    adapter: BaseAdapter,
    *,
    runner_command: Optional[str | Sequence[str]] = None,
    workspace_root: str | Path = "devdata/fizzy_workspaces",
    timeout_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Reserve one Fizzy work item, run its configured command, and emit output."""
    item_id = adapter.reserve_input()
    try:
        payload = adapter.load_payload(item_id)
        command = runner_command or payload.get("runner", {}).get("command")
        if not command:
            raise ValueError("runner command is required")

        card = payload.get("card", {})
        workspace = Path(workspace_root) / f"card-{card.get('number', item_id)}"
        workspace.mkdir(parents=True, exist_ok=True)

        args = _command_args(command)
        env = os.environ.copy()
        env["WORK_ITEM_ID"] = item_id
        env["WORK_ITEM_PAYLOAD_JSON"] = json.dumps(payload)

        completed = subprocess.run(
            args,
            cwd=workspace,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        succeeded = completed.returncode == 0
        result_payload: dict[str, JSONType] = {
            "source": "fizzy",
            "card": card,
            "workflow": payload.get("workflow", {}),
            "runner": payload.get("runner", {}),
            "result": {
                "status": "completed" if succeeded else "failed",
                "returncode": completed.returncode,
                "workspace": str(workspace),
            },
        }

        output_id = adapter.create_output(item_id, result_payload)
        _attach_text(adapter, output_id, "stdout.txt", completed.stdout)
        _attach_text(adapter, output_id, "stderr.txt", completed.stderr)

        if succeeded:
            adapter.release_input(item_id, State.DONE)
        else:
            adapter.release_input(
                item_id,
                State.FAILED,
                {
                    "type": "APPLICATION",
                    "code": str(completed.returncode),
                    "message": _failure_message(completed),
                },
            )

        return {
            "input_id": item_id,
            "output_id": output_id,
            "card_number": card.get("number"),
            "status": result_payload["result"]["status"],
            "returncode": completed.returncode,
        }
    except Exception as exc:
        _release_failed(adapter, item_id, "WORKER_ERROR", exc)
        raise


def report_worker_result_once(
    adapter: BaseAdapter,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Reserve one worker result and report it back to Fizzy via the CLI."""
    item_id = adapter.reserve_input()
    try:
        payload = adapter.load_payload(item_id)
        card_number = payload.get("card", {}).get("number")
        if card_number is None:
            raise ValueError("worker result payload missing card.number")

        body = format_fizzy_report_comment(payload)
        if not dry_run:
            _run_fizzy(["comment", "create", "--card", str(card_number), "--body", body])
            handoff_column_id = payload.get("workflow", {}).get("handoff_column_id")
            if handoff_column_id:
                _run_fizzy(["card", "column", str(card_number), "--column", handoff_column_id])

        adapter.release_input(item_id, State.DONE)
        return {
            "input_id": item_id,
            "card_number": card_number,
            "dry_run": dry_run,
            "comment": body,
        }
    except Exception as exc:
        _release_failed(adapter, item_id, "REPORTER_ERROR", exc)
        raise


def format_fizzy_report_comment(payload: dict[str, Any]) -> str:
    """Format a compact report comment for a Fizzy card."""
    result = payload.get("result", {})
    status = result.get("status", "unknown")
    returncode = result.get("returncode", "unknown")
    workspace = result.get("workspace", "")
    return (
        "Worker result\n\n"
        f"- Status: {status}\n"
        f"- Return code: {returncode}\n"
        f"- Workspace: `{workspace}`\n"
    )


def _run_fizzy(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["fizzy", *args, "--agent", "--quiet"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def _command_args(command: str | Sequence[str]) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return list(command)


def _attach_text(adapter: BaseAdapter, item_id: str, name: str, content: str) -> None:
    if content and hasattr(adapter, "add_file"):
        adapter.add_file(item_id, name, content.encode("utf-8"))


def _failure_message(completed: subprocess.CompletedProcess[str]) -> str:
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    if stderr:
        return stderr[:1000]
    if stdout:
        return stdout[:1000]
    return f"Runner exited with code {completed.returncode}"


def _release_failed(adapter: BaseAdapter, item_id: str, code: str, exc: Exception) -> None:
    adapter.release_input(
        item_id,
        State.FAILED,
        {
            "type": "APPLICATION",
            "code": code,
            "message": str(exc),
        },
    )


def _card_identity(payload: dict[str, Any]) -> Optional[tuple[str, int]]:
    if payload.get("source") != "fizzy":
        return None
    card = payload.get("card") or {}
    board_id = card.get("board_id")
    number = card.get("number")
    if not board_id or number is None:
        return None
    return str(board_id), int(number)


__all__ = [
    "build_fizzy_work_item_payload",
    "enqueue_fizzy_cards",
    "find_existing_fizzy_work_item",
    "format_fizzy_report_comment",
    "list_fizzy_cards",
    "report_worker_result_once",
    "run_worker_once",
]
