terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "sequin-benchmark-terraform-state"
    key     = "terraform.tfstate"
    region  = "us-west-2"
    profile = "dev"
    # If you want to use DynamoDB for state locking (recommended)
    # dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "dev"
}

resource "aws_key_pair" "benchmark" {
  key_name   = "benchmark-key"
  public_key = file("~/.ssh/benchmark-key.pub")
}
