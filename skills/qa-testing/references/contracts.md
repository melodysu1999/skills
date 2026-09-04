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
            └── evidence/
```

`checkpoint.json` carries active continuation. Once stage 7 completes, test evidence and verdict in `test-result.json` are immutable; only `mantis_note` delivery fields may change until delivery reaches a terminal state. `latest.json` is updated after each valid delivery state and always hashes the current result bytes.

## `qa.yaml` version 1

```yaml
schema_version: 1
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

- `schema_version` equals `1`.
- `mantis.project_id` is a quoted string equal to the live issue project ID.
- `mantis.private_notes` is `true`; public-note configuration is invalid.
- `mantis.note_policy` is `material_change`.
- Authentication contains strategies and reference names, never credential values.
- `workflow.playbook` equals `docs/testing/playbook.md`. Artifacts always use `docs/testing`; version 1 does not configure another playbook or artifact root.
- A source repository entry has `name`, `path`, and `required`; the entire list is optional.
- Safety sets do not conflict. `prohibited` wins if a conflict is discovered.

Mantis access and visible browser interaction are required for an ordinary verification run. Spreadsheet, document, PDF, and source-code capabilities are conditional on the issue and playbook.

## Run identity

Use a filesystem-safe run ID containing the issue and local timestamp, for example `qa-37259-20260904T143000+0800`. Each new SIT execution gets a run ID. A delivery-only retry reopens the original run's delivery fields and prepared note; it does not create a run or rerender the note.

## `checkpoint.json` version 1

Write checkpoints atomically and validate them with `scripts/validate_checkpoint.py`. Required structure:

```json
{
  "schema_version": 1,
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
  "security": {"secrets_redacted": true}
}
```

Allowed phases are `grounded`, `bound`, `continuity`, `preflight`, `planned`, `executing`, `classified`, and `delivering`. Allowed checkpoint statuses are `running`, `retryable_error`, `configuration_error`, `delivery_pending`, and `completed`. Continuation modes match the run workflow.

`result_finalized: true` requires a matching, valid `result_path` and phase `classified` or `delivering`. A delivery-only checkpoint additionally requires a pending or retryable prepared note path and hash; both `run_id` and `continuation.prior_run_id` retain the original test run ID. Relative result, note, and evidence paths resolve inside the run directory. Test-data references follow the same privacy rules as the result.

## `test-result.json` version 1

The canonical result is UTF-8 JSON with these top-level objects:

```json
{
  "schema_version": 1,
  "run": {},
  "issue": {},
  "project": {},
  "resume": {},
  "test_plan": {},
  "execution": {},
  "evidence": [],
  "result": {},
  "mantis_note": {},
  "security": {"secrets_redacted": true}
}
```

### Required fields

- `run`: `id`, `started_at`, `completed_at`, `status`
- `issue`: `id`, `url`, `project_id`, `summary`, `status`, `updated_at`, `fetched_at`, `acceptance_summary`
- `project`: `name`, `environment`, `source_review`
- `resume`: `mode`, `prior_run_id`, `reason`
- `test_plan`: `objective`, `preconditions`, `steps`, `regression_checks`, `prohibited_actions`
- `execution`: `last_completed_step`, `next_safe_step`, `test_data_refs`, `steps`
- `result`: `verdict`, `summary`, `blockers`, `release_conditions`, `next_step`
- `mantis_note`: `status`, `private`, `note_id`, `prepared_note_path`, `content_sha256`, `error`
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

The Mantis note is a human projection of the validated JSON, not a second independent verdict. It contains environment, work completed, expected versus actual behavior, evidence descriptions, verdict or run error, blocker, release condition, next step, and a run marker. It omits local paths, raw JSON, secrets, and unnecessary personal data.
