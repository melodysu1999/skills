# One-issue verification

Execute these stages in order. A completion criterion is a durable boundary: update `checkpoint.json` atomically and run `scripts/validate_checkpoint.py` after crossing it. The report-only and delivery-only branches explicitly skip every SIT stage.

## 1. Ground the issue

Resolve exactly one ID or same-origin Mantis issue URL. Use `operations:mantis` and its live status taxonomy, then fetch the current full issue. Read every note visible to the authorized account and the attachment list; inspect attachments that affect reproduction or acceptance.

Completion: the run holds a bounded live snapshot containing project ID, title, status, updated time, description, reproduction details, acceptance information, readable notes, and relevant attachment evidence. A live-read failure ends as a run error without an SIT verdict.

## 2. Bind the project

Read `qa.yaml` and the configured playbook, which version 1 requires to equal `docs/testing/playbook.md`. Match the live Mantis project ID exactly and resolve configured paths inside the workspace. Use Setup when either file is absent; stop on invalid or mismatched configuration.

Completion: one validated environment and playbook govern the run.

## 3. Reconcile continuity

Enumerate every direct child `docs/testing/<issue-id>/*/checkpoint.json` before consulting `latest.json`. Validate each checkpoint and retain active statuses: `running`, `retryable_error`, `configuration_error`, `report_pending`, and `delivery_pending`. More than one compatible active checkpoint is an ambiguous lock and stops the run before SIT mutation. Then read `latest.json` and its referenced result when present.

A compatible checkpoint has the same issue, Mantis project, and SIT environment; its safe data still exists; and no live requirement change invalidates its acceptance mapping or next step. A checkpoint validation failure is quarantined from resume and reported; it never silently becomes permission to start fresh when it may own test data.

Choose one mode:

- **fresh:** no compatible checkpoint exists;
- **resume:** a compatible SIT checkpoint has unfinished product verification;
- **supersede:** record the material incompatibility before replacement data is created;
- **report-only:** classification is finalized and the requested DOCX is missing, failed a document QA gate, or needs a user-requested revision;
- **delivery-only:** classification is finalized and a prepared private note or QA-passed DOCX has unresolved private delivery, including a material `Not Run` result.

For report-only and delivery-only, keep the original run ID, verdict, evidence, and completed SIT data. Skip stages 4–7; continue at stage 8 for report-only and stage 9 for delivery-only. Do not require an SIT session, role, test-data preflight, or new test data. A report-only revision may create new files only under `report-assets/` and the report path.

Completion: the mode, governing run ID, and next safe step are explicit. A downstream failure never justifies rebuilding completed SIT data.

## 4. Preflight SIT

For fresh, resume, or supersede only, confirm required installed capabilities, allowed final host, visible environment identity, authentication, role availability, artifact directory writability, and issue-specific prerequisites. Conditional file capabilities are required only when product testing uses them. Report authoring capability is checked downstream only when a report is requested. Read relevant source code when configured and available.

Completion: the correct environment and required role are visibly confirmed before test-data mutation. Failure produces `configuration_error` or `retryable_error` with verdict `Not Run`; it does not produce product Pending.

## 5. Plan

Derive a test plan from live Mantis, the project playbook, relevant attachments, optional source review, and the accepted checkpoint. Include objective, preconditions, safe data strategy, role, steps, expected results, adjacent regression checks, evidence required, and stopping points.

Completion: every acceptance condition maps to at least one executable step and expected observable result; every planned mutation is safe or separately authorized.

## 6. Execute visibly

Delegate visible interaction to `browser:control-in-app-browser`. Use `spreadsheets:Spreadsheets`, `documents:documents`, or `pdf:pdf` here only when product verification itself requires that file type; report authoring belongs to stage 8. Follow the playbook's safe lifecycle, using visible UI interactions and screenshots or produced files as evidence. Record the safe account label or role without credentials. After each material stage, record the safe data reference, last completed step, evidence, and next step.

Tool acknowledgements, synthetic DOM events, issue prose, and source code are supporting information rather than proof. Verify uploads on the resulting SIT screen; verify downloads by checking the resulting file and its relevant content. Use safe manual entry allowed by the playbook when expected automatic population fails.

