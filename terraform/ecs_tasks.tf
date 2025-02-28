# Common container definitions for Postgres (used by both platforms)
locals {
  sequin_containers = [
    {
      name  = "sequin"
      image = "sequin/sequin:v0.6.64-alpha.03"
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
        },
        {
          name  = "MAX_MEMORY_MB"
          value = "57344"
        },
        # Datadog APM configuration
        {
          name  = "DD_AGENT_HOST"
          value = "localhost"
        },
        {
          name  = "DD_TRACE_AGENT_PORT"
          value = "8126"
        },
        {
          name  = "DD_PROFILING_ENABLED"
          value = "true"
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
  memory                   = 57344

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  tags = var.common_tags
}

# Create CloudWatch log group for Datadog
resource "aws_cloudwatch_log_group" "datadog" {
  name              = "/ecs/benchmark-datadog"
  retention_in_days = 7
  tags              = var.common_tags
}

# Datadog agent task definition
resource "aws_ecs_task_definition" "datadog_agent" {
  family                   = "benchmark-datadog-agent"
  requires_compatibilities = ["EC2"]
  network_mode             = "host"

  container_definitions = jsonencode([
    {
      cpu       = 10
      image     = "datadog/agent:latest"
      memory    = 2560
      name      = "datadog-agent"
      essential = true
      hostname  = "datadog-agent.local"

      environment = [
        {
          name  = "DD_APM_NON_LOCAL_TRAFFIC"
          value = "true"
        },
        {
          name  = "DD_CONTAINER_EXCLUDE_LOGS"
          value = "name:datadog-agent"
        },
        {
          name  = "DD_DOGSTATSD_NON_LOCAL_TRAFFIC"
          value = "true"
        },
        {
          name  = "DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL"
          value = "true"
        },
        {
          name  = "DD_LOGS_ENABLED"
          value = "true"
        },
        {
          name  = "DD_OTLP_CONFIG_RECEIVER_PROTOCOLS_HTTP_ENDPOINT"
          value = "0.0.0.0:4318"
        },
        {
          name  = "DD_SITE"
          value = "datadoghq.com"
        },
        {
          name  = "DD_API_KEY"
          value = var.datadog_api_key
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "agent health"]
        interval    = 30
        retries     = 3
        startPeriod = 15
        timeout     = 5
      }

      mountPoints = [
        {
          containerPath = "/var/run/docker.sock"
          readOnly      = true
          sourceVolume  = "docker_sock"
        },
        {
          containerPath = "/host/sys/fs/cgroup"
          readOnly      = true
          sourceVolume  = "cgroup"
        },
        {
          containerPath = "/host/proc"
          readOnly      = true
          sourceVolume  = "proc"
        }
      ]

      portMappings = [
        {
          containerPort = 8125
          hostPort      = 8125
          protocol      = "udp"
        },
        {
          containerPort = 4318
          hostPort      = 4318
          protocol      = "tcp"
        },
        {
          containerPort = 8126
          hostPort      = 8126
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/benchmark-datadog"
          "awslogs-region"        = "us-west-2"
          "awslogs-stream-prefix" = "datadog"
        }
      }
    }
  ])

  volume {
    name      = "proc"
    host_path = "/proc/"
  }

  volume {
    name      = "cgroup"
    host_path = "/sys/fs/cgroup/"
  }

  volume {
    name      = "docker_sock"
    host_path = "/var/run/docker.sock"
  }

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  tags = var.common_tags
}
