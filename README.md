## Prerequisites

### SSH Key Generation

Before deploying infrastructure, you'll need to generate an SSH key pair:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/benchmark-key -C "benchmark"
```

This command will:

- Generate an ED25519 SSH key pair
- Save the private key to `~/.ssh/benchmark-key`
- Save the public key to `~/.ssh/benchmark-key.pub`
- Add "benchmark" as the key comment

### Terraform Setup

1. Install Terraform by following the [official installation guide](https://developer.hashicorp.com/terraform/install)
2. Initialize the Terraform working directory:

```bash
cd terraform
terraform init
```

3. Review the planned changes:

```bash
terraform plan
```

4. Apply the infrastructure changes:

```bash
terraform apply
```

Note: Make sure to keep your SSH private key secure and never commit it to version control.

Notes:
It's okay if you see a timeout error createing MSK clusters- they can often take 30 minutes to create.

```
aws_msk_cluster.kafka: Creation complete after 35m43s [id=arn:aws:kafka:us-west-2:689238261712:cluster/benchmark-kafka/f9dfedf0-a8be-4443-8797-ced47c1d6ae8-10]
╷
│ Error: waiting for MSK Connect Connector (arn:aws:kafkaconnect:us-west-2:689238261712:connector/benchmark-debezium-postgres/d8058951-2d49-4b0f-a87f-c4018e67e059-3) create: timeout while waiting for state to become 'RUNNING' (last state: 'CREATING', timeout: 20m0s)
│
│   with aws_mskconnect_connector.debezium,
│   on msk_connect.tf line 99, in resource "aws_mskconnect_connector" "debezium":
│   99: resource "aws_mskconnect_connector" "debezium" {
│
╵
╷
│ Error: creating Secrets Manager Secret (benchmark-db-credentials): operation error Secrets Manager: CreateSecret, https response error StatusCode: 400, RequestID: 2885bb88-281d-4130-90ec-e19b4c414c04, InvalidRequestException: You can't create this secret because a secret with this name is already scheduled for deletion.
│
│   with aws_secretsmanager_secret.db_credentials,
│   on secrets.tf line 2, in resource "aws_secretsmanager_secret" "db_credentials":
│    2: resource "aws_secretsmanager_secret" "db_credentials" {
```

Install Postgres on the load generator EC2 instance:

```
# Add PostgreSQL official repository
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# Install PostgreSQL client
sudo dnf install -y postgresql15

# If you specifically need a different version, you can install it by specifying the version:
# sudo dnf install -y postgresql14  # for PostgreSQL 14
# sudo dnf install -y postgresql16  # for PostgreSQL 16
```

And setup the load server for load generation:

```
make scp-all
make ssh-load
sudo yum install -y pip
pip install -r requirements.txt
```

And setup the stats server:

```
# ssh into the stats server
make ssh-stats

# Install wget and Java
sudo dnf install -y wget java-11-amazon-corretto

# Create a directory for Kafka
mkdir -p ~/kafka
cd ~/kafka

# Download the latest stable Kafka binary (adjust version if needed)
wget https://downloads.apache.org/kafka/3.9.0/kafka_2.12-3.9.0.tgz

# Extract the archive
tar -xzf kafka_2.12-3.9.0.tgz

# Add Kafka binaries to your PATH for easier access
echo 'export PATH=$PATH:~/kafka/kafka_2.12-3.9.0/bin' >> ~/.bashrc
source ~/.bashrc

[Follow these instructions to install AWS MSK tooling](https://docs.aws.amazon.com/msk/latest/developerguide/create-topic.html)

# Install pip and requirements
sudo yum install -y pip
pip install -r requirements.txt


```
