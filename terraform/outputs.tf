output "pg_sequin_endpoint" {
  value = aws_db_instance.postgres_sequin.endpoint
}

output "pg_load_endpoint" {
  value = aws_db_instance.postgres_load.endpoint
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

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}
