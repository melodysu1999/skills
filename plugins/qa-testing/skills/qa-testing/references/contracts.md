# Workspace and result contracts

This file is the single source of truth for persistent data written by `qa-testing`.

## Workspace

```text
<workspace>/
├── qa.yaml
└── docs/testing/
    ├── playbook.md
    └── <issue-id>/
        ├── latest.json
        └── <run-id>/
            ├── checkpoint.json
            ├── test-result.json
            ├── mantis-note.txt
            ├── evidence/
            ├── report-assets/
            └── Mantis-<zero-padded-issue-id>-測試報告.docx
```

`checkpoint.json` carries active continuation. Once stage 7 completes, the test evidence, execution facts, and verdict in `test-result.json` are immutable. Report projection metadata and the independent `mantis_note` and `report.delivery` fields may change downstream without changing the verdict. `latest.json` is updated after each valid downstream state and always hashes the current result bytes.

## `qa.yaml` version 2

```yaml
schema_version: 2
project:
  name: "Example project"
mantis:
  project_id: "123"
  private_notes: true
  note_policy: "material_change"
environment:
  name: "SIT"
  base_url: "https://sit.example.test/"
  expected_hosts:
    - "sit.example.test"
  expected_markers:
    - "SIT"
authentication:
  administrator:
    strategy: "environment_variables"
    username_env: "SIT_ADMIN_USERNAME"
    password_env: "SIT_ADMIN_PASSWORD"
  special_roles:
    strategy: "connected_source"
    source_description: "Approved role account source"
workflow:
  playbook: "docs/testing/playbook.md"
  source_repositories: []
report:
  policy: "on_request"
  format: "docx"
  page_size: "Letter"
  orientation: "portrait"
  max_pages: 1
  delivery: "private_note_attachment"
safety:
  allowed:
    - "create_test_data"
    - "run_safe_schedules"
    - "download_test_documents"
  approval_required: []
  prohibited:
    - "payment"
    - "send_email"
    - "formal_external_submission"
    - "delete_non_test_data"
    - "destructive_batch_mutation"
```

Required properties:

- `schema_version` equals `2` for newly configured workspaces. Version 1 remains readable and behaves as `report.policy: on_request` until guided setup upgrades it.
- `mantis.project_id` is a quoted string equal to the live issue project ID.
- `mantis.private_notes` is `true`; public-note configuration is invalid.
- `mantis.note_policy` is `material_change`.
- Authentication contains strategies and reference names, never credential values.
- `workflow.playbook` equals `docs/testing/playbook.md`. Artifacts always use `docs/testing`; version 2 does not configure another playbook or artifact root.
- `report.policy` is `always`, `on_request`, or `never`; a current explicit user request overrides the stored default. Version 2 supports only `docx`, Letter portrait, one page, and private-note attachment delivery.
- A source repository entry has `name`, `path`, and `required`; the entire list is optional.
- Safety sets do not conflict. `prohibited` wins if a conflict is discovered.

Mantis access and visible browser interaction are required for an ordinary verification run. Spreadsheet, document, PDF, and source-code capabilities are conditional on the issue and playbook. `documents:documents` is additionally required downstream only when a DOCX report is requested.

## Run identity

Use a filesystem-safe run ID containing the issue and local timestamp, for example `qa-37259-20260904T143000+0800`. Each new SIT execution gets a run ID. A `report-only` or `delivery-only` retry reopens the original downstream fields; it does not create a run, repeat SIT, or alter evidence and verdict.

## `checkpoint.json` version 2

Write checkpoints atomically and validate them with `scripts/validate_checkpoint.py`. Required structure:

```json
{
  "schema_version": 2,
  "run_id": "qa-37259-20260904T143000+0800",
  "updated_at": "2026-09-04T14:35:00+08:00",
  "phase": "executing",
  "status": "running",
  "issue": {
    "id": "37259",
    "project_id": "123",
    "updated_at": "2026-09-04T13:00:00+08:00"
  },
  "project": {"name": "Example project", "environment": "SIT"},
  "continuation": {
    "mode": "fresh",
    "prior_run_id": null,
    "result_finalized": false,
    "last_completed_step": "step-02",
    "next_safe_step": "Complete underwriting"
  },
  "test_data_refs": [],
  "evidence_refs": [],
  "result_path": null,
  "prepared_note": {
    "path": null,
    "sha256": null,
    "status": "not_prepared"
  },
  "report": {
    "requested": true,
    "status": "pending",
    "path": null,
    "sha256": null,
    "delivery_status": "not_ready",
    "attachment_id": null,
    "stored_filename": null,
    "revision": 1
  },
  "security": {"secrets_redacted": true}
}
```

Allowed phases are `grounded`, `bound`, `continuity`, `preflight`, `planned`, `executing`, `classified`, `reporting`, and `delivering`. Allowed checkpoint statuses are `running`, `retryable_error`, `configuration_error`, `report_pending`, `delivery_pending`, and `completed`. Continuation modes are `fresh`, `resume`, `supersede`, `report-only`, and `delivery-only`.

`result_finalized: true` requires a matching, valid `result_path` and phase `classified`, `reporting`, or `delivering`. A `report-only` checkpoint requires a requested report with unresolved generation or QA. A `delivery-only` checkpoint requires an unresolved prepared note or a QA-passed report awaiting attachment delivery. Both modes retain the original test run ID in `run_id` and `continuation.prior_run_id`. Checkpoint report identity must match the result. Relative result, note, report, and evidence paths resolve inside the run directory. Test-data references follow the same privacy rules as the result.

