import psycopg2
import json
import random
import time
from datetime import datetime
import argparse
from collections import deque

class WorkloadGenerator:
    def __init__(self, batch_size=100, interval=1.0, table_name="benchmark_records",
                 dbname="testdb", user="postgres", password="postgres", 
                 host="localhost", port="5432", target_bytes=100, num_columns=1):
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
        self.num_columns = num_columns
        self.cached_paddings = self._generate_cached_paddings(1000)  # Generate 1000 unique paddings
        self.padding_index = 0
        
        # Maintain separate pools for update and delete operations
        self.update_pool = deque()
        self.delete_pool = deque()
        
    def _generate_cached_paddings(self, count):
        """Pre-generate a list of padding strings"""
        base_size = 93  # Base row size including headers and fixed fields
        padding_needed = max(0, self.target_bytes - base_size)
        return [
            ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=padding_needed))
            for _ in range(count)
        ]
        
    def truncate_table(self):
        """Truncate the table"""
        self.cur.execute(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY")
        self.conn.commit()
        
    def setup_table(self):
        """Create the table if it doesn't exist and truncate it"""
        # Generate dynamic columns
        extra_columns = [f"extra_col_{i} TEXT" for i in range(self.num_columns)]
        columns_def = ",\n                ".join([
            "id SERIAL PRIMARY KEY",
            "string_field TEXT",
            "numeric_field DECIMAL",
            "timestamp_field TIMESTAMP WITH TIME ZONE",
            "json_field JSONB",
            *extra_columns,
            "inserted_at TIMESTAMP DEFAULT NOW()",
            "updated_at TIMESTAMP DEFAULT NOW()"
        ])
        
        self.cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                {columns_def}
            )
        """)
        self.conn.commit()
        self.truncate_table()
        # Clear the pools
        self.update_pool.clear()
        self.delete_pool.clear()
        
    def generate_record(self):
        """Generate a single record with random data"""
        padding = self.cached_paddings[self.padding_index]
        self.padding_index = (self.padding_index + 1) % len(self.cached_paddings)
        
        # Base record
        record = {
            "string_field": f"test-{random.randint(1, 1000)}",
            "numeric_field": round(random.uniform(1, 1000), 2),
            "timestamp_field": datetime.now(),
            "json_field": json.dumps({
                "hello": f"world-{random.randint(1, 100)}",
                "padding": padding
            })
        }
        
        # Add extra columns
        for i in range(self.num_columns):
            record[f"extra_col_{i}"] = f"extra-{random.randint(1, 1000)}"
            
        return record
    
    def insert_batch(self):
        """Insert a batch of records"""
        records = [self.generate_record() for _ in range(self.batch_size)]
        
        # Build the column list and value placeholders
        columns = ["string_field", "numeric_field", "timestamp_field", "json_field"] + [f"extra_col_{i}" for i in range(self.num_columns)]
        placeholders = [f"%({col})s" for col in columns]
        
        args_str = ','.join(self.cur.mogrify(
            f"({', '.join(placeholders)})",
            record
        ).decode('utf-8') for record in records)
        
        self.cur.execute(f"""
            INSERT INTO {self.table_name} 
            ({', '.join(columns)})
            VALUES {args_str}
            RETURNING id
        """)
        return self.cur.fetchall()
    
    def update_batch(self, batch_size):
        """Update a batch of records from the update pool"""
        if not self.update_pool or len(self.update_pool) < batch_size:
            # Not enough records to update, return empty list
            return []
        
        # Take records from the update pool
        ids_to_update = [self.update_pool.popleft() for _ in range(batch_size)]
        
        new_data = self.generate_record()
        id_list = ','.join(str(id[0]) for id in ids_to_update)
        
        # Build the SET clause including extra columns
        set_clause = ', '.join([
            "string_field = %(string_field)s",
            "numeric_field = %(numeric_field)s",
            "timestamp_field = %(timestamp_field)s",
            "json_field = %(json_field)s"
        ] + [
            f"extra_col_{i} = %(extra_col_{i})s" for i in range(self.num_columns)
        ] + ["updated_at = NOW()"])
        
        self.cur.execute(f"""
            UPDATE {self.table_name}
            SET {set_clause}
            WHERE id IN ({id_list})
        """, new_data)
        
        # Move updated records to the delete pool
        for id_record in ids_to_update:
            self.delete_pool.append(id_record)
            
        return ids_to_update
    
    def delete_batch(self, batch_size):
        """Delete a batch of records from the delete pool"""
        if not self.delete_pool or len(self.delete_pool) < batch_size:
            # Not enough records to delete, return empty list
            return []
        
        # Take records from the delete pool
        ids_to_delete = [self.delete_pool.popleft() for _ in range(batch_size)]
        
        id_list = ','.join(str(id[0]) for id in ids_to_delete)
        
        self.cur.execute(f"""
            DELETE FROM {self.table_name}
            WHERE id IN ({id_list})
        """)
        
        return ids_to_delete
    
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
            
            # Pre-populate the database with some records for updates and deletes
            warmup_batches = 3  # Number of batches to pre-populate
            for _ in range(warmup_batches):
                new_ids = self.insert_batch()
                # Add half to update pool, half to delete pool for initial operations
                half_point = len(new_ids) // 2
                for i, id_record in enumerate(new_ids):
                    if i < half_point:
                        self.update_pool.append(id_record)
                    else:
                        self.delete_pool.append(id_record)
            self.conn.commit()
            
            while time.time() - start_time < duration_seconds:
                # Insert new records
                new_ids = self.insert_batch()
                
                # Add new records to the update pool for future updates
                # for id_record in new_ids:
                #     self.update_pool.append(id_record)
                
                # Update records from the update pool
                # updated_ids = self.update_batch(self.batch_size)
                
                # Delete records from the delete pool
                # deleted_ids = self.delete_batch(self.batch_size)
                
                self.conn.commit()
                
                # Calculate operations and data volumes
                inserts = len(new_ids)
                # updates = len(updated_ids)
                # deletes = len(deleted_ids)
                updates = 0
                deletes = 0
                batch_operations = inserts + updates + deletes
                batch_bytes = (inserts + updates + deletes) * self.target_bytes
                
                total_operations += batch_operations
                total_bytes += batch_bytes
                
                # Calculate elapsed time and throughput
                current_time = time.time()
                batch_elapsed = current_time - batch_start_time
                overall_elapsed = current_time - start_time
                
                # Calculate throughput metrics
                batch_throughput = batch_operations / batch_elapsed if batch_elapsed > 0 else 0
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
                    f"Batch: {inserts}i/{updates}u/{deletes}d | "
                    f"Pools: {len(self.update_pool)}u/{len(self.delete_pool)}d | "
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
            final_throughput = total_operations / total_elapsed if total_elapsed > 0 else 0
            final_data_throughput = total_bytes / total_elapsed if total_elapsed > 0 else 0
            print(f"\nFinal Statistics:")
            print(f"Total operations: {total_operations}")
            print(f"Total data processed: {total_bytes/1_000_000:.2f} MB")
            print(f"Total time: {total_elapsed:.2f}s")
            print(f"Average throughput: {final_throughput:.2f} ops/s")
            print(f"Average data throughput: {format_data_rate(final_data_throughput)}")
            print(f"Remaining in pools: {len(self.update_pool)} updates, {len(self.delete_pool)} deletes")
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
    parser.add_argument('--columns', type=int, default=1,
                      help='Number of additional columns (default: 1)')
    
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
        target_bytes=args.byte_size,
        num_columns=args.columns
    )
    generator.run(duration_seconds=args.duration) 
