# One-issue verification

Execute these stages in order. A completion criterion is a durable boundary: update `checkpoint.json` atomically and run `scripts/validate_checkpoint.py` after crossing it. The delivery-only branch explicitly skips every SIT stage.

## 1. Ground the issue

Resolve exactly one ID or same-origin Mantis issue URL. Use `operations:mantis` and its live status taxonomy, then fetch the current full issue. Read every note visible to the authorized account and the attachment list; inspect attachments that affect reproduction or acceptance.

Completion: the run holds a bounded live snapshot containing project ID, title, status, updated time, description, reproduction details, acceptance information, readable notes, and relevant attachment evidence. A live-read failure ends as a run error without an SIT verdict.

## 2. Bind the project

Read `qa.yaml` and the configured playbook, which version 1 requires to equal `docs/testing/playbook.md`. Match the live Mantis project ID exactly and resolve configured paths inside the workspace. Use Setup when either file is absent; stop on invalid or mismatched configuration.

Completion: one validated environment and playbook govern the run.

## 3. Reconcile continuity

Enumerate every direct child `docs/testing/<issue-id>/*/checkpoint.json` before consulting `latest.json`. Validate each checkpoint and retain active statuses: `running`, `retryable_error`, `configuration_error`, and `delivery_pending`. More than one compatible active checkpoint is an ambiguous lock and stops the run before SIT mutation. Then read `latest.json` and its referenced result when present.

A compatible checkpoint has the same issue, Mantis project, and SIT environment; its safe data still exists; and no live requirement change invalidates its acceptance mapping or next step. A checkpoint validation failure is quarantined from resume and reported; it never silently becomes permission to start fresh when it may own test data.

Choose one mode:

- **fresh:** no compatible checkpoint exists;
- **resume:** a compatible SIT checkpoint has unfinished product verification;
- **supersede:** record the material incompatibility before replacement data is created;
- **delivery-only:** classification is finalized and a prepared private note has unresolved delivery, including a material `Not Run` result.

For delivery-only, keep the original run ID and prepared note bytes. Skip stages 4–7 and continue directly at stage 8; do not require an SIT session, role, file capability, or test-data preflight.

Completion: the mode, governing run ID, and next safe step are explicit. A downstream failure never justifies rebuilding completed SIT data.

## 4. Preflight SIT

For fresh, resume, or supersede only, confirm required installed capabilities, allowed final host, visible environment identity, authentication, role availability, artifact directory writability, and issue-specific prerequisites. Conditional file capabilities are required only when the plan uses them. Read relevant source code when configured and available.

Completion: the correct environment and required role are visibly confirmed before test-data mutation. Failure produces `configuration_error` or `retryable_error` with verdict `Not Run`; it does not produce product Pending.

## 5. Plan

Derive a test plan from live Mantis, the project playbook, relevant attachments, optional source review, and the accepted checkpoint. Include objective, preconditions, safe data strategy, role, steps, expected results, adjacent regression checks, evidence required, and stopping points.

Completion: every acceptance condition maps to at least one executable step and expected observable result; every planned mutation is safe or separately authorized.

## 6. Execute visibly

Delegate visible interaction to `browser:control-in-app-browser`. Use `spreadsheets:Spreadsheets`, `documents:documents`, or `pdf:pdf` only when the plan requires that file type. Follow the playbook's safe lifecycle, using visible UI interactions and screenshots or produced files as evidence. After each material stage, record the safe data reference, last completed step, evidence, and next step.

Tool acknowledgements, synthetic DOM events, issue prose, and source code are supporting information rather than proof. Verify uploads on the resulting SIT screen; verify downloads by checking the resulting file and its relevant content. Use safe manual entry allowed by the playbook when expected automatic population fails.

Completion: every planned acceptance step has actual evidence or a precise blocker. Stop at the first unsafe action or unresolved prerequisite without erasing completed checkpoints.

## 7. Classify and package

Assign run status and verdict using [contracts.md](contracts.md):

- observed conformance -> `completed + Pass`;
- observed product nonconformance -> `completed + Fail`;
- product, data, deployment, role, external-system, or requirement blocker after every safe attempt required by the plan -> `completed + Pending`;
- automation, browser-control, download-monitor, rendering, or transient connection failure without product evidence -> `retryable_error + Not Run`;
- invalid project, authentication, or required capability configuration -> `configuration_error + Not Run`.

Write the result and evidence beneath `docs/testing/<issue-id>/<run-id>/`. Render `mantis-note.txt`, record its relative path and content hash in the result, then run `scripts/validate_result.py`. Preserve these exact note bytes for delivery and retries.

Completion: summary, evidence, blockers, release conditions, last safe checkpoint, and next step support the classification; the preliminary result validates; and the prepared note hash is recorded even when delivery has not succeeded.

## 8. Deliver privately

Use `operations:mantis get-notes <issue-id> --last 20` immediately before delivery. Hash readable note bodies and compare them with the prepared content hash; also search for the original run marker. Either match proves the note already exists.

When no match exists and the result contains material new information, call `operations:mantis add-note <issue-id> --text <prepared-note> --private`. Material information is a changed verdict, evidence, blocker, release condition, completed stage, or next safe step. Repeating the same result without one of those changes is immaterial.

If the POST response is uncertain or times out, immediately read the latest 20 notes again and repeat the marker/hash comparison. Mark delivery `duplicate` when the note is observed; otherwise mark it `retryable_error`. A retry reuses the same run ID, `mantis-note.txt`, and content hash.

Record the observed note ID or delivery outcome, validate the result again, then run `scripts/update_latest.py` last so its hash covers the finalized bytes. Use `mantis_note.status=retryable_error` for an unresolved delivery; do not invent another run-error enum.

Completion: `test-result.json` validates, `latest.json` resolves to it with a matching hash, and the private note is confirmed, deduplicated, intentionally skipped as immaterial, or checkpointed for delivery-only retry.
