# service/main.py
"""
ECS Drift Detector - Main Entry Point
Runs the polling loop and Flask API concurrently.
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone

from service.app.detector import ECSdriftDetector
from service.app.remediator import ECSRemediator
from service.app.metrics import MetricsPublisher
from service.app import api

# Structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ"
)
logger = logging.getLogger(__name__)

# Config from environment variables
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
PROJECT_NAME = os.environ.get("PROJECT_NAME", "ecs-drift-detector")


def run_detector_loop():
    """Main polling loop - runs forever, checking for drift every POLL_INTERVAL seconds."""
    detector = ECSdriftDetector(region=AWS_REGION)
    remediator = ECSRemediator(region=AWS_REGION)
    metrics = MetricsPublisher(region=AWS_REGION, environment=ENVIRONMENT)

    scan_count = 0

    logger.info(f"Starting drift detector | region={AWS_REGION} interval={POLL_INTERVAL}s")

    while True:
        scan_start = datetime.now(timezone.utc).isoformat()
        scan_count += 1

        try:
            logger.info(f"Starting scan #{scan_count}")
            drift_events = detector.scan()

            remediation_count = 0

            for event in drift_events:
                # Emit metric for each drift event
                metrics.emit_drift_detected(event)

                # Attempt remediation if needed
                if event.requires_remediation:
                    success = remediator.remediate(event)
                    if success:
                        metrics.emit_remediation_triggered(event)
                        remediation_count += 1

            # Emit scan summary
            metrics.emit_scan_summary(
                total_services=0,  # extended in future iteration
                drift_count=len(drift_events),
                remediation_count=remediation_count
            )

            # Update API status
            api.update_status(drift_events, scan_start, scan_count)

            logger.info(
                f"Scan #{scan_count} complete | "
                f"drift_events={len(drift_events)} "
                f"remediations={remediation_count}"
            )

        except Exception as e:
            logger.error(f"Scan #{scan_count} failed with error: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)


def run_api():
    """Run the Flask API on port 8080."""
    api.app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    # Run Flask API in background thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    logger.info("Flask API started on port 8080")

    # Run detector loop in main thread
    run_detector_loop()
