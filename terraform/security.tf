# Security group for PostgreSQL RDS
resource "aws_security_group" "postgres" {
  name_prefix = "benchmark-postgres-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id, aws_security_group.load_generator.id, aws_security_group.msk_connect.id]
    cidr_blocks     = ["172.220.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-postgres-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security group for MSK (Kafka)
resource "aws_security_group" "kafka" {
  name_prefix = "benchmark-kafka-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
    cidr_blocks     = ["172.220.0.0/16"]
  }

  ingress {
    from_port = 9094
    to_port   = 9094
    protocol  = "tcp"
    security_groups = [
      aws_security_group.application.id,
      aws_security_group.stats_server.id,
      aws_security_group.msk_connect.id
    ]
    cidr_blocks = ["172.220.0.0/16"]
  }

  ingress {
    from_port = 9098
    to_port   = 9098
    protocol  = "tcp"
    security_groups = [
      aws_security_group.msk_connect.id,
      aws_security_group.stats_server.id,
      aws_security_group.application.id
    ]
    cidr_blocks = ["172.220.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-kafka-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security group for application host (Debezium/Sequin)
resource "aws_security_group" "application" {
  name_prefix = "benchmark-application-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  ingress {
    from_port   = 7376
    to_port     = 7376
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  ingress {
    from_port       = 8083
    to_port         = 8083
    protocol        = "tcp"
    security_groups = [aws_security_group.load_generator.id]
  }

  ingress {
    from_port       = 7376
    to_port         = 7376
    protocol        = "tcp"
    security_groups = [aws_security_group.load_generator.id]
  }

  # Datadog APM port
  ingress {
    from_port   = 8126
    to_port     = 8126
    protocol    = "tcp"
    self        = true
    description = "Datadog APM TCP"
  }

  # Datadog StatsD port
  ingress {
    from_port   = 8125
    to_port     = 8125
    protocol    = "udp"
    self        = true
    description = "Datadog StatsD UDP"
  }

  # Datadog OTLP port
  ingress {
    from_port   = 4318
    to_port     = 4318
    protocol    = "tcp"
    self        = true
    description = "Datadog OTLP TCP"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  ingress {
    from_port   = 51678
    to_port     = 51678
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-application-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security group for load generator
resource "aws_security_group" "load_generator" {
  name_prefix = "benchmark-load-generator-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-load-generator-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "stats_server" {
  name_prefix = "benchmark-stats-server-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  ingress {
    from_port   = 7376
    to_port     = 7376
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-stats-server-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "benchmark-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Add new security group for MSK Connect
resource "aws_security_group" "msk_connect" {
  name_prefix = "benchmark-msk-connect-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-msk-connect-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}
