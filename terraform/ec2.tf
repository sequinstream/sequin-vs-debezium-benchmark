data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "load_generator" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = "t3.medium"
  key_name      = aws_key_pair.benchmark.key_name

  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.load_generator.id]
  associate_public_ip_address = true

  lifecycle {
    ignore_changes = [ami]
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-load-generator"
  })
}

resource "aws_instance" "stats_server" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = "t3.medium"
  key_name      = aws_key_pair.benchmark.key_name

  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.stats_server.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 20 # GB
    volume_type = "gp3"
    encrypted   = true
  }

  lifecycle {
    ignore_changes = [ami]
  }

  iam_instance_profile = aws_iam_instance_profile.stats_server.name

  tags = merge(var.common_tags, {
    Name = "benchmark-stats-server"
  })
}
