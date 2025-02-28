resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "benchmark-redis"
  engine          = "redis"
  node_type       = "cache.m7g.xlarge"
  num_cache_nodes = 1
  port            = 6379

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  tags = merge(var.common_tags, {
    Name = "benchmark-redis"
  })
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "benchmark-redis-subnet-group"
  subnet_ids = module.vpc.private_subnets
}
