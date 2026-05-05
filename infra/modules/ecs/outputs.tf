# infra/modules/ecs/outputs.tf

output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "detector_service_name" {
  description = "Drift detector ECS service name"
  value       = aws_ecs_service.detector.name
}

output "sample_app_service_name" {
  description = "Sample app ECS service name"
  value       = aws_ecs_service.sample_app.name
}

output "task_execution_role_arn" {
  description = "Task execution IAM role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "log_group_name" {
  description = "CloudWatch log group for detector"
  value       = aws_cloudwatch_log_group.detector.name
}