Completion: every planned acceptance step has actual evidence or a precise blocker. Stop at the first unsafe action or unresolved prerequisite without erasing completed checkpoints.

## 7. Classify and package

Assign run status and verdict using [contracts.md](contracts.md):

- observed conformance -> `completed + Pass`;
- observed product nonconformance -> `completed + Fail`;
- product, data, deployment, role, external-system, or requirement blocker after every safe attempt required by the plan -> `completed + Pending`;
- automation, browser-control, download-monitor, rendering, or transient connection failure without product evidence -> `retryable_error + Not Run`;
- invalid project, authentication, or required capability configuration -> `configuration_error + Not Run`.

Write the version 2 result and evidence beneath `docs/testing/<issue-id>/<run-id>/`. Record whether the report is requested from `qa.yaml` or the current user instruction. Render the detailed `mantis-note.txt`, record its relative path and content hash in the result, then run `scripts/validate_result.py`. Preserve these exact note bytes for delivery and retries.

Completion: summary, evidence, blockers, release conditions, actor label, last safe checkpoint, next step, and report intent support the classification; the preliminary result validates; and the prepared note hash is recorded even when downstream work has not succeeded.

## 8. Build and verify the optional DOCX

Skip this stage when reporting is neither configured nor requested. Otherwise read [report.md](report.md), then delegate creation or revision to `documents:documents`. Supply only the validated result, hashed evidence, report contract, and user-approved revision request. Do not ask the document workflow to decide the verdict.

Keep the first report delivery at revision 1. Create focus-marked image copies beneath `report-assets/`; never modify `evidence/`. After the document skill finishes its final render, page inspection, title-line check, focus-marker check, and accessibility audit, hash the final DOCX and every derived asset and record their paths and QA gates in `test-result.json`. Validate the result again.

If authoring or any gate fails, record `report.status=retryable_error`, write a `report-only` checkpoint with the precise failed gate and next safe step, and stop without Mantis delivery. A user-requested post-upload revision increments the report revision and records the attachment ID it supersedes only after the new revision passes all gates.

Completion: reporting is `not_requested`, or the final DOCX is `ready`, hashed, derived from the canonical verdict, and has passed every pre-upload gate.

## 9. Deliver privately

Use `operations:mantis get-notes <issue-id> --last 20` immediately before delivery. Hash readable note bodies and compare them with the prepared content hash; also search for the original run marker. Either match proves the note already exists.

When no match exists and the result contains material new information, add the detailed private note. If a revision-1 DOCX is ready, make the preferred first delivery atomic from the workflow's perspective by calling `operations:mantis add-note <issue-id> --text <prepared-note> --private --file <final-docx>`. Without a report, call the same command without `--file`. Material information is a changed verdict, evidence, blocker, release condition, completed stage, next safe step, or requested report revision. Repeating the same result without one of those changes is immaterial.

Do not upload until every document QA gate is true. Read the upload response and attachment listing rather than assuming the local filename was retained. Record the note ID, attachment ID, requested filename, server-stored filename, and revision. Mantis may suffix a repeated filename; never overwrite, delete, or treat an older attachment as replaced.

If the POST response is uncertain or times out, immediately read the latest 20 notes and current attachment list again. Repeat the note marker/hash comparison and match the report using observed attachment identity. Mark an observed delivery `duplicate`; otherwise mark the unresolved note or report delivery `retryable_error`. A retry reuses the same run ID, prepared bytes, hashes, and verdict.

When the detailed note already exists but its report attachment still needs delivery, add a short private note with the report file rather than repeating the detailed note. For a user-requested revision after a prior successful upload, the new private note must state `請以本回話附件為準` and the result must record the superseded attachment ID.

Record every observed note and attachment delivery outcome, validate the result again, then run `scripts/update_latest.py` last so its hash covers the finalized bytes. Use the independent `mantis_note` and `report.delivery` states; downstream failure does not change `run.status` or `result.verdict`.

Completion: `test-result.json` validates, `latest.json` resolves to it with a matching hash, and every requested private note or report attachment is confirmed, deduplicated, intentionally skipped, or checkpointed for report-only or delivery-only retry. No Mantis status, assignee, or other issue field changes.
