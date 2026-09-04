# Acceptance scenarios

Evaluate observable behavior rather than exact wording. Use isolated artifacts and a non-production test environment. Live Mantis mutation requires an issue approved for private test notes.

Run `python -m unittest discover -s tests -v` from the skill directory before behavioral evaluation. Completion: every test passes, including the positive artifact flow and negative validation, security, path-containment, identity, and delivery-only cases.

## Discovery and setup

1. Natural-language verification intent with one Mantis ID or URL selects this skill; ordinary lookup intent stays with the Mantis skill.
2. A plain writable QA directory works without Git or source code.
3. Missing `qa.yaml` starts the guided interview. Cancellation writes nothing; confirmation produces valid `qa.yaml` and `docs/testing/playbook.md` without secrets.
4. A live issue from another Mantis project stops before SIT mutation and offers guided setup rather than guessing.

## Live grounding and preflight

5. Every run performs live Mantis status and full-issue reads, including current readable notes and relevant attachments.
6. Administrator or shared authentication failure produces `configuration_error + Not Run`, preserves the prior issue verdict, and creates no test data.
7. The browser must visibly prove the configured SIT host, environment, and role before mutation.

## Execution and continuity

8. A fresh safe record can proceed through the project's full prerequisite lifecycle and produce a Pass when every acceptance condition is visibly satisfied.
9. An existing compatible safe checkpoint resumes at its next safe step rather than creating a duplicate record.
   - The checkpoint is discovered even when an interruption occurred before `latest.json` was updated.
   - Multiple compatible active checkpoints stop safely as an ambiguous lock.
10. New live requirements that invalidate a checkpoint mark it superseded before replacement data is created.
11. A configured safe manual-entry fallback can continue when expected automatic population does not occur.
12. An observed SIT system error after safe prerequisites produces a supported Fail or Pending with the retained record, precise blocker, release condition, and next step.
13. Browser-control, download-monitor, rendering, or transient connection failure without product evidence produces `retryable_error + Not Run` rather than Fail or Pending.
14. File upload is verified on the resulting SIT screen. File download is verified by the produced file and relevant content, not only a click or event acknowledgement.

## Artifacts and delivery

15. The immutable result and evidence appear under `docs/testing/<issue-id>/<run-id>/`; hashes validate and `latest.json` resolves inside the issue directory.
16. The JSON contains enough structured evidence for a later report generator while excluding secrets and unnecessary personal data.
17. A material result produces one human-readable private Mantis note derived from the JSON. A matching run marker or content hash prevents duplication.
18. A private-note failure preserves the finalized result and resumes at delivery only; it never repeats SIT. This also holds for a material `Not Run` result.
19. No public note, Mantis field update, status transition, reassignment, or attachment mutation occurs.

## QA usability

20. A non-engineering QA user can start with a natural-language request, complete setup one question at a time, run verification, and understand the final response without editing YAML or reading source code.
