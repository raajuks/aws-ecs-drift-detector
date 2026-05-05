# AWS ECS Drift Detector

An automated ECS task drift detection and remediation service built with Python, Terraform, and GitHub Actions. Detects when ECS service running task counts diverge from desired counts and triggers automatic remediation.

---

## Architecture

```
GitHub Actions CI/CD
─────────────────────────────────────────────────────
PR   → fmt → validate → plan (posted as PR comment)
Main → apply → ECS smoke test
Service → lint → pytest → docker build → ECR push → ECS deploy

AWS Infrastructure
─────────────────────────────────────────────────────
VPC (10.0.0.0/16)
  ├── Public Subnet us-east-1a
  │     └── ECS Fargate: drift-detector service
  └── Public Subnet us-east-1b
        └── ECS Fargate: sample-app (nginx x2, monitored target)

ECS Drift Detector
  ├── Polls all ECS clusters every 60s via boto3
  ├── Detects desiredCount vs runningCount delta
  ├── Auto-remediates via update_service(forceNewDeployment=True)
  └── Exposes /health and /status Flask endpoints

Observability
  ├── CloudWatch Log Groups (structured JSON)
  ├── CloudWatch Custom Metrics (DriftDetected, RemediationTriggered)
  ├── CloudWatch Alarms → SNS Topic → Email alerts
  └── CloudWatch Dashboard (4 widgets)

State Backend
  ├── S3 bucket (versioned, encrypted, public access blocked)
  └── DynamoDB table (state locking)
```

---

## How It Works

The drift detector runs as an ECS Fargate service and polls all ECS clusters every 60 seconds. For each service it compares `desiredCount` vs `runningCount`:

- **No drift** → logs OK status, emits scan summary metric
- **Drift detected, pending > 0** → ECS is already self-healing, logs event, emits metric, skips remediation
- **Drift detected, pending = 0** → calls `update_service(forceNewDeployment=True)`, emits remediation metric, sends SNS alert

All events are logged as structured JSON for CloudWatch Log Insights compatibility.

---

## Project Structure

```
aws-ecs-drift-detector/
├── .github/workflows/
│   ├── terraform.yml        # Terraform CI/CD pipeline
│   └── python.yml           # Python lint, test, build, deploy
├── infra/
│   ├── bootstrap/           # One-time state backend setup (run manually)
│   ├── modules/
│   │   ├── ecs/             # Cluster, task definitions, IAM roles
│   │   ├── networking/      # VPC, subnets, security groups
│   │   └── observability/   # CloudWatch, SNS, dashboard
│   └── environments/dev/    # Root module, backend config, tfvars
├── service/
│   ├── app/
│   │   ├── detector.py      # ECS polling and drift detection logic
│   │   ├── remediator.py    # Auto-remediation via update_service
│   │   ├── metrics.py       # CloudWatch custom metrics publisher
│   │   └── api.py           # Flask /health and /status endpoints
│   ├── tests/               # Unit tests with mocked AWS calls
│   ├── Dockerfile           # Non-root, health-checked container
│   └── main.py              # Entry point, threading model
├── CLAUDE.md                # AI-native development workflow log
└── README.md
```

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
| Alerting | SNS Email |
| CI/CD | GitHub Actions |
| State backend | S3 + DynamoDB |
| AI collaboration | Claude (Anthropic) |

---

## Key Design Decisions

**Why Fargate over EC2?**
No cluster node management required. Immutable infrastructure — each deployment replaces containers entirely rather than mutating running instances.

**Why `forceNewDeployment` for remediation?**
Delegates reconciliation to the ECS scheduler which already knows the desired state. Avoids race conditions and duplicated scheduling logic.

**Why in-memory status store?**
MVP simplicity — no external dependency required to demonstrate the /status endpoint. Documented as an iteration target in CLAUDE.md.

**Why structured JSON logging?**
Native compatibility with CloudWatch Log Insights. The dashboard includes a pre-built query filtering DRIFT_DETECTED events directly from log data.

**Why separate bootstrap Terraform?**
Chicken-and-egg problem — you cannot store Terraform state for the resource that creates your state bucket. Bootstrap runs once manually.

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
Navigate to CloudWatch → Dashboards → `ecs-drift-detector-dashboard`

### Log Insights Query

```
SOURCE '/ecs/ecs-drift-detector/detector'
| fields @timestamp, service_name, desired_count, running_count, action
| filter event_type = 'DRIFT_DETECTED'
| sort @timestamp desc
| limit 20
```

### Endpoints

| Endpoint | Purpose |
|---|---|
| GET /health | Liveness probe — returns 200 if container is running |
| GET /status | Last scan time, total scans, recent drift events |

---

## CI/CD Pipeline

### On Pull Request
terraform fmt → validate → plan → plan posted as PR comment

### On Merge to Main (infra changes)
terraform apply → ECS smoke test

### On Merge to Main (service changes)
flake8 → pytest → docker build → ECR push → ECS force deploy → smoke test

---

## Future Iterations

- Private subnets with NAT gateway for production security posture
- DynamoDB persistence for drift event history across restarts
- Slack notification channel alongside email
- Extend monitoring to CPU/memory drift from baseline
- Terraform workspaces for multi-environment support
- Drift history trending with CloudWatch Contributor Insights

---

## AI-Native Development

See [CLAUDE.md](./CLAUDE.md) for a detailed log of how Claude (Anthropic) was used as a development collaborator throughout this project — from architecture decisions to test edge cases to security posture review.
