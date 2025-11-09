"""
Create the inventorybi database in AWS RDS
Run this if you get "database does not exist" error
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to the default 'postgres' database first
conn_string = "postgresql://postgres:Jijihwan1995!@inventorybi.cn4cyew02c9g.us-west-1.rds.amazonaws.com:5432/postgres"

print("🔌 Connecting to RDS default database...")

try:
    # Connect to default postgres database
    conn = psycopg2.connect(conn_string)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()

    print("✅ Connected to RDS")
    print()

    # Check if inventorybi database already exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'inventorybi'")
    exists = cursor.fetchone()

    if exists:
        print("✅ Database 'inventorybi' already exists")
    else:
        print("📝 Creating database 'inventorybi'...")
        cursor.execute("CREATE DATABASE inventorybi")
        print("✅ Database 'inventorybi' created successfully!")

    print()
    print("=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. python database/init_database.py")
    print("  2. python scripts/migrate_csv_to_postgres.py")
    print()

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Troubleshooting:")
    print("  1. Verify your RDS endpoint is correct")
    print("  2. Check security group allows your IP on port 5432")
    print("  3. Verify password is correct")
