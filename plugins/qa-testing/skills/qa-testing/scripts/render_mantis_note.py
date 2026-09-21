#!/usr/bin/env python3
"""Validate the classified core and render its readable private-note body."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from validate_result import ValidationError, validate


def readable_test_data(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        labels = {"safe_quote": "測試資料", "record": "測試紀錄", "case": "測試案件"}
        kind = value.get("type")
        identifier = value.get("value") or value.get("id") or value.get("reference")
        if identifier is not None:
            return f"{labels.get(kind, value.get('label') or '測試資料')}：{identifier}"
        pairs = [f"{key}：{item}" for key, item in value.items() if isinstance(item, (str, int, float, bool))]
        return "、".join(pairs) if pairs else "已記錄安全測試資料"
    return str(value)


def lines_for(result: dict) -> list[str]:
    run = result["run"]
    issue = result["issue"]
    project = result["project"]
    execution = result["execution"]
    outcome = result["result"]
    evidence = result["evidence"]
    actor = execution.get("actor", {})
    actor_label = actor.get("account_label") or actor.get("role")

    lines = [
        "【QA SIT 驗測結果】",
        f"Mantis：#{issue['id']} {issue['summary']}",
        f"環境：{project['name']}／{project['environment']}",
        f"帳號／角色：{actor_label or '未記錄'}",
        f"驗收重點：{issue['acceptance_summary']}",
        f"結果：{outcome['verdict']}",
        f"摘要：{outcome['summary']}",
        "",
        "主要測試資料：",
    ]
    test_data_refs = execution.get("test_data_refs", [])
    if test_data_refs:
        lines.extend(f"- {readable_test_data(item)}" for item in test_data_refs)
    else:
        lines.append("- 本次沒有建立測試資料。")

    lines.extend([
        "",
        "本次執行：",
    ])
    steps = execution.get("steps", [])
    if steps:
        for step in steps:
            lines.append(f"- {step['action']}（{step['status']}）")
            lines.append(f"  預期：{step['expected']}")
            lines.append(f"  實際：{step['actual']}")
    else:
        lines.append("- 尚未進入產品驗測。")

    lines.extend(["", "證據摘要："])
    if evidence:
        for item in evidence:
            lines.append(f"- {item['description']}")
    else:
        lines.append("- 本次沒有產生產品驗測證據。")

    blockers = outcome.get("blockers", [])
    release = outcome.get("release_conditions", [])
    if blockers:
        lines.extend(["", "目前卡點："])
        lines.extend(f"- {item}" for item in blockers)
    if release:
        lines.extend(["", "解除條件："])
        lines.extend(f"- {item}" for item in release)

    lines.extend(
        [
            "",
            f"最後完成步驟：{execution.get('last_completed_step') or '尚未開始'}",
            f"建議／下一步：{outcome['next_step']}",
            f"執行識別：{run['id']}",
        ]
    )
    return lines


def write_atomic_text(path: Path, value: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Validated test-result.json")
    parser.add_argument("--output", type=Path, help="Write UTF-8 note text and print only its path and hash")
    args = parser.parse_args()

    try:
        result_path = args.result.resolve(strict=True)
        data = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValidationError("root must be an object")
        validate(data, result_path, require_prepared_note=False, require_valid_report=False)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        parser.error(str(exc))

    note = "\n".join(lines_for(data)).rstrip() + "\n"
    digest = hashlib.sha256(note.encode("utf-8")).hexdigest()

    if args.output:
        output = args.output.resolve()
        if output.parent != result_path.parent:
            parser.error("output must stay inside the result run directory")
        write_atomic_text(output, note)
        print(json.dumps({"path": str(output), "sha256": digest}, ensure_ascii=False))
    else:
        print(note, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
