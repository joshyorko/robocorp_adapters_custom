#!/usr/bin/env python3
"""Report one completed Fizzy worker result back to Fizzy."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from robocorp_adapters_custom.fizzy_orchestration import report_worker_result_once  # noqa: E402
from robocorp_adapters_custom.workitems_integration import initialize_adapter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="devdata/env-fizzy-sqlite-reporter.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _load_env(args.env)
    adapter = initialize_adapter()
    result = report_worker_result_once(
        adapter,
        dry_run=args.dry_run or _truthy(os.getenv("FIZZY_REPORTER_DRY_RUN")),
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


def _truthy(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
