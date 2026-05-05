# service/app/api.py
"""
Flask API
Exposes /health and /status endpoints for the drift detector service.
"""

import logging
from flask import Flask, jsonify
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

app = Flask(__name__)

# In-memory store of recent drift events (last 50)
_recent_events = []
_last_scan_at = None
_scan_count = 0


def update_status(drift_events: list, scan_time: str, scan_count: int):
    """Called by the main loop after each scan to update status state."""
    global _recent_events, _last_scan_at, _scan_count
    _last_scan_at = scan_time
    _scan_count = scan_count
    _recent_events = (drift_events + _recent_events)[:50]


@app.route("/health")
def health():
    """Liveness probe endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/status")
def status():
    """Returns current detector status and recent drift events."""
    return jsonify({
        "status": "running",
        "last_scan_at": _last_scan_at,
        "total_scans": _scan_count,
        "recent_drift_events": [
            {
                "cluster_name": e.cluster_name,
                "service_name": e.service_name,
                "desired_count": e.desired_count,
                "running_count": e.running_count,
                "delta": e.delta,
                "detected_at": e.detected_at,
                "required_remediation": e.requires_remediation
            }
            for e in _recent_events
        ]
    }), 200
