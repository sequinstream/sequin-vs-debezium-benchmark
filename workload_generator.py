import psycopg2
import json
import random
import time
from datetime import datetime
import argparse

class WorkloadGenerator:
    def __init__(self, batch_size=100, interval=1.0, table_name="benchmark_records",
                 dbname="testdb", user="postgres", password="postgres", 
                 host="localhost", port="5432", target_bytes=100):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.batch_size = batch_size
        self.interval = interval
        self.table_name = table_name
        self.cur = self.conn.cursor()
        self.target_bytes = target_bytes
        self.partition_count = 16
        self.total_rows = 600_000
        self.rows_per_partition = self.total_rows // self.partition_count
        
    def truncate_table(self):
        """Truncate the table"""
        self.cur.execute(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY")
        self.conn.commit()
        
    def setup_table(self):
        """Drop and recreate the partitioned table"""
        # Drop existing table if it exists
        self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        
        # Create new partitioned table
        self.cur.execute(f"""
            CREATE TABLE {self.table_name} (
                id SERIAL PRIMARY KEY,
                string_field TEXT,
                numeric_field DECIMAL,
                timestamp_field TIMESTAMP WITH TIME ZONE,
                json_field JSONB,
                inserted_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            ) PARTITION BY RANGE (id)
        """)
        
        # Create partitions with inclusive ranges
        for i in range(self.partition_count):
            start_range, end_range = self.get_partition_range(i)
            partition_name = f"{self.table_name}_p{i}"
            
            self.cur.execute(f"""
                CREATE TABLE {partition_name}
                PARTITION OF {self.table_name}
                FOR VALUES FROM ({start_range}) TO ({end_range})
            """)
        
        self.conn.commit()

    def get_partition_range(self, partition_num):
        start_range = partition_num * self.rows_per_partition + 1
        end_range = start_range + self.rows_per_partition
        return start_range, end_range
        
    def load_initial_data(self):
        """Load initial data during setup"""
        print("\nLoading initial data...")
        batch_size = 10000  # Use larger batches for initial load
        loaded_rows = 0
        
        while loaded_rows < self.total_rows:
            records = [self.generate_record() for _ in range(batch_size)]
            args_str = ','.join(self.cur.mogrify(
                "(%(string_field)s, %(numeric_field)s, %(timestamp_field)s, %(json_field)s)",
                record
            ).decode('utf-8') for record in records)
            
            self.cur.execute(f"""
                INSERT INTO {self.table_name} 
                (string_field, numeric_field, timestamp_field, json_field)
                VALUES {args_str}
            """)
            
            loaded_rows += batch_size
            self.conn.commit()
            
            # Print progress
            progress = (loaded_rows / self.total_rows) * 100
            print(f"\rProgress: {progress:.2f}% ({loaded_rows:,} / {self.total_rows:,} rows)", end='')
        
        print("\nInitial data load complete!")

    def generate_record(self):
        """Generate a single record with random data"""
        # Calculate approximate static field sizes
        base_size = 93  # Base row size including headers and fixed fields
        
        # Generate padding to reach target size
        padding_needed = max(0, self.target_bytes - base_size)
        padding = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=padding_needed))
        
        return {
            "string_field": f"test-{random.randint(1, 1000)}",
            "numeric_field": round(random.uniform(1, 1000), 2),
            "timestamp_field": datetime.now(),
            "json_field": json.dumps({
                "hello": f"world-{random.randint(1, 100)}",
                "padding": padding
            })
        }
    
    def insert_batch(self):
        """Insert a batch of records"""
        records = [self.generate_record() for _ in range(self.batch_size)]
        args_str = ','.join(self.cur.mogrify(
            "(%(string_field)s, %(numeric_field)s, %(timestamp_field)s, %(json_field)s)",
            record
        ).decode('utf-8') for record in records)
        
        self.cur.execute(f"""
            INSERT INTO {self.table_name} 
            (string_field, numeric_field, timestamp_field, json_field)
            VALUES {args_str}
            RETURNING id
        """)
        return self.cur.fetchall()
    
    def get_random_ids_in_range(self, start_range, end_range):
        """Generate a batch of random IDs within the specified range"""
        return [random.randint(start_range, end_range - 1) for _ in range(self.batch_size)]

    def update_batch_in_range(self, start_range, end_range):
        """Update a batch of random records within the specified ID range"""
        ids = self.get_random_ids_in_range(start_range, end_range)
        new_data = self.generate_record()
        id_list = ','.join(str(id) for id in ids)
        self.cur.execute(f"""
            UPDATE {self.table_name}
            SET string_field = %(string_field)s,
                numeric_field = %(numeric_field)s,
                timestamp_field = %(timestamp_field)s,
                json_field = %(json_field)s,
                updated_at = NOW()
            WHERE id IN ({id_list})
        """, new_data)
        return self.cur.rowcount
    
    def delete_batch(self, ids):
        """Delete all records in the batch"""
        if not ids:
            return
        
        self.cur.execute(f"""
            DELETE FROM {self.table_name}
            WHERE id IN ({','.join(str(id[0]) for id in ids)})
        """)
        
        return []  # Return empty list since we deleted everything
    
    def run(self, duration_seconds=60, setup_mode=False, partition=None):
        """Run the workload generator"""
        if setup_mode:
            print("Running setup mode...")
            self.setup_table()
            self.load_initial_data()
            return

        if partition is None:
            raise ValueError("Partition number must be specified")

        if partition < 0 or partition >= self.partition_count:
            raise ValueError(f"Partition must be between 0 and {self.partition_count-1}")

        start_range, end_range = self.get_partition_range(partition)
        print(f"\nUpdating partition {partition} (ID range: {start_range:,} to {end_range:,})")
            
        try:
            start_time = time.time()
            total_operations = 0
            total_bytes = 0
            batch_start_time = time.time()
            
            print("\033[2J\033[H")  # Clear screen and move cursor to top
            print("Running workload generator...\n")
            
            while time.time() - start_time < duration_seconds:
                # Update batch of records in partition
                updates = self.update_batch_in_range(start_range, end_range)
                self.conn.commit()
                
                # Calculate metrics
                batch_bytes = updates * self.target_bytes
                total_operations += updates
                total_bytes += batch_bytes
                
                # Calculate elapsed time and throughput
                current_time = time.time()
                batch_elapsed = current_time - batch_start_time
                overall_elapsed = current_time - start_time
                
                # Calculate throughput metrics
                batch_throughput = updates / batch_elapsed if batch_elapsed > 0 else 0
                overall_throughput = total_operations / overall_elapsed if overall_elapsed > 0 else 0
                
                # Calculate data throughput
                batch_data_throughput = batch_bytes / batch_elapsed if batch_elapsed > 0 else 0
                overall_data_throughput = total_bytes / overall_elapsed if overall_elapsed > 0 else 0
                
                # Format data throughput for display
                def format_data_rate(bytes_per_sec):
                    if bytes_per_sec >= 1_000_000:
                        return f"{bytes_per_sec/1_000_000:.2f} MB/s"
                    elif bytes_per_sec >= 1_000:
                        return f"{bytes_per_sec/1_000:.2f} KB/s"
                    else:
                        return f"{bytes_per_sec:.2f} B/s"
                
                # Calculate progress
                progress = (current_time - start_time) / duration_seconds
                bar_width = 30
                filled = int(bar_width * progress)
                bar = '█' * filled + '░' * (bar_width - filled)
                percentage = progress * 100
                
                # Update status with progress bar and throughput metrics
                status = (
                    f"\r[{bar}] {percentage:0.1f}%\n"
                    f"Updates: {updates} | "
                    f"Batch throughput: {batch_throughput:.2f} updates/s | "
                    f"Data: {format_data_rate(batch_data_throughput)}\n"
                    f"Total updates: {total_operations} | "
                    f"Overall throughput: {overall_throughput:.2f} updates/s | "
                    f"Avg Data: {format_data_rate(overall_data_throughput)}"
                )
                print(f"{status}\033[2A", end='', flush=True)
                
                batch_start_time = time.time()
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n\nStopping workload generator...")
        finally:
            print("\n")
            end_time = time.time()
            total_elapsed = end_time - start_time
            final_throughput = total_operations / total_elapsed
            final_data_throughput = total_bytes / total_elapsed
            print(f"\nFinal Statistics:")
            print(f"Total updates: {total_operations}")
            print(f"Total data processed: {total_bytes/1_000_000:.2f} MB")
            print(f"Total time: {total_elapsed:.2f}s")
            print(f"Average throughput: {final_throughput:.2f} updates/s")
            print(f"Average data throughput: {format_data_rate(final_data_throughput)}")
            self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate database workload')
    parser.add_argument('--setup', action='store_true',
                      help='Run in setup mode to create and load initial data')
    parser.add_argument('--batch-size', type=int, default=100,
                      help='Number of records per batch (default: 100)')
    parser.add_argument('--interval', type=float, default=1.0,
                      help='Interval between batches in seconds (default: 1.0)')
    parser.add_argument('--duration', type=int, default=60,
                      help='Duration to run in seconds (default: 60)')
    parser.add_argument('--dbname', type=str, default='postgres',
                      help='Database name (default: postgres)')
    parser.add_argument('--user', type=str, default='postgres',
                      help='Database user (default: postgres)')
    parser.add_argument('--password', type=str, default='postgres',
                      help='Database password (default: postgres)')
    parser.add_argument('--host', type=str, default='localhost',
                      help='Database host (default: localhost)')
    parser.add_argument('--port', type=str, default='5432',
                      help='Database port (default: 5432)')
    parser.add_argument('--table-name', type=str, default='benchmark_records',
                      help='Table name (default: benchmark_records)')
    parser.add_argument('--byte-size', type=int, default=100,
                      help='Target size in bytes for each row (default: 100)')
    parser.add_argument('--partition', type=int,
                      help='Partition number to update (0-15)')
    
    args = parser.parse_args()
    
    generator = WorkloadGenerator(
        batch_size=args.batch_size,
        interval=args.interval,
        table_name=args.table_name,
        dbname=args.dbname,
        user=args.user,
        password=args.password,
        host=args.host,
        port=args.port,
        target_bytes=args.byte_size
    )
    generator.run(duration_seconds=args.duration, setup_mode=args.setup, partition=args.partition) 
