resource "aws_ecs_cluster" "main" {
  name = "benchmark-sequin-cluster"
  tags = var.common_tags

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

# Create the service using the selected platform
resource "aws_ecs_service" "benchmark_sequin" {
  name            = "benchmark-sequin-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.benchmark_sequin.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "EC2"
    weight            = 100
  }

  tags = var.common_tags
}

resource "aws_ecs_capacity_provider" "ec2" {
  name = "EC2"

  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.ecs.arn

    # Add managed scaling (recommended)
    managed_scaling {
      maximum_scaling_step_size = 1000
      minimum_scaling_step_size = 1
      status                    = "ENABLED"
      target_capacity           = 100
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "cluster_capacity" {
  cluster_name = aws_ecs_cluster.main.name

  # Add explicit dependency
  depends_on = [aws_ecs_capacity_provider.ec2]

  capacity_providers = [aws_ecs_capacity_provider.ec2.name] # Reference the name from the resource

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name # Reference the name from the resource
    weight            = 100
  }
}

# Create Datadog agent service as a daemon service
resource "aws_ecs_service" "datadog_agent" {
  name            = "benchmark-datadog-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.datadog_agent.arn

  # Explicitly set launch type to EC2 instead of using capacity providers
  launch_type = "EC2"

  # Use DAEMON scheduling strategy to ensure one agent per EC2 instance
  scheduling_strategy = "DAEMON"

  # No need for desired_count with DAEMON strategy

  tags = var.common_tags
}
