# Common container definitions for Postgres (used by both platforms)
locals {
  sequin_containers = [
    {
      name  = "sequin"
      image = "sequin/sequin:latest"
      portMappings = [
        {
          containerPort = 7376
          hostPort      = 7376
          protocol      = "tcp"
        }
      ]
      secrets = [
        {
          name      = "PG_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::"
        },
        {
          name      = "PG_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::"
        }
      ]
      environment = [
        {
          name  = "SERVER_HOST",
          value = var.server_host
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.cache_nodes[0].port}"
        },
        {
          name  = "PG_HOSTNAME"
          value = aws_db_instance.postgres_sequin.address
        },
        {
          name  = "PG_DATABASE"
          value = aws_db_instance.postgres_sequin.db_name
        },
        {
          name  = "PG_PORT"
          value = tostring(aws_db_instance.postgres_sequin.port)
        },
        {
          name  = "PG_SSL"
          value = "verify-none"
        },
        {
          name  = "PG_POOL_SIZE"
          value = "20"
        },
        {
          name  = "SECRET_KEY_BASE"
          value = "wDPLYus0pvD6qJhKJICO4dauYPXfO/Yl782Zjtpew5qRBDp7CZvbWtQmY0eB13If"
        },
        {
          name  = "VAULT_KEY"
          value = "2Sig69bIpuSm2kv0VQfDekET2qy8qUZGI8v3/h3ASiY="
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/benchmark-sequin"
          "awslogs-region"        = "us-west-2"
          "awslogs-stream-prefix" = "sequin"
        }
      }
    }
  ]
}

# Create CloudWatch log group for Sequin
resource "aws_cloudwatch_log_group" "sequin" {
  name              = "/ecs/benchmark-sequin"
  retention_in_days = 7
  tags              = var.common_tags
}

resource "aws_ecs_task_definition" "benchmark_sequin" {
  family                = "benchmark-sequin"
  container_definitions = jsonencode(local.sequin_containers)
  network_mode          = "host"

  requires_compatibilities = ["EC2"]
  memory                   = 122880

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  tags = var.common_tags
}
