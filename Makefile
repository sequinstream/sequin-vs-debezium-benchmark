# SSH options to disable strict host checking
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
SSH_KEY := ~/.ssh/benchmark-key

# SSH to load generator
ssh-load:
	@echo "Connecting to load generator..."
	@cd terraform && ssh -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -raw load_generator_dns)

# SSH to stats server
ssh-stats:
	@echo "Connecting to stats server..."
	@cd terraform && ssh -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -raw stats_server_dns)

# SSH to ECS instances
ssh-ecs:
	@echo "Connecting to ECS instance..."
	@cd terraform && ssh -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -json ecs_instance_dns | jq -r '.[0]')

scp-stats:
	@echo "Copying consumer stats to stats server..."
	@cd terraform && scp -i $(SSH_KEY) ../cdc_stats.py ../backfill_stats.py ../requirements.txt ec2-user@$$(terraform output -no-color -raw stats_server_dns):~/

scp-load:
	@echo "Copying workload generator to load generator instance..."
	@cd terraform && scp -i $(SSH_KEY) ../workload_generator.py ../data_loader.py ../requirements.txt ec2-user@$$(terraform output -no-color -raw load_generator_dns):~/

# Combined target to copy both files
scp-all: scp-stats scp-load

# Print formatted Terraform output
tf-output:
	@echo "Terraform outputs:"
	@cd terraform && terraform output -no-color -json | jq '.'

# Setup stats server with Kafka
setup-stats:
	@echo "Installing Kafka on stats server..."
	@cd terraform && ssh -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -raw stats_server_dns) '\
		sudo yum install -y wget python3-pip && \
		wget https://downloads.apache.org/kafka/3.9.0/kafka_2.13-3.9.0.tgz && \
		tar -xzf kafka_2.13-3.9.0.tgz && \
		echo "security.protocol=SSL" > kafka_2.13-3.9.0/bin/client.properties && \
		sudo yum install -y java-17-amazon-corretto && \
		pip3 install -r requirements.txt'
	@$(MAKE) scp-stats
	@echo "\nSetup complete! To start the consumer, run:"
	@$(MAKE) print-consumer-command

# Print Kafka bootstrap servers
kafka-url:
	@echo "Kafka Bootstrap Servers:"
	@cd terraform && terraform output -no-color -raw kafka_bootstrap_brokers_tls

# Print command to run consumer stats
print-consumer-command:
	@echo "Run this command on the stats server:"
	@echo "python3 cdc_stats.py --bootstrap-servers $$(cd terraform && terraform output -no-color -raw kafka_bootstrap_brokers_tls) --topic=benchmark_records"

# Copy remote IEx script to ECS instance
setup-remiex:
	@echo "Copying remote IEx script to ECS instance..."
	@cd terraform && scp -i $(SSH_KEY) ../remote_iex.sh ec2-user@$$(terraform output -no-color -json ecs_instance_dns | jq -r '.[0]'):~/ && \
	ssh -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -json ecs_instance_dns | jq -r '.[0]') "chmod +x ~/remote_iex.sh"

# Remote IEx connection to the application
remiex:
	@echo "Connecting to remote IEx..."
	@cd terraform && ssh -t $(SSH_OPTS) -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -json ecs_instance_dns | jq -r '.[0]') "./remote_iex.sh"

# Download kafka_stats.csv from stats server with timestamp
download-stats:
	@echo "Downloading kafka_stats.csv from stats server..."
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	cd terraform && scp -i $(SSH_KEY) \
		ec2-user@$$(terraform output -no-color -raw stats_server_dns):~/kafka_stats.csv \
		../kafka_stats_$$timestamp.csv && \
	echo "File downloaded as kafka_stats_$$timestamp.csv"

# Connect to Sequin container shell on ECS instance
shell:
	@echo "Connecting to Sequin container shell..."
	@cd terraform && ssh -t $(SSH_OPTS) -i $(SSH_KEY) ec2-user@$$(terraform output -no-color -json ecs_instance_dns | jq -r '.[0]') \
		"docker exec -it \$$(docker ps --filter name=sequin --format '{{.ID}}') /bin/bash"