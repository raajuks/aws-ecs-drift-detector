# AWS ECS Drift Detector

An automated ECS task drift detection and remediation service built with Python, Terraform, and GitHub Actions. Detects when ECS service running task counts diverge from desired counts and triggers automatic remediation.

---

## Architecture

┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    VPC (10.0.0.0/16)                 │   │
│  │                                                      │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐  │   │
│  │  │  Public Subnet  │    │    Public Subnet         │  │   │
│  │  │  us-east-1a     │    │    us-east-1b            │  │   │
│  │  │                 │    │                          │  │   │
│  │  │  ┌───────────┐  │    │  ┌─────────────────┐    │  │   │
│  │  │  │ ECS       │  │    │  │ ECS Sample App  │    │  │   │
│  │  │  │ Drift     │  │    │  │ (nginx x2)      │    │  │   │
│  │  │  │ Detector  │  │    │  │ [monitored]     │    │  │   │
│  │  │  └─────┬─────┘  │    │  └─────────────────┘    │  │   │
│  │  └────────┼────────┘    └──────────────────────────┘  │   │
│  └───────────┼──────────────────────────────────────────┘   │
│              │                                              │
│              ▼                                              │
│  ┌───────────────────┐    ┌──────────────────────────────┐  │
│  │   CloudWatch      │    │          SNS Topic           │  │
│  │   - Log Groups    │───▶│   drift-alerts               │  │
│  │   - Custom Metrics│    │   (email notification)       │  │
│  │   - Alarms        │    └──────────────────────────────┘  │
│  │   - Dashboard     │                                      │
│  └───────────────────┘                                      │
│                                                             │
│  ┌───────────────────┐    ┌──────────────────────────────┐  │
│  │   ECR Repository  │    │   S3 + DynamoDB              │  │
│  │   drift-detector  │    │   Terraform State Backend    │  │
│  └───────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
GitHub Actions
──────────────
PR  → fmt → validate → tflint → plan (posted as PR comment)
Main → apply → smoke test (ECS service health check)
Service → lint → test → docker build → ECR push → ECS deploy

---

## How It Works

The drift detector runs as an ECS Fargate service and polls all ECS clusters every 60 seconds via the AWS SDK. For each service it compares `desiredCount` vs `runningCount`:

- **No drift** → logs OK status, emits scan summary metric
- **Drift detected, pending > 0** → ECS is already self-healing, logs event, emits metric, skips remediation
- **Drift detected, pending = 0** → calls `update_service(forceNewDeployment=True)` to trigger ECS scheduler reconciliation, emits remediation metric, sends SNS alert

All events are logged as structured JSON for CloudWatch Log Insights queries.

---

## Project Structure

aws-ecs-drift-detector/
├── .github/workflows/
│   ├── terraform.yml        # Terraform CI/CD pipeline
│   └── python.yml           # Python lint, test, build, deploy
├── infra/
│   ├── bootstrap/           # One-time state backend setup
│   ├── modules/
│   │   ├── ecs/             # Cluster, task definitions, IAM
│   │   ├── networking/      # VPC, subnets, security groups
│   │   └── observability/   # CloudWatch, SNS, dashboard
│   └── environments/dev/    # Root module, backend config
├── service/
│   ├── app/
│   │   ├── detector.py      # ECS polling and drift detection
│   │   ├── remediator.py    # Auto-remediation via update_service
│   │   ├── metrics.py       # CloudWatch custom metrics publisher
│   │   └── api.py           # Flask /health and /status endpoints
│   ├── tests/               # Unit tests with mocked AWS calls
│   ├── Dockerfile           # Non-root, health-checked container
│   └── main.py              # Entry point, threading model
├── CLAUDE.md                # AI-native development workflow log
└── README.md

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | Flask |
| AWS SDK | boto3 |
| Infrastructure | Terraform >= 1.6, AWS provider ~> 5.0 |
| Container registry | Amazon ECR |
| Compute | ECS Fargate |
| Observability | CloudWatch Logs, Metrics, Alarms, Dashboard |
| Alerting | SNS → Email |
| CI/CD | GitHub Actions |
| State backend | S3 + DynamoDB |
| AI collaboration | Claude (Anthropic) via Claude Code |

---

## Key Design Decisions

**Why Fargate over EC2?**
No cluster node management required. Immutable infrastructure — each deployment replaces containers entirely rather than mutating running instances.

**Why `forceNewDeployment` for remediation?**
The simplest correct approach. Rather than manually calculating task counts and launching tasks, we delegate reconciliation to the ECS scheduler which already knows the desired state. This avoids race conditions and duplicated logic.

**Why in-memory status store?**
For MVP simplicity — no external dependency (Redis, DynamoDB) required to demonstrate the /status endpoint. Clearly documented as an iteration target in CLAUDE.md.

**Why structured JSON logging?**
Native compatibility with CloudWatch Log Insights. The dashboard includes a pre-built query that filters `event_type = DRIFT_DETECTED` events directly from log data.

**Why separate bootstrap Terraform?**
Chicken-and-egg problem — you cannot store Terraform state for the resource that creates your state bucket. Bootstrap runs once manually; all subsequent infrastructure uses the remote backend.

---

## Local Development

### Prerequisites
- Python 3.12+
- Docker Desktop
- Terraform >= 1.6
- AWS CLI configured

### Run Tests

```bash
cd aws-ecs-drift-detector
pip install -r service/requirements.txt
pytest service/tests/ -v
```

### Run Locally

```bash
export AWS_REGION=us-east-1
export ENVIRONMENT=dev
export PROJECT_NAME=ecs-drift-detector
export POLL_INTERVAL=60
export SNS_TOPIC_ARN=arn:aws:sns:us-east-1:502140064534:ecs-drift-detector-drift-alerts

cd service
python -m service.main
```

### Deploy Infrastructure

```bash
# One-time bootstrap
cd infra/bootstrap
terraform init && terraform apply

# Main infrastructure
cd infra/environments/dev
terraform init && terraform apply
```

---

## Observability

### CloudWatch Dashboard
Navigate to CloudWatch → Dashboards → `ecs-drift-detector-dashboard` to see:
- Drift events detected over time
- Remediations triggered
- Task count delta per service

### Log Insights Query

SOURCE '/ecs/ecs-drift-detector/detector'
| fields @timestamp, service_name, desired_count, running_count, action
| filter event_type = 'DRIFT_DETECTED'
| sort @timestamp desc
| limit 20

### Endpoints
| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness probe — returns 200 if container is running |
| `GET /status` | Last scan time, total scans, recent drift events |

---

## CI/CD Pipeline

### On Pull Request (infra changes)
`terraform fmt` → `terraform validate` → `terraform plan` → plan posted as PR comment

### On Merge to Main (infra changes)
`terraform apply` → ECS smoke test

### On Merge to Main (service changes)
`flake8 lint` → `pytest` → `docker build` → `ECR push` → `ECS force deploy` → smoke test

---

## Future Iterations

- Add private subnets with NAT gateway for production security posture
- Replace in-memory status store with DynamoDB for persistence across restarts
- Add Slack notification channel alongside email
- Extend monitoring to cover ECS service CPU/memory drift from baseline
- Add terraform workspaces for multi-environment support (staging, prod)
- Implement drift history trending with CloudWatch Contributor Insights

---

## AI-Native Development

See [CLAUDE.md](./CLAUDE.md) for a detailed log of how Claude (Anthropic) was used as a development collaborator throughout this project — from architecture decisions to test edge cases to security posture review.
