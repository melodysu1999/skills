---
name: qa-testing
description: Verify one Mantis issue in SIT from an issue ID or URL, or guide first-time setup of a QA workspace. Orchestrates live issue reading, safe resumable testing, evidence capture, JSON under docs/testing, and a deduplicated private Mantis note. Use for explicit test, retest, verification, or 驗測 intent; ordinary Mantis lookup, batch queues, Sheet synchronization, and polished report generation belong elsewhere.
---

# QA Testing

Coordinate existing Mantis, browser, spreadsheet, document, and PDF capabilities. The current workspace is the durable QA project; it may be a plain writable folder without source code or Git.

## Choose the entry branch

- **Setup:** The user asks to configure QA testing, or `qa.yaml` is missing or mismatched. Read [references/setup.md](references/setup.md). Setup is complete when confirmed `qa.yaml` and `docs/testing/playbook.md` both validate on reread. When an issue verification request triggered setup, continue into Verify in the same task after setup succeeds.
- **Verify:** The user provides exactly one Mantis ID or issue URL and project setup is valid. Read [references/run.md](references/run.md) and [references/contracts.md](references/contracts.md). Verification is complete when the result artifact validates and every material external delivery is either confirmed or checkpointed for retry.
- **Evaluate:** The skill or workflow is being reviewed or changed. Read [references/acceptance.md](references/acceptance.md).

## Invariants

- Fetch the full live issue every run after the Mantis status check; local artifacts add continuity but never replace live requirements.
- Match the issue's Mantis project ID to `qa.yaml` before SIT mutation. Route missing configuration to Setup; record invalid configuration as `configuration_error + Not Run`.
- Pass environment and authentication preflight before test-data mutation. A shared preflight failure is a run error, not product Pending.
- Ground verdicts in visible SIT behavior and captured evidence. Source code and DOM state inform the plan but do not replace real interaction.
- Resume a compatible checkpoint. Supersede it only when requirements, environment, or test data materially invalidate the continuation.
- Store secrets only in approved external providers. Artifacts, screenshots, tool output, chat, and Mantis remain secret-free.
- Limit Mantis mutation to a private note containing material new progress. Deduplicate before posting; delivery failure resumes at the note step rather than rerunning SIT.
- Follow the project playbook's positive safe path. A prohibited action is a hard stop unless the user separately authorizes that exact action.

Return a readable summary with the issue, environment, work completed, verdict or run error, next step, artifact location, and private-note delivery status. Keep JSON in the artifact, not the chat response.
