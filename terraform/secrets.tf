# Create the secret in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "benchmark-db-creds"
  tags = var.common_tags
}

# Store the secret values
resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}
