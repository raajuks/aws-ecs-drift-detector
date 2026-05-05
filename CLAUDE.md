# CLAUDE.md — AI-Native Development Workflow

This project was built using Claude (Anthropic) as a primary development collaborator,
reflecting the team's own use of Claude Code in their stack.

## How Claude Was Used

### Architecture Design
Claude was used to reason through the overall system design — specifically the decision
to separate concerns into four Python modules (detector, remediator, metrics, api) and
three Terraform modules (networking, ecs, observability). The modular approach was
validated through back-and-forth discussion about long-term maintainability vs complexity.

### Terraform Module Structure
Claude helped design idiomatic HCL structure including:
- Separation of bootstrap state backend from main infrastructure
- IAM least-privilege policy scoping for ECS task roles
- Output chaining between modules (networking ? ecs, observability ? ecs)

### Python Service Logic
Claude assisted with:
- Designing the DriftEvent dataclass to carry all relevant context through the pipeline
- The decision to use `requires_remediation=False` when pending > 0 (ECS is already
  self-healing, no need to force a new deployment)
- Structured JSON logging format for CloudWatch Log Insights compatibility
- Threading model: Flask API in daemon thread, detector loop in main thread

### Test Coverage
Claude generated unit tests with explicit discussion of edge cases:
- Drift with pending tasks (should NOT remediate)
- AWS ClientError handling in remediator
- Paginator mocking for list_clusters and list_services
- Status endpoint reflecting in-memory drift event state

### Key Design Decisions Influenced by AI Collaboration

| Decision | Rationale |
|---|---|
| Fargate over EC2 | No cluster node management, immutable infrastructure |
| forceNewDeployment for remediation | Simplest correct approach; ECS scheduler reconciles |
| In-memory status store (50 events) | Avoids external dependency for MVP; clearly noted as iteration target |
| Structured JSON logs | Native CloudWatch Log Insights compatibility |
| Non-root Docker user | Security best practice surfaced during review |

## Iteration Notes
- Initial design used a single `main.py` monolith; Claude suggested splitting into
  focused modules for testability
- SNS alert email subscription was added after Claude flagged that CloudWatch alarms
  alone do not notify humans without an action target
- The `prevent_destroy` lifecycle rule on the S3 state bucket was added after Claude
  flagged the risk of accidental state loss

## What Was Not AI-Generated
- AWS account setup and credential configuration
- Git workflow and commit decisions
- Final review of IAM permissions for security posture
- The decision to use ECS task drift as the monitoring target (domain judgment)
