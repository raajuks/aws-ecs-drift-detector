# infra/environments/dev/main.tf

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ecs-drift-detector-tfstate-502140064534"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ecs-drift-detector-tfstate-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"
}

module "networking" {
  source = "../../modules/networking"

  project_name        = var.project_name
  environment         = var.environment
  vpc_cidr            = "10.0.0.0/16"
  public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  availability_zones  = ["us-east-1a", "us-east-1b"]
}

module "observability" {
  source = "../../modules/observability"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = "us-east-1"
  alert_email  = var.alert_email
}

module "ecs" {
  source = "../../modules/ecs"

  project_name          = var.project_name
  environment           = var.environment
  aws_region            = "us-east-1"
  subnet_ids            = module.networking.public_subnet_ids
  security_group_id     = module.networking.ecs_security_group_id
  container_image       = var.container_image
  poll_interval_seconds = 60
  sns_topic_arn         = module.observability.sns_topic_arn
}
