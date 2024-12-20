variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  sensitive   = true
}

variable "schedule_expression" {
  description = "CloudWatch Events schedule expression"
  type        = string
  default     = "rate(5 minutes)"
}

variable "services_config" {
  description = "Configuration for services to monitor"
  type = list(object({
    name            = string
    url             = string
    type            = string
    timeout         = optional(number)
    expected_status = optional(number)
    custom_headers  = optional(map(string))
  }))
}
