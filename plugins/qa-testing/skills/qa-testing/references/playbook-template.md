# Project QA playbook

Write project rules as observable safe paths. Name existing skills or tools only where choosing the wrong capability changes the result.

## Environment identity

- Allowed SIT hosts and legitimate authentication redirects
- Visible application, environment, version, and role markers

## Authentication and roles

- Administrator preflight
- Approved source for special-role accounts
- Safe role-switching order
- Evidence that distinguishes configuration failure from product behavior

## Safe test data

- Non-sensitive identifiers and naming rules
- Product or scenario selection rules
- Conditions for reusing, superseding, or discarding a checkpoint

## Standard lifecycle

- Minimum safe record creation
- Review, approval, scheduling, issuance, or equivalent stages
- Visible checkpoint and safe record reference after each material stage
- Treatment of identifiers copied from production or UAT reports

## Special workflows

- Role-specific verification
- Safe manual fallback when automatic field population does not occur
- File preparation, upload, download, print, and content verification
- Project schedules that may be run safely

## Evidence and classification

- Required evidence by stage
- Product failure signals
- Product or data blockers
- Automation and tool failure signals

## Safety

- Safe actions
- Approval-required actions and stopping points
- Prohibited actions

## Completion

- Pass, Fail, and Pending conditions
- Required blocker, release condition, checkpoint, and next-step detail
