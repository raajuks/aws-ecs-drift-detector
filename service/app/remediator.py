# service/app/remediator.py
"""
ECS Drift Remediator
Forces ECS service stabilization when drift is detected.
"""

import logging
import boto3
from botocore.exceptions import ClientError
from service.app.detector import DriftEvent

logger = logging.getLogger(__name__)


class ECSRemediator:
    def __init__(self, region: str = "us-east-1"):
        self.ecs_client = boto3.client("ecs", region_name=region)
        self.region = region

    def remediate(self, event: DriftEvent) -> bool:
        """
        Force ECS service stabilization by calling update_service.
        This triggers ECS scheduler to reconcile desired vs running count.
        Returns True if remediation was successfully triggered.
        """
        if not event.requires_remediation:
            logger.info(
                f"Skipping remediation for {event.service_name} "
                f"- pending tasks already in flight"
            )
            return False

        try:
            self.ecs_client.update_service(
                cluster=event.cluster_name,
                service=event.service_name,
                forceNewDeployment=True
            )
            logger.warning(
                f"REMEDIATION TRIGGERED | cluster={event.cluster_name} "
                f"service={event.service_name} "
                f"desired={event.desired_count} running={event.running_count}"
            )
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(
                f"REMEDIATION FAILED | cluster={event.cluster_name} "
                f"service={event.service_name} error={error_code} | {e}"
            )
            return False

    def remediate_all(self, events: list[DriftEvent]) -> dict:
        """Attempt remediation for all drift events. Returns summary."""
        results = {"attempted": 0, "succeeded": 0, "skipped": 0, "failed": 0}

        for event in events:
            if not event.requires_remediation:
                results["skipped"] += 1
                continue

            results["attempted"] += 1
            success = self.remediate(event)
            if success:
                results["succeeded"] += 1
            else:
                results["failed"] += 1

        return results
