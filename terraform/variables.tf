variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "benchmark"
}

# variable "cdc_platform" {
#   type        = string
#   description = "CDC platform to deploy (debezium or sequin)"
#   validation {
#     condition     = contains(["debezium", "sequin"], var.cdc_platform)
#     error_message = "cdc_platform must be either 'debezium' or 'sequin'"
#   }
# }

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_username" {
  description = "Database administrator username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Database administrator password"
  type        = string
  default     = "postgres"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "benchmark"
    Project     = "CDC-Benchmark"
    Terraform   = "true"
    Purpose     = "CDC Performance Testing"
  }
}

variable "server_host" {
  description = "Server host address"
  type        = string
}

variable "allowed_ip" {
  description = "IP address allowed for SSH and management access (CIDR notation)"
  type        = string
}

variable "datadog_api_key" {
  description = "Datadog API key"
  type        = string
}
