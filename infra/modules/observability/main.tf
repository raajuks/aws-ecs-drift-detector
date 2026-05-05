# infra/modules/observability/main.tf

# SNS topic for drift alerts
resource "aws_sns_topic" "drift_alerts" {
  name = "${var.project_name}-drift-alerts"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.drift_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch alarm - drift detected
resource "aws_cloudwatch_metric_alarm" "drift_detected" {
  alarm_name          = "${var.project_name}-drift-detected"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DriftDetected"
  namespace           = "ECSdriftDetector"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "ECS task count drift detected between desired and running"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.drift_alerts.arn]
  ok_actions          = [aws_sns_topic.drift_alerts.arn]

  dimensions = {
    Environment = var.environment
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# CloudWatch alarm - remediation triggered
resource "aws_cloudwatch_metric_alarm" "remediation_triggered" {
  alarm_name          = "${var.project_name}-remediation-triggered"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RemediationTriggered"
  namespace           = "ECSdriftDetector"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "ECS drift auto-remediation was triggered"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.drift_alerts.arn]

  dimensions = {
    Environment = var.environment
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# CloudWatch dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Drift Events Detected"
          view    = "timeSeries"
          stacked = false
          metrics = [[
            "ECSdriftDetector", "DriftDetected",
            "Environment", var.environment
          ]]
          period = 60
          region = var.aws_region
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Remediations Triggered"
          view    = "timeSeries"
          stacked = false
          metrics = [[
            "ECSdriftDetector", "RemediationTriggered",
            "Environment", var.environment
          ]]
          period = 60
          region = var.aws_region
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Task Count Delta (Desired vs Running)"
          view    = "timeSeries"
          stacked = false
          metrics = [[
            "ECSdriftDetector", "TaskCountDelta",
            "Environment", var.environment
          ]]
          period = 60
          region = var.aws_region
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Recent Drift Events (Log Insights)"
          view    = "table"
          region  = var.aws_region
          query   = "SOURCE '/ecs/${var.project_name}/detector' | fields @timestamp, service_name, desired_count, running_count, action | filter event_type = 'DRIFT_DETECTED' | sort @timestamp desc | limit 20"
        }
      }
    ]
  })
}
