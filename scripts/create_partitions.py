"""
Create missing partitions for gold.fact_sales table

This script adds partitions for years that have data but no partition.
"""

import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def create_partitions():
    """Create missing fact_sales partitions"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print("=" * 70)
    print("🔧 CREATING MISSING FACT_SALES PARTITIONS")
    print("=" * 70)
    print()

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("📊 Checking existing partitions...")
        cursor.execute("""
            SELECT
                c.relname as partition_name,
                pg_get_expr(c.relpartbound, c.oid) as partition_range
            FROM pg_class c
            JOIN pg_inherits i ON c.oid = i.inhrelid
            JOIN pg_class p ON i.inhparent = p.oid
            WHERE p.relname = 'fact_sales'
            ORDER BY c.relname;
        """)

        existing_partitions = cursor.fetchall()
        if existing_partitions:
            print("✅ Existing partitions:")
            for name, range_def in existing_partitions:
                print(f"   - {name}: {range_def}")
        else:
            print("⚠️  No partitions found!")
        print()

        # Define partitions to create (from 2020 onwards)
        years_to_create = [
            (2020, 20200101, 20210101),
            (2021, 20210101, 20220101),
            (2022, 20220101, 20230101),  # The missing one!
            (2023, 20230101, 20240101),
            (2024, 20240101, 20250101),
            (2025, 20250101, 20260101),
            (2026, 20260101, 20270101),
            (2027, 20270101, 20280101),
        ]

        print("🔨 Creating partitions...")
        created_count = 0
        skipped_count = 0

        for year, start_key, end_key in years_to_create:
            partition_name = f"gold.fact_sales_{year}"

            try:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name}
                        PARTITION OF gold.fact_sales
                        FOR VALUES FROM ({start_key}) TO ({end_key});
                """)
                conn.commit()

                # Check if it was actually created or already existed
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_class c
                        JOIN pg_inherits i ON c.oid = i.inhrelid
                        JOIN pg_class p ON i.inhparent = p.oid
                        WHERE p.relname = 'fact_sales'
                        AND c.relname = %s
                    );
                """, (f"fact_sales_{year}",))

                exists = cursor.fetchone()[0]
                if exists:
                    print(f"✅ {partition_name} ({start_key} to {end_key})")
                    created_count += 1
                else:
                    print(f"⚠️  {partition_name} - could not verify")

            except psycopg2.errors.DuplicateTable as e:
                conn.rollback()
                print(f"⏭️  {partition_name} - already exists")
                skipped_count += 1
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()

            except Exception as e:
                conn.rollback()
                print(f"❌ {partition_name} - error: {e}")
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()

        print()
        print("=" * 70)
        print(f"✅ PARTITION CREATION COMPLETE")
        print("=" * 70)
        print(f"   Created/Verified: {created_count}")
        print(f"   Already existed: {skipped_count}")
        print()

        # Show final list of partitions
        print("📋 Final partition list:")
        cursor.execute("""
            SELECT
                c.relname as partition_name,
                pg_get_expr(c.relpartbound, c.oid) as partition_range
            FROM pg_class c
            JOIN pg_inherits i ON c.oid = i.inhrelid
            JOIN pg_class p ON i.inhparent = p.oid
            WHERE p.relname = 'fact_sales'
            ORDER BY c.relname;
        """)

        all_partitions = cursor.fetchall()
        for name, range_def in all_partitions:
            print(f"   - {name}: {range_def}")

        print()
        print("✅ You can now run the sync script:")
        print("   python scripts/sync_square_to_postgres.py --days 90 --oldest")
        print()

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_partitions()
