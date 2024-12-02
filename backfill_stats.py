from confluent_kafka import Consumer, KafkaError
import time
import argparse
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

class KafkaBackfillCollector:
    def __init__(self, bootstrap_servers, topic, use_iam=False):
        # Common consumer configs - shared with cdc_stats.py
        consumer_config = {
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'backfill_stats_group',
            'auto.offset.reset': 'end',
            'client.id': 'backfill_stats'
        }

        # Configure authentication based on use_iam flag - shared with cdc_stats.py
        if use_iam:
            print("Using IAM authentication")

            def oauth_cb(config):
                auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token("us-west-2")
                return auth_token, expiry_ms/1000

            consumer_config.update({
                'security.protocol': 'SASL_SSL',
                'sasl.mechanisms': 'OAUTHBEARER',
                'oauth_cb': oauth_cb,
                'ssl.ca.location': '/etc/ssl/certs/ca-bundle.crt'
            })
        else:
            consumer_config.update({
                'security.protocol': 'PLAINTEXT',
            })

        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe([topic])
        self.topic = topic

    def run(self, backfill_count):
        try:
            message_count = 0
            start_time = None
            end_time = None

            print(f"Starting to collect backfill statistics for {backfill_count} messages...")

            while message_count < backfill_count:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Consumer error: {msg.error()}")
                        break

                # Record timing for first message
                if start_time is None:
                    start_time = time.time()

                message_count += 1
                
                # Print progress every 1000 messages
                if message_count % 1000 == 0:
                    print(f"Processed {message_count} messages...")

                # Record timing for last message
                end_time = time.time()

            # Calculate and print statistics
            if start_time and end_time:
                total_time = end_time - start_time
                messages_per_second = message_count / total_time
                
                print("\nBackfill Statistics:")
                print(f"Total messages processed: {message_count}")
                print(f"Total time elapsed: {total_time:.2f} seconds")
                print(f"Average throughput: {messages_per_second:.2f} messages/second")

        except KeyboardInterrupt:
            print("\nStopping backfill collection...")
        finally:
            self.consumer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Collect Kafka backfill statistics')
    parser.add_argument('--bootstrap-servers', type=str, default='localhost:9092',
                      help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--topic', type=str, default='postgres.public.benchmark_records',
                      help='Kafka topic to consume from (default: postgres.public.benchmark_records)')
    parser.add_argument('--use-iam', action='store_true',
                      help='Use IAM authentication for MSK')
    parser.add_argument('--backfill-count', type=int, default=10000,
                      help='Number of messages to process for backfill statistics (default: 10000)')

    args = parser.parse_args()
    
    bootstrap_servers = args.bootstrap_servers.split(',')
    
    collector = KafkaBackfillCollector(
        bootstrap_servers=bootstrap_servers,
        topic=args.topic,
        use_iam=args.use_iam
    )
    collector.run(args.backfill_count)