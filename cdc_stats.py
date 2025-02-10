from confluent_kafka import Consumer, KafkaError
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
import csv
from collections import deque
import argparse
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
import re

class KafkaStatsCollector:
    def __init__(self, bootstrap_servers, topic, use_iam=False, source='debezium'):
        # Common consumer configs
        consumer_config = {
            'bootstrap.servers': ','.join(bootstrap_servers),
            'group.id': 'stats_collector_group',
            'auto.offset.reset': 'end',
            'client.id': 'stats_collector'
        }

        # Configure authentication based on use_iam flag
        if use_iam:
            print("Using IAM authentication")

            def oauth_cb(config):
                # Generate token and convert expiry from ms to seconds
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
        
        # Add tracking for consumer lag
        self.topic = topic
        self.last_processed_offsets = {}
        self.last_committed_offsets = {}
        
        self.latencies = deque(maxlen=10000)  # Rolling window of latencies
        self.replication_latencies = deque(maxlen=100000)  # New: Rolling window for replication latencies
        self.delivery_latencies = deque(maxlen=100000)    # New: Rolling window for delivery latencies
        self.throughput_window = deque(maxlen=100000)  # Rolling window for throughput
        self.stats_file = 'kafka_stats.csv'
        self.last_stats_time = time.time()
        self.stats_interval = 10  # Calculate stats every 10 seconds
        
        # Initialize CSV file with headers
        with open(self.stats_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'time_elapsed_ms', 'avg_latency_ms', 'p50_latency_ms', 
                           'p95_latency_ms', 'p99_latency_ms', 'throughput_msgs_per_sec',
                           'avg_replication_latency_ms', 'avg_delivery_latency_ms'])  # New columns

        self.source = source  # Add source tracking
        self.start_time = time.time() * 1000  # Store start time in milliseconds

    def get_consumer_lag(self):
        # Get topic partition metadata
        assignments = self.consumer.assignment()
        total_lag = 0
        
        for partition in assignments:
            # Get end offset (latest available message)
            high_watermark = self.consumer.get_watermark_offsets(partition)[1]
            # Get current position (need to get the offset value, not the TopicPartition object)
            position = self.consumer.position([partition])[0].offset
            
            partition_lag = high_watermark - position
            total_lag += partition_lag
            
        return total_lag

    def parse_message(self, message):
        """
        Parse a Kafka message based on the source type.
        """
        if self.source == 'debezium':
            return self._parse_debezium_message(message)
        elif self.source == 'sequin':
            return self._parse_sequin_message(message)
        else:
            raise ValueError(f"Unsupported source type: {self.source}")

    def _parse_debezium_message(self, message):
        """
        Parse a Debezium-formatted Kafka message.
        """
        if message is None or message.value() is None:
            return None
        
        try:
            msg_str = message.value().decode('utf-8') if isinstance(message.value(), bytes) else message.value()
            if msg_str is None:
                raise ValueError("Message is None or value is None")
            
            source_ts_match = re.search(r'source=Struct{.*?ts_ms=(\d+)', msg_str)
            delivery_ts_match = re.search(r',ts_ms=(\d+),ts_us=', msg_str)
            
            source_ts = int(source_ts_match.group(1)) if source_ts_match else None
            delivery_ts = int(delivery_ts_match.group(1)) if delivery_ts_match else None
            
            if source_ts is None or delivery_ts is None:
                print(f"Missing timestamps - source_ts: {source_ts}, delivery_ts: {delivery_ts}")
                print(f"Message content: {msg_str}")
                return None
                
            return {
                'source_ts': source_ts,
                'delivery_ts': delivery_ts,
                'latency': delivery_ts - source_ts
            }
            
        except Exception as e:
            print(f"Error processing message content: {e}")
            print(f"Message structure: {message.value()}")
            return None

    def _parse_sequin_message(self, message):
        """
        Parse a Sequin-formatted Kafka message using Kafka's CreateTime.
        """
        if message is None or message.value() is None:
            raise ValueError("Message is None or value is None")
        
        try:
            msg_data = json.loads(message.value())
            metadata = msg_data.get('metadata', {})
            commit_ts = datetime.fromisoformat(metadata['commit_timestamp'].replace('Z', '+00:00'))
            commit_ts_ms = int(commit_ts.timestamp() * 1000)
            # Get Kafka's internal CreateTime
            delivery_ts_ms = message.timestamp()[1]  # timestamp() returns (TimestampType, timestamp)
            
            return {
                'source_ts': commit_ts_ms,
                'delivery_ts': delivery_ts_ms,
                'latency': delivery_ts_ms - commit_ts_ms
            }
            
        except Exception as e:
            print(f"Error processing Sequin message: {e}")
            print(f"Message content: {message.value()}")
            return None

    def calculate_latency(self, message):
        parsed_data = self.parse_message(message)
        if parsed_data:
            self.latencies.append(parsed_data['latency'])
            self.throughput_window.append(time.time())

    def calculate_and_save_stats(self):
        current_time = time.time()
        
        if current_time - self.last_stats_time >= self.stats_interval:
            # Add lag calculation
            consumer_lag = self.get_consumer_lag()
            
            if len(self.latencies) > 0:
                latencies_array = np.array(self.latencies)
                
                # Calculate percentiles
                p99 = np.percentile(latencies_array, 99)
                avg_latency = np.mean(latencies_array)
                
                # Calculate throughput (messages per second)
                recent_times = np.array([t for t in self.throughput_window 
                                       if t > current_time - self.stats_interval])
                throughput = len(recent_times) / (max(recent_times) - min(recent_times)) if len(recent_times) > 1 else 0

                # Save full stats to CSV as before
                time_elapsed = int((current_time * 1000) - self.start_time)
                stats_row = [
                    datetime.now().isoformat(),
                    time_elapsed,
                    round(avg_latency, 2),
                    round(np.percentile(latencies_array, 50), 2),
                    round(np.percentile(latencies_array, 95), 2),
                    round(p99, 2),
                    round(throughput, 2),
                    round(np.mean(np.array(self.replication_latencies)), 2) if self.replication_latencies else '',
                    round(np.mean(np.array(self.delivery_latencies)), 2) if self.delivery_latencies else ''
                ]
                
                # Save to CSV
                with open(self.stats_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(stats_row)
                
                # Print simplified stats
                print(f"Throughput: {throughput:>6.1f} msg/s | Latency avg: {avg_latency:>6.1f}ms p99: {p99:>6.1f}ms | Lag: {consumer_lag:>6d}")
            
            self.last_stats_time = current_time

    def run(self):
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Consumer error: {msg.error()}")
                        break

                try:
                    self.calculate_latency(msg)
                    self.calculate_and_save_stats()
                except Exception as e:
                    print(f"Error processing message: {e}")

        except KeyboardInterrupt:
            print("\nStopping stats collection...")
        finally:
            self.consumer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Collect Kafka consumer statistics')
    parser.add_argument('--bootstrap-servers', type=str, default='localhost:9092',
                      help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--topic', type=str, default='postgres.public.benchmark_records',
                      help='Kafka topic to consume from (default: postgres.public.benchmark_records)')
    parser.add_argument('--stats-interval', type=float, default=5.0,
                      help='Interval between stats calculations in seconds (default: 5.0)')
    parser.add_argument('--use-iam', action='store_true',
                      help='Use IAM authentication for MSK')
    parser.add_argument('--source', type=str, choices=['debezium', 'sequin'], default='debezium',
                      help='Source type of Kafka messages (default: debezium)')

    args = parser.parse_args()
    
    bootstrap_servers = args.bootstrap_servers.split(',')
    
    collector = KafkaStatsCollector(
        bootstrap_servers=bootstrap_servers,
        topic=args.topic,
        use_iam=args.use_iam,
        source=args.source  # Add source parameter
    )
    collector.stats_interval = args.stats_interval
    collector.run() 