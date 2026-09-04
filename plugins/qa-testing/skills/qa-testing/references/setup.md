# Guided setup

Setup establishes stable project policy. It ends before issue testing begins.

## Interview

Ask one plain-language question at a time. Offer a recommended answer and a safe `不知道／稍後設定` choice when the field is optional. Reuse facts from the representative issue and environment instead of asking the QA user for IDs the agent can discover. Ask how the QA user normally signs in or obtains a role account, then translate that answer into the technical strategy; do not ask them to design authentication or safety schemas.

1. Obtain one representative Mantis ID or URL. Run the Mantis status check and fetch the full issue; derive its project ID and name. Completion: both values came from live Mantis.
2. Confirm the workspace label, target environment, SIT base URL, and visible markers that prove the correct environment loaded. Completion: the allowed final host and at least one identity check are explicit.
3. Choose administrator and special-role authentication strategies. Store an existing-session strategy, environment-variable names, or an approved connected-source description. Completion: every required role has a strategy and no secret value entered the conversation or draft.
4. Confirm the action policy: safe, approval-required, and prohibited. Completion: the three sets do not conflict and risky external actions have an explicit stopping point.
5. Discover optional source repositories and project instructions. A QA workspace without source code is valid. Completion: each discovered source is confirmed, or source review is recorded as optional and unavailable.
6. Draft `docs/testing/playbook.md` from confirmed project material using [playbook-template.md](playbook-template.md). Review it section by section. Completion: environment identity, authentication, safe data lifecycle, special workflows, evidence, safety, and verdict rules are each confirmed or explicitly deferred.
7. Build `qa.yaml` according to [contracts.md](contracts.md), then show a readable summary. Completion: the user explicitly approves the summary.
8. Write both files atomically, reread them, resolve every configured relative path against the workspace root, and scan for literal secrets. Completion: required values are present, paths stay inside the workspace, private notes are enforced, and neither file contains a secret.

An interrupted interview leaves no partial configuration. If a non-destructive connection or login preflight is requested, run it after the files validate and report it as setup evidence, never as an issue verdict. When setup began from an issue verification request, continue with the Verify branch after successful setup; when setup was the entire request, stop after the setup summary.

## Update

For an existing workspace, read both files, ask only about the requested or invalid settings, and show old versus proposed values without resolving secret references. Preserve unknown keys and unchanged playbook sections. Apply the edit once after confirmation, then repeat the setup validation criteria.

A live issue from another Mantis project is a workspace mismatch. Offer setup in another directory or an explicitly approved replacement; never repurpose the current workspace silently.
