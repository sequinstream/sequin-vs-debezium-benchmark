resource "aws_db_instance" "postgres" {
  identifier        = "benchmark-postgres"
  engine            = "postgres"
  engine_version    = "17.2"
  instance_class    = "db.t3.2xlarge"
  allocated_storage = 200

  db_name  = "testdb"
  username = var.db_username
  password = var.db_password

  iam_database_authentication_enabled = false

  vpc_security_group_ids = [aws_security_group.postgres.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name

  skip_final_snapshot = true

  parameter_group_name = aws_db_parameter_group.postgres.name

  tags = merge(var.common_tags, {
    Name = "benchmark-postgres"
  })
}

resource "aws_db_parameter_group" "postgres" {
  family = "postgres17"
  name   = "benchmark-postgres-params"

  parameter {
    name         = "rds.logical_replication"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_wal_senders"
    value        = "5"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_replication_slots"
    value        = "5"
    apply_method = "pending-reboot"
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-postgres-params"
  })
}

resource "aws_db_subnet_group" "postgres" {
  name       = "benchmark-postgres-subnet-group"
  subnet_ids = module.vpc.private_subnets

  tags = merge(var.common_tags, {
    Name = "benchmark-postgres-subnet-group"
  })
}
