#!/usr/bin/env python3
"""Atomically update an issue's latest.json pointer for a validated result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Validated test-result.json")
    args = parser.parse_args()

    result = args.result.resolve(strict=True)
    if result.name != "test-result.json":
        parser.error("result filename must be test-result.json")
    run_dir = result.parent
    issue_dir = run_dir.parent
    if run_dir == issue_dir:
        parser.error("result must be inside an issue/run directory")

    data = json.loads(result.read_text(encoding="utf-8"))
    run_id = data.get("run", {}).get("id")
    issue_id = data.get("issue", {}).get("id")
    if run_id != run_dir.name:
        parser.error("run.id must match the run directory name")
    if str(issue_id) != issue_dir.name:
        parser.error("issue.id must match the issue directory name")

    pointer = {
        "schema_version": 1,
        "run_id": run_id,
        "result_path": f"{run_dir.name}/test-result.json",
        "sha256": sha256(result),
    }
    latest = issue_dir / "latest.json"
    fd, temp_name = tempfile.mkstemp(prefix="latest-", suffix=".tmp", dir=issue_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(pointer, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, latest)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    print(latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
