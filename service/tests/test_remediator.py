# service/tests/test_remediator.py
"""
Unit tests for ECS Drift Remediator
"""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from service.app.remediator import ECSRemediator
from service.app.detector import DriftEvent
from datetime import datetime, timezone


def make_drift_event(requires_remediation=True, pending=0):
    return DriftEvent(
        cluster_name="test-cluster",
        service_name="test-svc",
        desired_count=2,
        running_count=1,
        pending_count=pending,
        delta=1,
        detected_at=datetime.now(timezone.utc).isoformat(),
        requires_remediation=requires_remediation
    )


@pytest.fixture
def mock_ecs_client():
    with patch("boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def remediator(mock_ecs_client):
    return ECSRemediator(region="us-east-1")


def test_remediate_calls_update_service(remediator, mock_ecs_client):
    """remediate() should call update_service when remediation is required."""
    event = make_drift_event(requires_remediation=True)
    mock_ecs_client.update_service.return_value = {}

    result = remediator.remediate(event)

    assert result is True
    mock_ecs_client.update_service.assert_called_once_with(
        cluster="test-cluster",
        service="test-svc",
        forceNewDeployment=True
    )


def test_remediate_skips_when_not_required(remediator, mock_ecs_client):
    """remediate() should skip and return False when remediation is not required."""
    event = make_drift_event(requires_remediation=False)

    result = remediator.remediate(event)

    assert result is False
    mock_ecs_client.update_service.assert_not_called()


def test_remediate_handles_client_error(remediator, mock_ecs_client):
    """remediate() should return False and log error on AWS ClientError."""
    event = make_drift_event(requires_remediation=True)
    mock_ecs_client.update_service.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
        "UpdateService"
    )

    result = remediator.remediate(event)

    assert result is False


def test_remediate_all_summary(remediator, mock_ecs_client):
    """remediate_all() should return correct counts for attempted, succeeded, skipped."""
    events = [
        make_drift_event(requires_remediation=True),
        make_drift_event(requires_remediation=True),
        make_drift_event(requires_remediation=False)
    ]
    mock_ecs_client.update_service.return_value = {}

    results = remediator.remediate_all(events)

    assert results["attempted"] == 2
    assert results["succeeded"] == 2
    assert results["skipped"] == 1
    assert results["failed"] == 0
