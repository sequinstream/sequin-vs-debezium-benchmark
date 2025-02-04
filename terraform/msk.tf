resource "aws_msk_cluster" "kafka" {
  cluster_name           = "benchmark-kafka"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.kafka.id]
    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
    connectivity_info {
      public_access {
        type = "DISABLED"
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    sasl {
      iam = true
    }

    tls {}
  }

  configuration_info {
    arn      = aws_msk_configuration.kafka.arn
    revision = aws_msk_configuration.kafka.latest_revision
  }

  tags = merge(var.common_tags, {
    Name = "benchmark-kafka"
  })
}

resource "aws_msk_configuration" "kafka" {
  kafka_versions = ["3.5.1"]
  name           = "benchmark-kafka-config"

  server_properties = <<PROPERTIES
auto.create.topics.enable=true
delete.topic.enable=true
PROPERTIES
}

output "bootstrap_servers" {
  description = "MSK Bootstrap servers for TLS connectivity"
  value       = aws_msk_cluster.kafka.bootstrap_brokers_sasl_iam
}
