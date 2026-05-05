# service/app/detector.py
"""
ECS Task Drift Detector
Polls ECS clusters and compares desired vs running task counts.
"""

import logging
import boto3
from dataclasses import dataclass
from typing import List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class DriftEvent:
    cluster_name: str
    service_name: str
    desired_count: int
    running_count: int
    pending_count: int
    delta: int
    detected_at: str
    requires_remediation: bool


class ECSdriftDetector:
    def __init__(self, region: str = "us-east-1"):
        self.ecs_client = boto3.client("ecs", region_name=region)
        self.region = region

    def list_clusters(self) -> List[str]:
        """Return all ECS cluster ARNs in the account."""
        clusters = []
        paginator = self.ecs_client.get_paginator("list_clusters")
        for page in paginator.paginate():
            clusters.extend(page["clusterArns"])
        logger.info(f"Found {len(clusters)} cluster(s)")
        return clusters

    def list_services(self, cluster_arn: str) -> List[str]:
        """Return all service ARNs in a given cluster."""
        services = []
        paginator = self.ecs_client.get_paginator("list_services")
        for page in paginator.paginate(cluster=cluster_arn):
            services.extend(page["serviceArns"])
        return services

    def describe_services(self, cluster_arn: str, service_arns: List[str]) -> List[dict]:
        """Describe up to 10 services at a time (AWS API limit)."""
        results = []
        for i in range(0, len(service_arns), 10):
            batch = service_arns[i:i + 10]
            response = self.ecs_client.describe_services(
                cluster=cluster_arn,
                services=batch
            )
            results.extend(response["services"])
        return results

    def check_cluster(self, cluster_arn: str) -> List[DriftEvent]:
        """Check all services in a cluster for task count drift."""
        drift_events = []
        cluster_name = cluster_arn.split("/")[-1]

        service_arns = self.list_services(cluster_arn)
        if not service_arns:
            logger.info(f"No services found in cluster: {cluster_name}")
            return drift_events

        services = self.describe_services(cluster_arn, service_arns)

        for svc in services:
            desired = svc["desiredCount"]
            running = svc["runningCount"]
            pending = svc["pendingCount"]
            delta = desired - running
            service_name = svc["serviceName"]

            if delta != 0:
                event = DriftEvent(
                    cluster_name=cluster_name,
                    service_name=service_name,
                    desired_count=desired,
                    running_count=running,
                    pending_count=pending,
                    delta=delta,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    requires_remediation=delta > 0 and pending == 0
                )
                drift_events.append(event)
                logger.warning(
                    f"DRIFT DETECTED | cluster={cluster_name} "
                    f"service={service_name} desired={desired} "
                    f"running={running} delta={delta}"
                )
            else:
                logger.info(
                    f"OK | cluster={cluster_name} "
                    f"service={service_name} running={running}/{desired}"
                )

        return drift_events

    def scan(self) -> List[DriftEvent]:
        """Scan all clusters and return all drift events found."""
        all_drift = []
        clusters = self.list_clusters()
        for cluster_arn in clusters:
            events = self.check_cluster(cluster_arn)
            all_drift.extend(events)
        return all_drift