Version 1 checkpoints remain valid for pre-report runs. New and upgraded runs write version 2.

## `test-result.json` version 2

The canonical result is UTF-8 JSON with these top-level objects:

```json
{
  "schema_version": 2,
  "run": {},
  "issue": {},
  "project": {},
  "resume": {},
  "test_plan": {},
  "execution": {},
  "evidence": [],
  "result": {},
  "mantis_note": {},
  "report": {},
  "security": {"secrets_redacted": true}
}
```

### Required fields

- `run`: `id`, `started_at`, `completed_at`, `status`
- `issue`: `id`, `url`, `project_id`, `summary`, `status`, `updated_at`, `fetched_at`, `acceptance_summary`
- `project`: `name`, `environment`, `source_review`
- `resume`: `mode`, `prior_run_id`, `reason`
- `test_plan`: `objective`, `preconditions`, `steps`, `regression_checks`, `prohibited_actions`
- `execution`: `actor`, `last_completed_step`, `next_safe_step`, `test_data_refs`, `steps`; `actor` contains a safe `role` and `account_label`, never a password, token, cookie, or session value
- `result`: `verdict`, `summary`, `blockers`, `release_conditions`, `next_step`
- `mantis_note`: `status`, `private`, `note_id`, `prepared_note_path`, `content_sha256`, `error`
- `report`: `requested`, `status`, `format`, `path`, `sha256`, `assets`, `quality`, `delivery`, `error`
- `security`: `secrets_redacted`

Allowed result run statuses are `completed`, `retryable_error`, and `configuration_error`. Allowed verdicts are `Pass`, `Fail`, `Pending`, and `Not Run`.

Valid terminal combinations:

| Run status | Verdict |
|---|---|
| `completed` | `Pass`, `Fail`, or `Pending` |
| `retryable_error` | `Not Run` |
| `configuration_error` | `Not Run` |

`mantis_note.status` is `pending`, `posted`, `duplicate`, `skipped_immaterial`, or `retryable_error`. `private` is always `true`. Pending, posted, duplicate, and retryable delivery states require `prepared_note_path` and a content hash; posted requires a note ID. The prepared path resolves inside the run directory and normally names `mantis-note.txt`.

Each execution step has an ID, action, expected result, actual result, status, and evidence ID list. Each evidence item has an ID, step ID, type, relative path, SHA-256, capture time, and description. Evidence paths resolve from the run directory and remain inside it.

Safe test-data references may contain non-sensitive record identifiers needed to resume. They exclude credentials, session material, unnecessary personal data, and production data.

Version 1 results remain readable for existing runs. New classifications write version 2 and include `execution.actor` and `report`.

## DOCX report projection

`report.status` is `not_requested`, `pending`, `ready`, `retryable_error`, or `delivered`. Report generation and delivery are downstream states: `retryable_error` does not change `run.status` or `result.verdict`.

When `requested` is `false`, status is `not_requested`, artifact fields are null, assets are empty, and delivery status is `not_requested`. When requested, `format` is `docx`, the delivery revision is a positive integer, and the requested filename is preserved. `ready` and `delivered` require a `.docx` path and SHA-256 inside the run directory.

Each report asset contains `id`, `source_evidence_id`, `type`, `path`, `sha256`, `description`, and `annotation`. Paths stay beneath `report-assets/`, never reuse an `evidence/` path, and hashes cover the derived bytes. An `annotated_screenshot` uses `red_frame` or `equivalent_focus_marker`; the original evidence remains unchanged.

The `quality` object records `page_count`, `page_size`, `orientation`, `max_pages`, `render_reviewed`, `title_style_checked`, `focus_annotations_checked`, and `accessibility_audit_passed`. A report may become `ready` only when page count is one, layout is Letter portrait, and every boolean gate is true on the final bytes.

The nested delivery object contains:

```json
{
  "status": "posted",
  "note_id": "98123",
  "attachment_id": "45678",
  "requested_filename": "Mantis 034199 測試報告.docx",
  "stored_filename": "Mantis 034199 測試報告-2.docx",
  "revision": 2,
  "supersedes_attachment_id": "44567",
  "error": null
}
```

Allowed delivery statuses are `not_requested`, `not_ready`, `pending`, `posted`, `duplicate`, and `retryable_error`. Posted or duplicate delivery requires the observed note ID, attachment ID, and server-stored filename. A delivered revision greater than one requires `supersedes_attachment_id`; the stored filename may differ from the requested filename.

## `latest.json` version 1

```json
{
  "schema_version": 1,
  "run_id": "qa-37259-20260904T143000+0800",
  "result_path": "qa-37259-20260904T143000+0800/test-result.json",
  "sha256": "<lowercase sha256>"
}
```

The result path is relative to the issue directory and resolves inside it. The hash is computed from the immutable bytes of `test-result.json`.

## Private note projection

The Mantis note is the detailed human projection of the validated JSON, not a second independent verdict. It contains environment, safe account label or role, acceptance focus, safe test-data identifiers, work completed, expected versus actual behavior, evidence descriptions, verdict or run error, blocker, release condition, recommendation, and a run marker. It omits local paths, raw JSON, secrets, and unnecessary personal data.

The DOCX is the concise user-facing projection. It contains the same canonical verdict but omits engineering detail and full execution steps. First delivery should attach the QA-passed DOCX to the detailed private note. Later revisions use a new private note and attachment; Mantis attachment IDs and server-stored filenames are durable identities, while local filenames are only requested names.
