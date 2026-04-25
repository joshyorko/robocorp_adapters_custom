import sqlite3
import sys
from argparse import Namespace

import pytest

from robocorp_adapters_custom._sqlite import SQLiteAdapter
from robocorp_adapters_custom.fizzy_orchestration import (
    build_fizzy_work_item_payload,
    enqueue_fizzy_cards,
    format_fizzy_report_comment,
    report_worker_result_once,
    run_worker_once,
)
from scripts.fizzy_seed_sqlite import _resolve_runtime_options


def test_build_fizzy_work_item_payload_normalizes_nested_card_fields():
    payload = build_fizzy_work_item_payload(
        {
            "id": "card-id",
            "number": 579,
            "title": "Implement feature",
            "description": "Details",
            "url": "https://example.test/cards/579",
            "board": {"id": "board-id"},
            "column": {"id": "column-id", "name": "Ready for Agents"},
        },
        workflow={"allowed_paths": ["src/", "tests/"]},
        runner={"command": "python worker.py"},
    )

    assert payload["source"] == "fizzy"
    assert payload["card"] == {
        "id": "card-id",
        "number": 579,
        "title": "Implement feature",
        "description": "Details",
        "url": "https://example.test/cards/579",
        "board_id": "board-id",
        "column_id": "column-id",
        "state": "Ready for Agents",
        "labels": [],
        "branch_name": "",
    }
    assert payload["workflow"]["allowed_paths"] == ["src/", "tests/"]
    assert payload["runner"]["command"] == "python worker.py"


def test_enqueue_fizzy_cards_prevents_duplicate_sqlite_items(tmp_path, monkeypatch):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_cards")
    card = _card(number=218, board_id="board-example")

    first = enqueue_fizzy_cards(adapter, [card])
    second = enqueue_fizzy_cards(adapter, [card])

    assert first == [
        {"card_number": 218, "item_id": first[0]["item_id"], "created": True, "duplicate": False}
    ]
    assert second == [
        {"card_number": 218, "item_id": first[0]["item_id"], "created": False, "duplicate": True}
    ]

    with sqlite3.connect(adapter.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    assert count == 1


def test_run_worker_once_creates_completed_result_and_attaches_stdout(tmp_path, monkeypatch):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_cards")
    item_id = adapter.seed_input(
        build_fizzy_work_item_payload(_card(), runner={"command": "unused"})
    )

    result = run_worker_once(
        adapter,
        runner_command=[sys.executable, "-c", "print('proof output')"],
        workspace_root=tmp_path / "workspaces",
    )

    assert result["input_id"] == item_id
    assert result["card_number"] == 101
    assert result["status"] == "completed"
    assert adapter.get_file(result["output_id"], "stdout.txt") == b"proof output\n"

    with sqlite3.connect(adapter.db_path) as conn:
        state = conn.execute("SELECT state FROM work_items WHERE id = ?", (item_id,)).fetchone()[0]
    assert state == "COMPLETED"


def test_run_worker_once_marks_failure_and_preserves_stderr(tmp_path, monkeypatch):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_cards")
    item_id = adapter.seed_input(build_fizzy_work_item_payload(_card()))

    result = run_worker_once(
        adapter,
        runner_command=[
            sys.executable,
            "-c",
            "import sys; print('bad', file=sys.stderr); raise SystemExit(7)",
        ],
        workspace_root=tmp_path / "workspaces",
    )

    assert result["status"] == "failed"
    assert result["returncode"] == 7
    assert adapter.get_file(result["output_id"], "stderr.txt") == b"bad\n"

    with sqlite3.connect(adapter.db_path) as conn:
        row = conn.execute(
            "SELECT state, exception_type, exception_code, exception_message FROM work_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    assert row == ("FAILED", "APPLICATION", "7", "bad")


def test_run_worker_once_marks_reserved_item_failed_when_command_is_missing(tmp_path, monkeypatch):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_cards")
    item_id = adapter.seed_input(build_fizzy_work_item_payload(_card(), runner={"command": ""}))

    with pytest.raises(ValueError, match="runner command is required"):
        run_worker_once(adapter, workspace_root=tmp_path / "workspaces")

    with sqlite3.connect(adapter.db_path) as conn:
        row = conn.execute(
            "SELECT state, exception_type, exception_code, exception_message FROM work_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    assert row == ("FAILED", "APPLICATION", "WORKER_ERROR", "runner command is required")


def test_report_worker_result_once_dry_run_releases_result(tmp_path, monkeypatch):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_worker_results")
    item_id = adapter.seed_input(
        {
            "source": "fizzy",
            "card": {"number": 101},
            "workflow": {},
            "result": {"status": "completed", "returncode": 0, "workspace": "workspace"},
        }
    )

    result = report_worker_result_once(adapter, dry_run=True)

    assert result["input_id"] == item_id
    assert result["card_number"] == 101
    assert "Status: completed" in result["comment"]

    with sqlite3.connect(adapter.db_path) as conn:
        state = conn.execute("SELECT state FROM work_items WHERE id = ?", (item_id,)).fetchone()[0]
    assert state == "COMPLETED"


def test_report_worker_result_once_marks_reserved_item_failed_for_bad_payload(
    tmp_path, monkeypatch
):
    adapter = _sqlite_adapter(tmp_path, monkeypatch, queue_name="fizzy_worker_results")
    item_id = adapter.seed_input({"source": "fizzy", "card": {}, "result": {}})

    with pytest.raises(ValueError, match="worker result payload missing card.number"):
        report_worker_result_once(adapter, dry_run=True)

    with sqlite3.connect(adapter.db_path) as conn:
        row = conn.execute(
            "SELECT state, exception_type, exception_code, exception_message FROM work_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    assert row == (
        "FAILED",
        "APPLICATION",
        "REPORTER_ERROR",
        "worker result payload missing card.number",
    )


def test_format_fizzy_report_comment_includes_result_summary():
    comment = format_fizzy_report_comment(
        {"result": {"status": "failed", "returncode": 2, "workspace": "dev/work"}}
    )

    assert "Status: failed" in comment
    assert "Return code: 2" in comment
    assert "Workspace: `dev/work`" in comment


def test_seed_runtime_options_use_env_file_column_after_loading(tmp_path, monkeypatch):
    env_path = tmp_path / "env.json"
    env_path.write_text(
        '{"FIZZY_BOARD_ID": "board-from-file", "FIZZY_SOURCE_COLUMN_ID": "column-from-file"}'
    )
    monkeypatch.delenv("FIZZY_BOARD_ID", raising=False)
    monkeypatch.delenv("FIZZY_SOURCE_COLUMN_ID", raising=False)

    board_id, column_id = _resolve_runtime_options(
        Namespace(env=str(env_path), board="", column="")
    )

    assert board_id == "board-from-file"
    assert column_id == "column-from-file"


def _sqlite_adapter(tmp_path, monkeypatch, queue_name):
    monkeypatch.setenv("RC_WORKITEM_DB_PATH", str(tmp_path / "work_items.db"))
    monkeypatch.setenv("RC_WORKITEM_FILES_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("RC_WORKITEM_QUEUE_NAME", queue_name)
    monkeypatch.setenv("RC_WORKITEM_OUTPUT_QUEUE_NAME", f"{queue_name}_output")
    return SQLiteAdapter()


def _card(number=101, board_id="board-id"):
    return {
        "id": f"card-{number}",
        "number": number,
        "title": "Implement task",
        "description": "Card details",
        "url": f"https://example.test/cards/{number}",
        "board": {"id": board_id},
        "column": {"id": "column-id", "name": "Ready for Agents"},
    }
