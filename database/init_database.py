"""
Initialize PostgreSQL database for Inventory BI
Runs all schema SQL files in order
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_sql_file(conn, filepath):
    """Execute SQL from a file."""
    with open(filepath, 'r') as f:
        sql = f.read()

    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()

def main():
    print("=" * 70)
    print("  PostgreSQL Database Initialization for Inventory BI")
    print("=" * 70)
    print()

    # Get database URL
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        print()
        print("Please set DATABASE_URL in your .env file:")
        print("  DATABASE_URL=postgresql://user:password@localhost:5432/inventory_bi")
        print()
        sys.exit(1)

    print("✅ DATABASE_URL is set")
    print()

    # Connect to database
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(database_url)
        print("✅ Connected successfully")
        print()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check if PostgreSQL is running")
        print("  2. Verify DATABASE_URL is correct")
        print("  3. Ensure database 'inventory_bi' exists")
        sys.exit(1)

    # Schema files directory
    schema_dir = Path(__file__).parent / "schemas"

    # Run schema files in order
    schema_files = [
        ("01_create_schemas.sql", "Creating schemas"),
        ("02_bronze_tables.sql", "Creating bronze tables"),
        ("03_silver_tables.sql", "Creating silver tables"),
        ("04_gold_tables.sql", "Creating gold tables"),
        ("05_features_predictions.sql", "Creating features and predictions tables"),
        ("06_populate_dim_date.sql", "Populating date dimension"),
    ]

    for i, (filename, description) in enumerate(schema_files, 1):
        filepath = schema_dir / filename

        print(f"Step {i}: {description}...")
        try:
            run_sql_file(conn, filepath)
            print(f"✅ {description} complete")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
            conn.rollback()
            conn.close()
            sys.exit(1)

    conn.close()

    print("=" * 70)
    print("✅ Database initialization complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run CSV migration: python scripts/migrate_csv_to_postgres.py")
    print("  2. Set up incremental sync: python scripts/sync_square_to_postgres.py")
    print("  3. Run dbt transformations: dbt run")
    print()

if __name__ == "__main__":
    main()
