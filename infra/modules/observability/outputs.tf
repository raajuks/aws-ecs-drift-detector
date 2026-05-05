# infra/modules/observability/outputs.tf

output "sns_topic_arn" {
  description = "SNS topic ARN for drift alerts"
  value       = aws_sns_topic.drift_alerts.arn
}

output "dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "drift_alarm_name" {
  description = "CloudWatch alarm name for drift detection"
  value       = aws_cloudwatch_metric_alarm.drift_detected.alarm_name
}
