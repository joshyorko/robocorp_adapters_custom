#!/usr/bin/env python3
"""Run one configured runner command for one Fizzy work item."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from robocorp_adapters_custom.fizzy_orchestration import run_worker_once  # noqa: E402
from robocorp_adapters_custom.workitems_integration import initialize_adapter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="devdata/env-fizzy-sqlite-worker.json")
    args = parser.parse_args()

    _load_env(args.env)
    adapter = initialize_adapter()
    result = run_worker_once(
        adapter,
        runner_command=os.getenv("FIZZY_RUNNER_COMMAND") or None,
        workspace_root=os.getenv("FIZZY_WORKSPACE_ROOT", "devdata/fizzy_workspaces"),
        timeout_seconds=_optional_int(os.getenv("FIZZY_RUNNER_TIMEOUT_SECONDS")),
    )
    print(json.dumps(result, indent=2))
    return 0


def _load_env(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    data = json.loads(env_path.read_text())
    for key, value in data.items():
        os.environ.setdefault(key, str(value))


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None


if __name__ == "__main__":
    raise SystemExit(main())
