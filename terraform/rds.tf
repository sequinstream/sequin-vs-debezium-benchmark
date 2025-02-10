resource "aws_db_instance" "postgres_sequin" {
  identifier        = "benchmark-sequin"
  engine            = "postgres"
  engine_version    = "17.2"
  instance_class    = "db.t3.medium"
  allocated_storage = 50

  db_name  = "sequindb"
  username = var.db_username
  password = var.db_password

  iam_database_authentication_enabled = false

  vpc_security_group_ids = [aws_security_group.postgres.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name

  skip_final_snapshot = true

  parameter_group_name = aws_db_parameter_group.postgres_sequin.name

  tags = merge(var.common_tags, {
    Name = "benchmark-sequin"
  })
}

resource "aws_db_instance" "postgres_load" {
  identifier        = "benchmark-load"
  engine            = "postgres"
  engine_version    = "17.2"
  instance_class    = "db.r6g.4xlarge"
  allocated_storage = 1000

  db_name  = "loaddb"
  username = var.db_username
  password = var.db_password

  iam_database_authentication_enabled = false

  vpc_security_group_ids = [aws_security_group.postgres.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name

  skip_final_snapshot = true

  parameter_group_name = aws_db_parameter_group.postgres_load.name

  tags = merge(var.common_tags, {
    Name = "benchmark-load"
  })
}


resource "aws_db_parameter_group" "postgres_sequin" {
  family = "postgres17"
  name   = "benchmark-sequin-params"

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
    Name = "benchmark-sequin-params"
  })
}

resource "aws_db_parameter_group" "postgres_load" {
  family = "postgres17"
  name   = "benchmark-load-params"

  parameter {
    name         = "rds.logical_replication"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_wal_senders"
    value        = "20"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_replication_slots"
    value        = "20"
    apply_method = "pending-reboot"
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-load-params"
  })
}

resource "aws_db_subnet_group" "postgres" {
  name       = "benchmark-postgres-subnet-group"
  subnet_ids = module.vpc.private_subnets

  tags = merge(var.common_tags, {
    Name = "benchmark-postgres-subnet-group"
  })
}
