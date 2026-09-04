#!/usr/bin/env python3
"""Validate a qa-testing checkpoint and its local continuation references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_result import (
    RESUME_MODES,
    SUPPORTED_SCHEMA_VERSIONS,
    ValidationError,
    contained_file,
    require_fields,
    require_list,
    require_object,
    require_optional_text,
    require_text,
    require_timestamp,
    scan_secrets,
    validate as validate_result,
)


PHASES = {"grounded", "bound", "continuity", "preflight", "planned", "executing", "classified", "reporting", "delivering"}
STATUSES = {"running", "retryable_error", "configuration_error", "report_pending", "delivery_pending", "completed"}
NOTE_STATUSES = {"not_prepared", "pending", "retryable_error", "posted", "duplicate", "skipped_immaterial"}
CHECKPOINT_REPORT_STATUSES = {"not_requested", "pending", "ready", "retryable_error", "delivered"}
CHECKPOINT_REPORT_DELIVERY_STATUSES = {"not_requested", "not_ready", "pending", "posted", "duplicate", "retryable_error"}


def validate_checkpoint_report(report: dict, result_data: dict | None, result_finalized: bool) -> None:
    require_fields(
        report,
        "report",
        ("requested", "status", "path", "sha256", "delivery_status", "attachment_id", "stored_filename", "revision"),
    )
    requested = report.get("requested")
    if not isinstance(requested, bool):
        raise ValidationError("report.requested must be boolean")
    if report.get("status") not in CHECKPOINT_REPORT_STATUSES:
        raise ValidationError(f"invalid report.status: {report.get('status')}")
    if report.get("delivery_status") not in CHECKPOINT_REPORT_DELIVERY_STATUSES:
        raise ValidationError(f"invalid report.delivery_status: {report.get('delivery_status')}")
    for name in ("path", "sha256", "attachment_id", "stored_filename"):
        require_optional_text(report, "report", name)
    revision = report.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValidationError("report.revision must be a non-negative integer")
    if requested and revision < 1:
        raise ValidationError("requested report revision must be positive")
    if not requested and (revision != 0 or report.get("status") != "not_requested"):
        raise ValidationError("unrequested checkpoint report must use revision zero and not_requested status")

    if result_finalized:
        if result_data is None or result_data.get("schema_version") != 2:
            raise ValidationError("version 2 checkpoint report requires a version 2 result")
        result_report = result_data["report"]
        result_delivery = result_report["delivery"]
        expected = {
            "requested": result_report["requested"],
            "status": result_report["status"],
            "path": result_report["path"],
            "sha256": result_report["sha256"],
            "delivery_status": result_delivery["status"],
            "attachment_id": result_delivery["attachment_id"],
            "stored_filename": result_delivery["stored_filename"],
            "revision": result_delivery["revision"],
        }
        if any(report.get(key) != value for key, value in expected.items()):
            raise ValidationError("checkpoint and result report identity differ")
    else:
        if report.get("status") not in {"not_requested", "pending"}:
            raise ValidationError("unfinished SIT checkpoint must not contain a generated report")
        if report.get("path") is not None or report.get("sha256") is not None:
            raise ValidationError("unfinished SIT checkpoint must not reference a report artifact")
        if report.get("attachment_id") is not None or report.get("stored_filename") is not None:
            raise ValidationError("unfinished SIT checkpoint must not contain report delivery identity")
        expected_delivery = "not_ready" if requested else "not_requested"
        if report.get("delivery_status") != expected_delivery:
            raise ValidationError("unfinished SIT checkpoint has invalid report delivery state")


def validate(data: dict, checkpoint_path: Path) -> None:
    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValidationError("schema_version must equal 1 or 2")
    required_fields = [
        "run_id",
        "updated_at",
        "phase",
        "status",
        "issue",
        "project",
        "continuation",
        "test_data_refs",
        "evidence_refs",
        "result_path",
        "prepared_note",
        "security",
    ]
    if schema_version == 2:
        required_fields.append("report")
    require_fields(
        data,
        "$",
        tuple(required_fields),
    )
    run_id = require_text(data, "$", "run_id")
    require_timestamp(data, "$", "updated_at")
    if data.get("phase") not in PHASES:
        raise ValidationError(f"invalid phase: {data.get('phase')}")
    if data.get("status") not in STATUSES:
        raise ValidationError(f"invalid status: {data.get('status')}")
    if checkpoint_path.parent.name != run_id:
        raise ValidationError("run_id must match the run directory name")

    issue = require_object(data, "issue")
    require_fields(issue, "issue", ("id", "project_id", "updated_at"))
    issue_id = require_text(issue, "issue", "id")
    require_text(issue, "issue", "project_id")
    require_timestamp(issue, "issue", "updated_at")
    if checkpoint_path.parent.parent.name != issue_id:
        raise ValidationError("issue.id must match the issue directory name")

    project = require_object(data, "project")
    require_fields(project, "project", ("name", "environment"))
    require_text(project, "project", "name")
    require_text(project, "project", "environment")

    continuation = require_object(data, "continuation")
    require_fields(
        continuation,
        "continuation",
        ("mode", "prior_run_id", "result_finalized", "last_completed_step", "next_safe_step"),
    )
    if continuation.get("mode") not in RESUME_MODES:
        raise ValidationError(f"invalid continuation.mode: {continuation.get('mode')}")
    require_optional_text(continuation, "continuation", "prior_run_id")
    if not isinstance(continuation.get("result_finalized"), bool):
        raise ValidationError("continuation.result_finalized must be boolean")
    require_optional_text(continuation, "continuation", "last_completed_step")
    require_text(continuation, "continuation", "next_safe_step")

    require_list(data, "test_data_refs")
    evidence_refs = require_list(data, "evidence_refs")
    for index, relative in enumerate(evidence_refs):
        if not isinstance(relative, str) or not relative:
            raise ValidationError(f"evidence_refs[{index}] must be a non-empty relative path")
        contained_file(checkpoint_path.parent, relative)

    result_path_value = require_optional_text(data, "$", "result_path")
    prepared = require_object(data, "prepared_note")
    require_fields(prepared, "prepared_note", ("path", "sha256", "status"))
    note_path_value = require_optional_text(prepared, "prepared_note", "path")
    note_hash = require_optional_text(prepared, "prepared_note", "sha256")
    if prepared.get("status") not in NOTE_STATUSES:
        raise ValidationError(f"invalid prepared_note.status: {prepared.get('status')}")

    result_finalized = continuation["result_finalized"]
    mode = continuation.get("mode")
    if mode in {"report-only", "delivery-only"} and not result_finalized:
        raise ValidationError(f"{mode} requires continuation.result_finalized=true")
    result_data = None
    result_report = None
    if result_finalized:
        if data.get("phase") not in {"classified", "reporting", "delivering"}:
            raise ValidationError("finalized result requires classified, reporting, or delivering phase")
        result_relative = require_text(data, "$", "result_path")
        result_file = contained_file(checkpoint_path.parent, result_relative)
        result_data = json.loads(result_file.read_text(encoding="utf-8"))
        if not isinstance(result_data, dict):
            raise ValidationError("checkpoint result_path must contain a JSON object")
        validate_result(result_data, result_file)
        if result_data["run"]["id"] != run_id:
            raise ValidationError("checkpoint and result run IDs differ")
        if result_data["issue"]["id"] != issue_id or result_data["issue"]["project_id"] != issue["project_id"]:
            raise ValidationError("checkpoint and result issue identity differ")
        if result_data["project"]["name"] != project["name"] or result_data["project"]["environment"] != project["environment"]:
            raise ValidationError("checkpoint and result project identity differ")
        result_note = result_data["mantis_note"]
        if result_note["status"] != prepared["status"]:
            raise ValidationError("checkpoint and result note statuses differ")
        if result_note["prepared_note_path"] != note_path_value or result_note["content_sha256"] != note_hash:
            raise ValidationError("checkpoint and result prepared note identity differ")
        result_evidence = {item["path"] for item in result_data["evidence"]}
        if not set(evidence_refs).issubset(result_evidence):
            raise ValidationError("checkpoint evidence is not present in the result")
        result_report = result_data.get("report")
    else:
        if result_path_value is not None:
            raise ValidationError("unfinished checkpoint must not reference a finalized result")
        if note_path_value is not None or note_hash is not None or prepared.get("status") != "not_prepared":
            raise ValidationError("unfinished checkpoint must not contain a prepared note")

    if schema_version == 2:
        report = require_object(data, "report")
        validate_checkpoint_report(report, result_data, result_finalized)
    else:
        report = None

    if mode in {"report-only", "delivery-only"}:
        if continuation.get("prior_run_id") != run_id:
            raise ValidationError(f"{mode} must retain the original run ID")
        if mode == "report-only" and (schema_version != 2 or result_report is None):
            raise ValidationError("report-only requires a version 2 report state")

    unresolved_note = prepared.get("status") in {"pending", "retryable_error"}
    unresolved_report_generation = bool(
        result_report
        and result_report["requested"]
        and result_report["status"] in {"pending", "retryable_error"}
    )
    unresolved_report_delivery = bool(
        result_report
        and result_report["status"] == "ready"
        and result_report["delivery"]["status"] in {"pending", "retryable_error"}
    )

    if mode == "report-only":
        if not unresolved_report_generation:
            raise ValidationError("report-only requires unresolved report generation or QA")
        if data.get("phase") != "reporting":
            raise ValidationError("report-only requires reporting phase")
    if mode == "delivery-only" and not (unresolved_note or unresolved_report_delivery):
        raise ValidationError("delivery-only requires unresolved note or report delivery")
    if data.get("status") == "report_pending" and not unresolved_report_generation:
        raise ValidationError("report_pending requires unresolved report generation or QA")
    if data.get("status") == "delivery_pending" and not (unresolved_note or unresolved_report_delivery):
        raise ValidationError("delivery_pending requires unresolved note or report delivery")

    security = require_object(data, "security")
    if security.get("secrets_redacted") is not True:
        raise ValidationError("security.secrets_redacted must be true")
    scan_secrets(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="Path to checkpoint.json")
    args = parser.parse_args()
    try:
        raw = args.checkpoint.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValidationError("root must be an object")
        validate(data, args.checkpoint)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {args.checkpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
