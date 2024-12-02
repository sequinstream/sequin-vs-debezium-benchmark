locals {
  debezium_connector_config = {
    connectorConfiguration = {
      "connector.class"      = "io.debezium.connector.postgresql.PostgresConnector"
      "tasks.max"            = "1"
      "database.hostname"    = aws_db_instance.postgres.address
      "database.port"        = tostring(aws_db_instance.postgres.port)
      "database.user"        = "postgres"
      "database.password"    = "postgres"
      "database.dbname"      = aws_db_instance.postgres.db_name
      "database.server.name" = "benchmark-postgres"
      "schema.include.list"  = "public" # Adjust based on your needs
      "plugin.name"          = "pgoutput"
      "topic.prefix"         = "debezium.benchmark.postgres"

      # Add the new configurations here
      "signal.data.collection"                    = "public.debezium_signal"
      "topic.creation.enable"                     = "true"
      "topic.creation.default.replication.factor" = "3"
      "topic.creation.default.partitions"         = "1"

      # Schema history configuration
      "schema.history.internal.kafka.topic"             = "schema-changes.benchmark"
      "schema.history.internal.kafka.bootstrap.servers" = aws_msk_cluster.kafka.bootstrap_brokers_tls

      # Security settings for schema history
      "schema.history.internal.consumer.security.protocol"                  = "SASL_SSL"
      "schema.history.internal.consumer.sasl.mechanism"                     = "AWS_MSK_IAM"
      "schema.history.internal.consumer.sasl.jaas.config"                   = "software.amazon.msk.auth.iam.IAMLoginModule required;"
      "schema.history.internal.consumer.sasl.client.callback.handler.class" = "software.amazon.msk.auth.iam.IAMClientCallbackHandler"

      "schema.history.internal.producer.security.protocol"                  = "SASL_SSL"
      "schema.history.internal.producer.sasl.mechanism"                     = "AWS_MSK_IAM"
      "schema.history.internal.producer.sasl.jaas.config"                   = "software.amazon.msk.auth.iam.IAMLoginModule required;"
      "schema.history.internal.producer.sasl.client.callback.handler.class" = "software.amazon.msk.auth.iam.IAMClientCallbackHandler"

      "include.schema.changes" = "true"
    }

    connectorName = "benchmark-debezium-postgres-connector"

    kafkaCluster = {
      apacheKafkaCluster = {
        bootstrapServers = aws_msk_cluster.kafka.bootstrap_brokers_tls
        vpc = {
          subnets        = module.vpc.private_subnets
          securityGroups = [aws_security_group.kafka.id, aws_security_group.msk_connect.id]
        }
      }
    }

    capacity = {
      provisionedCapacity = {
        mcuCount    = 8
        workerCount = 1
      }
    }

    kafkaConnectVersion     = "2.7.1"
    serviceExecutionRoleArn = aws_iam_role.msk_connect_role.arn

    plugins = [{
      customPlugin = {
        customPluginArn = "arn:aws:kafkaconnect:us-west-2:689238261712:custom-plugin/benchmark-debezium-postgresql-connector/20e5cfd3-44c7-40b8-bc05-c19078e0755c-3"
        revision        = 1
      }
    }]

    kafkaClusterEncryptionInTransit = {
      encryptionType = "TLS"
    }

    kafkaClusterClientAuthentication = {
      authenticationType = "IAM"
    }
  }
}

# Create the CloudWatch Log Group first
resource "aws_cloudwatch_log_group" "msk_connect_logs" {
  name              = "/aws/kafkaconnect/benchmark-debezium-postgres"
  retention_in_days = 14 # Adjust retention as needed
}

# Create the MSK Connect Custom Plugin
resource "aws_mskconnect_custom_plugin" "debezium" {
  name         = "benchmark-debezium-postgresql-connector"
  content_type = "ZIP"

  location {
    s3 {
      bucket_arn = "arn:aws:s3:::benchmark-debezium-postgresql-connector"
      file_key   = "connector.zip"
    }
  }
}

# Create MSK Connect connector
resource "aws_mskconnect_connector" "debezium" {
  name = "benchmark-debezium-postgres"

  kafkaconnect_version = local.debezium_connector_config.kafkaConnectVersion

  capacity {
    provisioned_capacity {
      mcu_count    = local.debezium_connector_config.capacity.provisionedCapacity.mcuCount
      worker_count = local.debezium_connector_config.capacity.provisionedCapacity.workerCount
    }
  }

  connector_configuration = local.debezium_connector_config.connectorConfiguration

  kafka_cluster {
    apache_kafka_cluster {
      bootstrap_servers = aws_msk_cluster.kafka.bootstrap_brokers_sasl_iam
      vpc {
        security_groups = [aws_security_group.kafka.id, aws_security_group.msk_connect.id]
        subnets         = module.vpc.private_subnets
      }
    }
  }

  kafka_cluster_client_authentication {
    authentication_type = local.debezium_connector_config.kafkaClusterClientAuthentication.authenticationType
  }

  kafka_cluster_encryption_in_transit {
    encryption_type = local.debezium_connector_config.kafkaClusterEncryptionInTransit.encryptionType
  }

  plugin {
    custom_plugin {
      arn      = aws_mskconnect_custom_plugin.debezium.arn
      revision = aws_mskconnect_custom_plugin.debezium.latest_revision
    }
  }

  service_execution_role_arn = local.debezium_connector_config.serviceExecutionRoleArn

  log_delivery {
    worker_log_delivery {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_connect_logs.name
      }
    }
  }

  # Add explicit dependency on the log group
  depends_on = [
    aws_cloudwatch_log_group.msk_connect_logs,
    aws_mskconnect_custom_plugin.debezium
  ]
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Create IAM role for MSK Connect
resource "aws_iam_role" "msk_connect_role" {
  name = "msk-connect-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "kafkaconnect.amazonaws.com"
        }
      }
    ]
  })
}

# Add necessary permissions for MSK Connect role
resource "aws_iam_role_policy" "msk_connect_policy" {
  name = "msk-connect-policy"
  role = aws_iam_role.msk_connect_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "kafka-cluster:*"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          "arn:aws:logs:us-west-2:${data.aws_caller_identity.current.account_id}:log-group:/aws/kafkaconnect/*",
          "arn:aws:logs:us-west-2:${data.aws_caller_identity.current.account_id}:log-group:/aws/kafkaconnect/benchmark-debezium-postgres:*"
        ]
      }
    ]
  })
}
