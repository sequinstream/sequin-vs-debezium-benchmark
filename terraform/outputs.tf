output "postgres_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "pg_hostname" {
  value = aws_db_instance.postgres.address
}

output "pg_database" {
  value = aws_db_instance.postgres.db_name
}

output "pg_port" {
  value = aws_db_instance.postgres.port
}

output "pg_username" {
  value = aws_db_instance.postgres.username
}

output "pg_password" {
  value     = aws_db_instance.postgres.password
  sensitive = true
}

output "kafka_bootstrap_brokers_tls" {
  description = "TLS connection host:port pairs for Kafka brokers"
  value       = aws_msk_cluster.kafka.bootstrap_brokers_tls
}

output "kafka_zookeeper_connect_string" {
  description = "Zookeeper connection string"
  value       = aws_msk_cluster.kafka.zookeeper_connect_string
}

output "load_generator_dns" {
  description = "Public DNS name of the load generator instance"
  value       = aws_instance.load_generator.public_dns
}

output "stats_server_dns" {
  description = "Public DNS name of the stats server instance"
  value       = aws_instance.stats_server.public_dns
}

output "ecs_instance_dns" {
  description = "Public DNS names of the ECS instances in the ASG"
  value       = data.aws_instances.ecs_instances.public_ips
}

output "application_access_key_id" {
  description = "Access Key ID for application MSK access"
  value       = aws_iam_access_key.application_user.id
  sensitive   = true
}

output "application_secret_access_key" {
  description = "Secret Access Key for application MSK access"
  value       = aws_iam_access_key.application_user.secret
  sensitive   = true
}
