# infra/environments/dev/variables.tf

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "ecs-drift-detector"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "alert_email" {
  description = "Email for drift alerts"
  type        = string
}

variable "container_image" {
  description = "Docker image URI for the drift detector"
  type        = string
}
