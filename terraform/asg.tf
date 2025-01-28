data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-ecs-hvm-*-arm64"]
  }
}
# Launch template for ECS instances
resource "aws_launch_template" "ecs" {
  name_prefix   = "ecs-template"
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = "m8g.48xlarge"
  key_name      = aws_key_pair.benchmark.key_name

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.application.id]
  }

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  user_data = base64encode(<<-EOF
              #!/bin/bash
              echo 'ECS_CLUSTER=${aws_ecs_cluster.main.name}' >> /etc/ecs/ecs.config
              EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.common_tags, {
      Name = "benchmark-sequin-ecs-instance"
    })
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "ecs" {
  name                = "benchmark-sequin-ecs-asg"
  vpc_zone_identifier = [module.vpc.public_subnets[1]] # us-west-2b
  target_group_arns   = []                             # Add if you need load balancer integration
  health_check_type   = "EC2"
  desired_capacity    = 1
  max_size            = 2
  min_size            = 1

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = true
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = var.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_instance_role_policy,
    aws_iam_instance_profile.ecs_instance_profile
  ]
}

# Data source to get ECS instances information
data "aws_instances" "ecs_instances" {
  instance_tags = {
    "AmazonECSManaged" = "true"
  }

  depends_on = [aws_autoscaling_group.ecs]
}
