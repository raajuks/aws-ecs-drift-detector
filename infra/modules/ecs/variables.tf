# infra/modules/ecs/variables.tf

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS tasks"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "container_image" {
  description = "Docker image for the drift detector service"
  type        = string
}

variable "task_cpu" {
  description = "CPU units for the detector task"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Memory (MB) for the detector task"
  type        = string
  default     = "512"
}

variable "poll_interval_seconds" {
  description = "How often the detector polls ECS for drift"
  type        = number
  default     = 60
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for drift alerts"
  type        = string
}
