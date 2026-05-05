# service/tests/test_api.py
"""
Unit tests for Flask API endpoints
"""

import pytest
from service.app.api import app, update_status
from service.app.detector import DriftEvent
from datetime import datetime, timezone


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_drift_event():
    return DriftEvent(
        cluster_name="test-cluster",
        service_name="test-svc",
        desired_count=2,
        running_count=1,
        pending_count=0,
        delta=1,
        detected_at=datetime.now(timezone.utc).isoformat(),
        requires_remediation=True
    )


def test_health_returns_200(client):
    """GET /health should return 200 with healthy status."""
    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_status_returns_200(client):
    """GET /status should return 200 with running status."""
    response = client.get("/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "running"


def test_status_reflects_drift_events(client):
    """GET /status should include recent drift events after update_status is called."""
    event = make_drift_event()
    update_status([event], datetime.now(timezone.utc).isoformat(), 1)

    response = client.get("/status")
    data = response.get_json()

    assert data["total_scans"] == 1
    assert len(data["recent_drift_events"]) >= 1
    assert data["recent_drift_events"][0]["service_name"] == "test-svc"
    assert data["recent_drift_events"][0]["delta"] == 1
