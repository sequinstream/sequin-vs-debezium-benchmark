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
        
    def truncate_table(self):
        """Truncate the table"""
        self.cur.execute(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY")
        self.conn.commit()
        
    def setup_table(self):
        """Create the table if it doesn't exist and truncate it"""
        self.cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                string_field TEXT,
                numeric_field DECIMAL,
                timestamp_field TIMESTAMP WITH TIME ZONE,
                json_field JSONB,
                inserted_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        self.conn.commit()
        self.truncate_table()
        
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
    
    def update_batch(self, ids):
        """Update all records in the batch"""
        if not ids:
            return
        
        new_data = self.generate_record()
        id_list = ','.join(str(id[0]) for id in ids)
        self.cur.execute(f"""
            UPDATE {self.table_name}
            SET string_field = %(string_field)s,
                numeric_field = %(numeric_field)s,
                timestamp_field = %(timestamp_field)s,
                json_field = %(json_field)s,
                updated_at = NOW()
            WHERE id IN ({id_list})
        """, new_data)
    
    def delete_batch(self, ids):
        """Delete all records in the batch"""
        if not ids:
            return
        
        self.cur.execute(f"""
            DELETE FROM {self.table_name}
            WHERE id IN ({','.join(str(id[0]) for id in ids)})
        """)
        
        return []  # Return empty list since we deleted everything
    
    def run(self, duration_seconds=60):
        """Run the workload for a specified duration"""
        try:
            self.setup_table()
            start_time = time.time()
            total_operations = 0
            total_bytes = 0
            batch_start_time = time.time()
            
            print("\033[2J\033[H")  # Clear screen and move cursor to top
            print("Running workload generator...\n")
            
            while time.time() - start_time < duration_seconds:
                # Insert batch
                new_ids = self.insert_batch()
                
                # Update all records in batch
                # self.update_batch(new_ids)
                
                # Delete all records in batch
                # self.delete_batch(new_ids)
                
                self.conn.commit()
                
                # Calculate operations and data volumes
                inserts = len(new_ids)
                updates = len(new_ids)
                deletes = len(new_ids)
                batch_operations = inserts + updates + deletes
                batch_bytes = (inserts + updates + deletes) * self.target_bytes
                
                total_operations += batch_operations
                total_bytes += batch_bytes
                
                # Calculate elapsed time and throughput
                current_time = time.time()
                batch_elapsed = current_time - batch_start_time
                overall_elapsed = current_time - start_time
                
                # Calculate throughput metrics
                batch_throughput = batch_operations / batch_elapsed
                overall_throughput = total_operations / overall_elapsed
                
                # Calculate data throughput
                batch_data_throughput = batch_bytes / batch_elapsed
                overall_data_throughput = total_bytes / overall_elapsed
                
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
                    f"Batch: {inserts}i/{updates}u/{deletes}d | "
                    f"Batch time: {batch_elapsed:.2f}s | "
                    f"Batch throughput: {batch_throughput:.2f} ops/s | "
                    f"Data: {format_data_rate(batch_data_throughput)}\n"
                    f"Total operations: {total_operations} | "
                    f"Overall throughput: {overall_throughput:.2f} ops/s | "
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
            print(f"Total operations: {total_operations}")
            print(f"Total data processed: {total_bytes/1_000_000:.2f} MB")
            print(f"Total time: {total_elapsed:.2f}s")
            print(f"Average throughput: {final_throughput:.2f} ops/s")
            print(f"Average data throughput: {format_data_rate(final_data_throughput)}")
            self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate database workload')
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
    generator.run(duration_seconds=args.duration) 
