# Create the secret in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "benchmark-db-creds-${random_id.suffix.hex}"
  recovery_window_in_days = 0 # Immediate deletion
  tags                    = var.common_tags
}

# Generate random suffix
resource "random_id" "suffix" {
  byte_length = 4

  # # This will generate a new random ID whenever terraform apply is run
  # keepers = {
  #   # Simply update this timestamp for a new random value
  #   timestamp = timestamp()
  # }
}

# Store the secret values
resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}
