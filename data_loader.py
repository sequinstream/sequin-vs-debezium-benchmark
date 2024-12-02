import psycopg2
import json
import random
from datetime import datetime
import argparse

class DataLoader:
    def __init__(self, table_name="benchmark_records",
                 dbname="testdb", user="postgres", password="postgres", 
                 host="localhost", port="5432"):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.table_name = table_name
        self.cur = self.conn.cursor()
        
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
        
    def generate_record(self):
        """Generate a single record with random data"""
        return {
            "string_field": f"test-{random.randint(1, 1000)}",
            "numeric_field": round(random.uniform(1, 1000), 2),
            "timestamp_field": datetime.now(),
            "json_field": json.dumps({"hello": f"world-{random.randint(1, 100)}"})
        }
    
    def load_data(self, count, batch_size=1000):
        """Load specified number of records in batches"""
        try:
            self.setup_table()
            
            total_batches = (count + batch_size - 1) // batch_size
            records_loaded = 0
            
            print(f"Loading {count} records in {total_batches} batches...")
            
            for batch_num in range(total_batches):
                # Calculate batch size for last batch
                current_batch_size = min(batch_size, count - records_loaded)
                
                records = [self.generate_record() for _ in range(current_batch_size)]
                args_str = ','.join(self.cur.mogrify(
                    "(%(string_field)s, %(numeric_field)s, %(timestamp_field)s, %(json_field)s)",
                    record
                ).decode('utf-8') for record in records)
                
                self.cur.execute(f"""
                    INSERT INTO {self.table_name} 
                    (string_field, numeric_field, timestamp_field, json_field)
                    VALUES {args_str}
                """)
                
                self.conn.commit()
                records_loaded += current_batch_size
                
                print(f"Batch {batch_num + 1}/{total_batches} complete. "
                      f"Loaded {records_loaded}/{count} records...")
                
        except Exception as e:
            print(f"Error loading data: {e}")
        finally:
            print(f"\nFinal Statistics:")
            print(f"Total records loaded: {records_loaded}")
            self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load test data into database')
    parser.add_argument('--count', type=int, required=True,
                      help='Number of records to load')
    parser.add_argument('--batch-size', type=int, default=1000,
                      help='Number of records per batch (default: 1000)')
    parser.add_argument('--dbname', type=str, default='testdb',
                      help='Database name (default: testdb)')
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
    
    args = parser.parse_args()
    
    loader = DataLoader(
        table_name=args.table_name,
        dbname=args.dbname,
        user=args.user,
        password=args.password,
        host=args.host,
        port=args.port
    )
    loader.load_data(count=args.count, batch_size=args.batch_size)