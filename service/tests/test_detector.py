# service/tests/test_detector.py
"""
Unit tests for ECS Drift Detector
"""

import pytest
from unittest.mock import MagicMock, patch
from service.app.detector import ECSdriftDetector, DriftEvent


@pytest.fixture
def mock_ecs_client():
    with patch("boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def detector(mock_ecs_client):
    return ECSdriftDetector(region="us-east-1")


def test_list_clusters_returns_arns(detector, mock_ecs_client):
    """list_clusters should return all cluster ARNs via paginator."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"clusterArns": ["arn:aws:ecs:us-east-1:123:cluster/test-cluster"]}
    ]
    mock_ecs_client.get_paginator.return_value = mock_paginator

    clusters = detector.list_clusters()

    assert len(clusters) == 1
    assert "test-cluster" in clusters[0]


def test_list_clusters_empty(detector, mock_ecs_client):
    """list_clusters should return empty list when no clusters exist."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"clusterArns": []}]
    mock_ecs_client.get_paginator.return_value = mock_paginator

    clusters = detector.list_clusters()

    assert clusters == []


def test_no_drift_when_counts_match(detector, mock_ecs_client):
    """check_cluster should return no drift events when desired == running."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"serviceArns": ["arn:aws:ecs:us-east-1:123:service/test-cluster/my-svc"]}
    ]
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_ecs_client.describe_services.return_value = {
        "services": [{
            "serviceName": "my-svc",
            "desiredCount": 2,
            "runningCount": 2,
            "pendingCount": 0
        }]
    }

    events = detector.check_cluster("arn:aws:ecs:us-east-1:123:cluster/test-cluster")

    assert events == []


def test_drift_detected_when_running_less_than_desired(detector, mock_ecs_client):
    """check_cluster should detect drift when running < desired."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"serviceArns": ["arn:aws:ecs:us-east-1:123:service/test-cluster/my-svc"]}
    ]
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_ecs_client.describe_services.return_value = {
        "services": [{
            "serviceName": "my-svc",
            "desiredCount": 3,
            "runningCount": 1,
            "pendingCount": 0
        }]
    }

    events = detector.check_cluster("arn:aws:ecs:us-east-1:123:cluster/test-cluster")

    assert len(events) == 1
    assert events[0].delta == 2
    assert events[0].requires_remediation is True
    assert events[0].service_name == "my-svc"


def test_drift_requires_no_remediation_when_pending(detector, mock_ecs_client):
    """Drift with pending tasks should not require remediation - ECS is already recovering."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"serviceArns": ["arn:aws:ecs:us-east-1:123:service/test-cluster/my-svc"]}
    ]
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_ecs_client.describe_services.return_value = {
        "services": [{
            "serviceName": "my-svc",
            "desiredCount": 2,
            "runningCount": 1,
            "pendingCount": 1
        }]
    }

    events = detector.check_cluster("arn:aws:ecs:us-east-1:123:cluster/test-cluster")

    assert len(events) == 1
    assert events[0].requires_remediation is False


def test_scan_aggregates_all_clusters(detector, mock_ecs_client):
    """scan() should check all clusters and aggregate drift events."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.side_effect = [
        # list_clusters call
        [{"clusterArns": [
            "arn:aws:ecs:us-east-1:123:cluster/cluster-a",
            "arn:aws:ecs:us-east-1:123:cluster/cluster-b"
        ]}],
        # list_services for cluster-a
        [{"serviceArns": ["arn:aws:ecs:us-east-1:123:service/cluster-a/svc-a"]}],
        # list_services for cluster-b
        [{"serviceArns": []}]
    ]
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_ecs_client.describe_services.return_value = {
        "services": [{
            "serviceName": "svc-a",
            "desiredCount": 2,
            "runningCount": 0,
            "pendingCount": 0
        }]
    }

    events = detector.scan()

    assert len(events) == 1
    assert events[0].cluster_name == "cluster-a"
