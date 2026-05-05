# service/app/metrics.py
"""
CloudWatch Metrics Publisher
Emits custom metrics for drift detection and remediation events.
"""

import logging
import boto3
from botocore.exceptions import ClientError
from service.app.detector import DriftEvent

logger = logging.getLogger(__name__)

NAMESPACE = "ECSdriftDetector"


class MetricsPublisher:
    def __init__(self, region: str = "us-east-1", environment: str = "dev"):
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.environment = environment

    def _put_metric(self, metric_name: str, value: float, dimensions: list):
        """Core method to publish a single metric to CloudWatch."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=NAMESPACE,
                MetricData=[{
                    "MetricName": metric_name,
                    "Dimensions": dimensions,
                    "Value": value,
                    "Unit": "Count"
                }]
            )
        except ClientError as e:
            logger.error(f"Failed to publish metric {metric_name}: {e}")

    def emit_drift_detected(self, event: DriftEvent):
        """Emit a DriftDetected metric for a single drift event."""
        dimensions = [
            {"Name": "Environment", "Value": self.environment},
            {"Name": "ClusterName", "Value": event.cluster_name},
            {"Name": "ServiceName", "Value": event.service_name}
        ]
        self._put_metric("DriftDetected", 1, dimensions)
        self._put_metric("TaskCountDelta", abs(event.delta), dimensions)
        logger.info(
            f"Metrics emitted | DriftDetected + TaskCountDelta "
            f"for {event.cluster_name}/{event.service_name}"
        )

    def emit_remediation_triggered(self, event: DriftEvent):
        """Emit a RemediationTriggered metric."""
        dimensions = [
            {"Name": "Environment", "Value": self.environment},
            {"Name": "ClusterName", "Value": event.cluster_name},
            {"Name": "ServiceName", "Value": event.service_name}
        ]
        self._put_metric("RemediationTriggered", 1, dimensions)
        logger.info(
            f"Metrics emitted | RemediationTriggered "
            f"for {event.cluster_name}/{event.service_name}"
        )

    def emit_scan_summary(self, total_services: int, drift_count: int, remediation_count: int):
        """Emit a summary metric after each full scan."""
        dimensions = [{"Name": "Environment", "Value": self.environment}]
        self._put_metric("TotalServicesScanned", total_services, dimensions)
        self._put_metric("TotalDriftEvents", drift_count, dimensions)
        self._put_metric("TotalRemediations", remediation_count, dimensions)
