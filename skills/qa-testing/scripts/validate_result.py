#!/usr/bin/env python3
"""Validate a qa-testing result and its local evidence without external I/O."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_VERSIONS = {1, 2}
RUN_STATUSES = {"completed", "retryable_error", "configuration_error"}
VERDICTS = {"Pass", "Fail", "Pending", "Not Run"}
NOTE_STATUSES = {"pending", "posted", "duplicate", "skipped_immaterial", "retryable_error"}
RESUME_MODES = {"fresh", "resume", "supersede", "report-only", "delivery-only"}
REPORT_STATUSES = {"not_requested", "pending", "ready", "retryable_error", "delivered"}
REPORT_DELIVERY_STATUSES = {"not_requested", "not_ready", "pending", "posted", "duplicate", "retryable_error"}
REPORT_ANNOTATIONS = {"none", "red_frame", "equivalent_focus_marker"}
TERMINAL_VERDICTS = {
    "completed": {"Pass", "Fail", "Pending"},
    "retryable_error": {"Not Run"},
    "configuration_error": {"Not Run"},
}
SECRET_KEYS = re.compile(r"(?:password|token|cookie|authorization|credential|secret)", re.I)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+\S+", re.I),
    re.compile(r"\bAuthorization\s*:\s*\S+", re.I),
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(Exception):
    pass


def require_object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValidationError(f"{key} must be an object")
    return value


def require_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise ValidationError(f"{key} must be an array")
    return value


def require_fields(parent: dict[str, Any], prefix: str, names: tuple[str, ...]) -> None:
    missing = [name for name in names if name not in parent]
    if missing:
        raise ValidationError(f"{prefix} missing fields: {', '.join(missing)}")


def require_text(parent: dict[str, Any], prefix: str, name: str, *, allow_empty: bool = False) -> str:
    value = parent.get(name)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValidationError(f"{prefix}.{name} must be {'a string' if allow_empty else 'a non-empty string'}")
    return value


def require_optional_text(parent: dict[str, Any], prefix: str, name: str) -> str | None:
    value = parent.get(name)
    if value is not None and not isinstance(value, str):
        raise ValidationError(f"{prefix}.{name} must be a string or null")
    return value


def require_bool(parent: dict[str, Any], prefix: str, name: str) -> bool:
    value = parent.get(name)
    if not isinstance(value, bool):
        raise ValidationError(f"{prefix}.{name} must be boolean")
    return value


def require_timestamp(parent: dict[str, Any], prefix: str, name: str, *, allow_null: bool = False) -> None:
    value = parent.get(name)
    if value is None and allow_null:
        return
    if not isinstance(value, str):
        raise ValidationError(f"{prefix}.{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{prefix}.{name} is not ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{prefix}.{name} must include a timezone")


def scan_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key != "secrets_redacted" and SECRET_KEYS.search(key):
                if child not in (None, "", [], {}):
                    raise ValidationError(f"secret-like field must be empty or absent: {child_path}")
            scan_secrets(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise ValidationError(f"secret-like value found at {path}")


def contained_file(run_dir: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValidationError(f"evidence path must be relative: {relative}")
    root = run_dir.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"evidence path escapes run directory: {relative}") from exc
    if not resolved.is_file():
        raise ValidationError(f"evidence file does not exist: {relative}")
    return resolved


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_report(
    report: dict[str, Any],
    result_path: Path,
    evidence_ids: set[str],
    evidence_paths: set[str],
) -> None:
    require_fields(
        report,
        "report",
        ("requested", "status", "format", "path", "sha256", "assets", "quality", "delivery", "error"),
    )
    requested = require_bool(report, "report", "requested")
    status = report.get("status")
    if status not in REPORT_STATUSES:
        raise ValidationError(f"invalid report.status: {status}")
    report_format = require_optional_text(report, "report", "format")
    report_path_value = require_optional_text(report, "report", "path")
    report_hash = require_optional_text(report, "report", "sha256")
    report_error = require_optional_text(report, "report", "error")
    assets = require_list(report, "assets")

    quality = require_object(report, "quality")
    require_fields(
        quality,
        "report.quality",
        (
            "page_count",
            "page_size",
            "orientation",
            "max_pages",
            "render_reviewed",
            "title_style_checked",
            "focus_annotations_checked",
            "accessibility_audit_passed",
        ),
    )
    page_count = quality.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1):
        raise ValidationError("report.quality.page_count must be a positive integer or null")
    if quality.get("page_size") != "Letter":
        raise ValidationError("report.quality.page_size must be Letter")
    if quality.get("orientation") != "portrait":
        raise ValidationError("report.quality.orientation must be portrait")
    if quality.get("max_pages") != 1:
        raise ValidationError("report.quality.max_pages must equal 1")
    quality_gates = (
        "render_reviewed",
        "title_style_checked",
        "focus_annotations_checked",
        "accessibility_audit_passed",
    )
    for gate in quality_gates:
        require_bool(quality, "report.quality", gate)

    delivery = require_object(report, "delivery")
    require_fields(
        delivery,
        "report.delivery",
        (
            "status",
            "note_id",
            "attachment_id",
            "requested_filename",
            "stored_filename",
            "revision",
            "supersedes_attachment_id",
            "error",
        ),
    )
    delivery_status = delivery.get("status")
    if delivery_status not in REPORT_DELIVERY_STATUSES:
        raise ValidationError(f"invalid report.delivery.status: {delivery_status}")
    for name in ("note_id", "attachment_id", "requested_filename", "stored_filename", "supersedes_attachment_id", "error"):
        require_optional_text(delivery, "report.delivery", name)
    revision = delivery.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValidationError("report.delivery.revision must be a non-negative integer")

    if not requested:
        if status != "not_requested" or report_format is not None or report_path_value is not None or report_hash is not None:
            raise ValidationError("unrequested report must not contain an artifact")
        if assets or delivery_status != "not_requested" or revision != 0:
            raise ValidationError("unrequested report must not contain assets or delivery state")
        return

    if status == "not_requested" or report_format != "docx":
        raise ValidationError("requested report must use docx and a requested status")
    requested_filename = require_text(delivery, "report.delivery", "requested_filename")
    if not requested_filename.lower().endswith(".docx"):
        raise ValidationError("report.delivery.requested_filename must end with .docx")
    if revision < 1:
        raise ValidationError("requested report delivery revision must be positive")

    artifact_required = status in {"ready", "delivered"}
    if artifact_required:
        artifact_relative = require_text(report, "report", "path")
        if not artifact_relative.lower().endswith(".docx"):
            raise ValidationError("report.path must end with .docx")
        artifact_hash = require_text(report, "report", "sha256")
        if not SHA256.fullmatch(artifact_hash):
            raise ValidationError("report.sha256 must be lowercase SHA-256")
        artifact_path = contained_file(result_path.parent, artifact_relative)
        if file_sha256(artifact_path) != artifact_hash:
            raise ValidationError("report DOCX hash mismatch")
        if page_count != 1 or not all(quality.get(gate) is True for gate in quality_gates):
            raise ValidationError("ready report requires every pre-upload QA gate")
    elif report_path_value is not None or report_hash is not None:
        if report_path_value is None or report_hash is None or not SHA256.fullmatch(report_hash):
            raise ValidationError("partial report artifact identity is invalid")
        draft_path = contained_file(result_path.parent, report_path_value)
        if file_sha256(draft_path) != report_hash:
            raise ValidationError("report DOCX hash mismatch")

    if status == "retryable_error" and not report_error:
        raise ValidationError("report.error is required for retryable_error")
    if status in {"pending", "retryable_error"} and delivery_status != "not_ready":
        raise ValidationError("unfinished report generation must use delivery status not_ready")
    if status == "ready" and delivery_status not in {"pending", "retryable_error"}:
        raise ValidationError("ready report requires unresolved delivery")
    if status == "delivered" and delivery_status not in {"posted", "duplicate"}:
        raise ValidationError("delivered report requires observed attachment delivery")
    if delivery_status == "retryable_error" and not delivery.get("error"):
        raise ValidationError("report.delivery.error is required for retryable_error")

    asset_ids: set[str] = set()
    for index, item in enumerate(assets):
        if not isinstance(item, dict):
            raise ValidationError(f"report.assets[{index}] must be an object")
        prefix = f"report.assets[{index}]"
        require_fields(item, prefix, ("id", "source_evidence_id", "type", "path", "sha256", "description", "annotation"))
        asset_id = require_text(item, prefix, "id")
        if asset_id in asset_ids:
            raise ValidationError(f"duplicate report asset id: {asset_id}")
        asset_ids.add(asset_id)
        source_id = require_text(item, prefix, "source_evidence_id")
        if source_id not in evidence_ids:
            raise ValidationError(f"report asset references missing evidence: {source_id}")
        asset_type = require_text(item, prefix, "type")
        relative = require_text(item, prefix, "path")
        normalized = Path(relative).as_posix()
        if not normalized.startswith("report-assets/") or normalized in evidence_paths:
            raise ValidationError("report asset must stay under report-assets and remain separate from evidence")
        expected_hash = require_text(item, prefix, "sha256")
        if not SHA256.fullmatch(expected_hash):
            raise ValidationError(f"{prefix}.sha256 must be lowercase SHA-256")
        require_text(item, prefix, "description")
        annotation = require_text(item, prefix, "annotation")
        if annotation not in REPORT_ANNOTATIONS:
            raise ValidationError(f"invalid {prefix}.annotation: {annotation}")
        if asset_type == "annotated_screenshot" and annotation not in {"red_frame", "equivalent_focus_marker"}:
            raise ValidationError("annotated report screenshot requires a visible focus marker")
        asset_path = contained_file(result_path.parent, relative)
        if file_sha256(asset_path) != expected_hash:
            raise ValidationError(f"report asset hash mismatch: {relative}")

    if delivery_status in {"posted", "duplicate"}:
        require_text(delivery, "report.delivery", "note_id")
        require_text(delivery, "report.delivery", "attachment_id")
        require_text(delivery, "report.delivery", "stored_filename")
        if revision > 1:
            require_text(delivery, "report.delivery", "supersedes_attachment_id")


def validate(data: dict[str, Any], result_path: Path) -> None:
    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValidationError("schema_version must equal 1 or 2")

    top_objects = ["run", "issue", "project", "resume", "test_plan", "execution", "result", "mantis_note", "security"]
    if schema_version == 2:
        top_objects.append("report")
    objects = {key: require_object(data, key) for key in top_objects}
    evidence = require_list(data, "evidence")

    run = objects["run"]
    require_fields(run, "run", ("id", "started_at", "completed_at", "status"))
    require_text(run, "run", "id")
    require_timestamp(run, "run", "started_at")
    require_timestamp(run, "run", "completed_at")
    if run.get("status") not in RUN_STATUSES:
        raise ValidationError(f"invalid run.status: {run.get('status')}")

    issue = objects["issue"]
    require_fields(issue, "issue", ("id", "url", "project_id", "summary", "status", "updated_at", "fetched_at", "acceptance_summary"))
    for name in ("id", "url", "project_id", "summary", "status", "acceptance_summary"):
        require_text(issue, "issue", name)
    require_timestamp(issue, "issue", "updated_at")
    require_timestamp(issue, "issue", "fetched_at")

    project = objects["project"]
    require_fields(project, "project", ("name", "environment", "source_review"))
    for name in ("name", "environment", "source_review"):
        require_text(project, "project", name)

    resume = objects["resume"]
    require_fields(resume, "resume", ("mode", "prior_run_id", "reason"))
    if resume.get("mode") not in RESUME_MODES:
        raise ValidationError(f"invalid resume.mode: {resume.get('mode')}")
    require_optional_text(resume, "resume", "prior_run_id")
    require_text(resume, "resume", "reason")

    plan = objects["test_plan"]
    require_fields(plan, "test_plan", ("objective", "preconditions", "steps", "regression_checks", "prohibited_actions"))
    require_text(plan, "test_plan", "objective")
    for name in ("preconditions", "steps", "regression_checks", "prohibited_actions"):
        require_list(plan, name)

    execution = objects["execution"]
    require_fields(execution, "execution", ("last_completed_step", "next_safe_step", "test_data_refs", "steps"))
    if schema_version == 2:
        actor = require_object(execution, "actor")
        require_fields(actor, "execution.actor", ("role", "account_label"))
        require_text(actor, "execution.actor", "role")
        require_text(actor, "execution.actor", "account_label")
    require_optional_text(execution, "execution", "last_completed_step")
    require_text(execution, "execution", "next_safe_step")
    require_list(execution, "test_data_refs")
    execution_steps = require_list(execution, "steps")

    result = objects["result"]
    require_fields(result, "result", ("verdict", "summary", "blockers", "release_conditions", "next_step"))
    verdict = result.get("verdict")
    if verdict not in VERDICTS:
        raise ValidationError(f"invalid result.verdict: {verdict}")
    require_text(result, "result", "summary")
    require_list(result, "blockers")
    require_list(result, "release_conditions")
    require_text(result, "result", "next_step")

    run_status = run.get("status")
    if verdict not in TERMINAL_VERDICTS[run_status]:
        raise ValidationError(f"invalid terminal combination: {run_status} + {verdict}")

    note = objects["mantis_note"]
    require_fields(note, "mantis_note", ("status", "private", "note_id", "prepared_note_path", "content_sha256", "error"))
    if note.get("status") not in NOTE_STATUSES:
        raise ValidationError(f"invalid mantis_note.status: {note.get('status')}")
    if note.get("private") is not True:
        raise ValidationError("mantis_note.private must be true")
    for name in ("note_id", "prepared_note_path", "content_sha256", "error"):
        require_optional_text(note, "mantis_note", name)
    prepared_statuses = {"pending", "posted", "duplicate", "retryable_error"}
    if note.get("status") in prepared_statuses:
        note_path_value = require_text(note, "mantis_note", "prepared_note_path")
        note_hash = require_text(note, "mantis_note", "content_sha256")
        if not SHA256.fullmatch(note_hash):
            raise ValidationError("prepared mantis_note.content_sha256 must be lowercase SHA-256")
        note_path = contained_file(result_path.parent, note_path_value)
        if file_sha256(note_path) != note_hash:
            raise ValidationError("prepared Mantis note hash mismatch")
    if note.get("status") == "posted" or (schema_version == 2 and note.get("status") == "duplicate"):
        require_text(note, "mantis_note", "note_id")

    security = objects["security"]
    if security.get("secrets_redacted") is not True:
        raise ValidationError("security.secrets_redacted must be true")

    evidence_ids: set[str] = set()
    evidence_paths: set[str] = set()
    run_dir = result_path.parent
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ValidationError(f"evidence[{index}] must be an object")
        require_fields(item, f"evidence[{index}]", ("id", "step_id", "type", "path", "sha256", "captured_at", "description"))
        evidence_id = require_text(item, f"evidence[{index}]", "id")
        if evidence_id in evidence_ids:
            raise ValidationError(f"duplicate evidence id: {evidence_id}")
        evidence_ids.add(evidence_id)
        require_text(item, f"evidence[{index}]", "step_id")
        require_text(item, f"evidence[{index}]", "type")
        relative = require_text(item, f"evidence[{index}]", "path")
        evidence_paths.add(Path(relative).as_posix())
        expected_hash = require_text(item, f"evidence[{index}]", "sha256")
        if not SHA256.fullmatch(expected_hash):
            raise ValidationError(f"evidence[{index}].sha256 must be lowercase SHA-256")
        require_timestamp(item, f"evidence[{index}]", "captured_at")
        require_text(item, f"evidence[{index}]", "description")
        evidence_path = contained_file(run_dir, relative)
        if file_sha256(evidence_path) != expected_hash:
            raise ValidationError(f"evidence hash mismatch: {relative}")

    step_ids: set[str] = set()
    referenced_evidence: set[str] = set()
    for index, step in enumerate(execution_steps):
        if not isinstance(step, dict):
            raise ValidationError(f"execution.steps[{index}] must be an object")
        require_fields(step, f"execution.steps[{index}]", ("id", "action", "expected", "actual", "status", "evidence_ids"))
        step_id = require_text(step, f"execution.steps[{index}]", "id")
        if step_id in step_ids:
            raise ValidationError(f"duplicate execution step id: {step_id}")
        step_ids.add(step_id)
        for name in ("action", "expected", "actual", "status"):
            require_text(step, f"execution.steps[{index}]", name)
        refs = require_list(step, "evidence_ids")
        for ref in refs:
            if not isinstance(ref, str):
                raise ValidationError(f"execution.steps[{index}].evidence_ids must contain strings")
            referenced_evidence.add(ref)

    missing_refs = referenced_evidence - evidence_ids
    if missing_refs:
        raise ValidationError(f"execution steps reference missing evidence: {', '.join(sorted(missing_refs))}")
    unknown_steps = {item["step_id"] for item in evidence if item["step_id"] not in step_ids}
    if unknown_steps:
        raise ValidationError(f"evidence references missing execution steps: {', '.join(sorted(unknown_steps))}")

    if schema_version == 2:
        validate_report(objects["report"], result_path, evidence_ids, evidence_paths)

    scan_secrets(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Path to test-result.json")
    args = parser.parse_args()
    try:
        raw = args.result.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValidationError("root must be an object")
        validate(data, args.result)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {args.result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
