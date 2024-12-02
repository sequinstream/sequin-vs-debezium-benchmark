terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
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
