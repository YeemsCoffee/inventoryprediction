"""
Fix materialized view indexes to support concurrent refresh

This script adds the missing unique indexes required for concurrent refresh
of materialized views in the gold schema.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def fix_materialized_view_indexes():
    """Add unique indexes to materialized views"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False

    print("=" * 70)
    print("🔧 FIXING MATERIALIZED VIEW INDEXES")
    print("=" * 70)
    print()

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("📊 Step 1: Checking existing materialized views...")
        cursor.execute("""
            SELECT schemaname, matviewname
            FROM pg_matviews
            WHERE schemaname = 'gold'
            ORDER BY matviewname;
        """)

        views = cursor.fetchall()
        if views:
            print("✅ Found materialized views:")
            for schema, view in views:
                print(f"   - {schema}.{view}")
        else:
            print("⚠️  No materialized views found in gold schema")
            return False
        print()

        # Check existing indexes
        print("📋 Step 2: Checking existing indexes...")
        for schema, view in views:
            cursor.execute("""
                SELECT
                    i.relname as index_name,
                    ix.indisunique as is_unique,
                    array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns
                FROM pg_index ix
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                LEFT JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE n.nspname = %s AND t.relname = %s
                GROUP BY i.relname, ix.indisunique
                ORDER BY i.relname;
            """, (schema, view))

            indexes = cursor.fetchall()
            if indexes:
                print(f"\n   {schema}.{view}:")
                for idx_name, is_unique, cols in indexes:
                    unique_marker = "🔑 UNIQUE" if is_unique else "📌 REGULAR"
                    print(f"      {unique_marker} {idx_name} on ({', '.join(cols)})")
            else:
                print(f"\n   {schema}.{view}: No indexes")
        print()

        # Create missing unique indexes
        print("🔨 Step 3: Creating/verifying unique indexes...")

        fixes_applied = 0

        # Fix 1: daily_sales_summary (should already have unique index)
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_summary_date_loc
                ON gold.daily_sales_summary(date_key, location_sk);
            """)
            conn.commit()
            print("✅ gold.daily_sales_summary - unique index on (date_key, location_sk)")
            fixes_applied += 1
        except Exception as e:
            conn.rollback()
            print(f"⚠️  gold.daily_sales_summary - {e}")
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()

        # Fix 2: product_performance (missing unique index!)
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_product_perf_unique
                ON gold.product_performance(product_sk, date_key, location_sk);
            """)
            conn.commit()
            print("✅ gold.product_performance - unique index on (product_sk, date_key, location_sk)")
            fixes_applied += 1
        except Exception as e:
            conn.rollback()
            print(f"⚠️  gold.product_performance - {e}")
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()

        print()

        # Test concurrent refresh
        print("🧪 Step 4: Testing concurrent refresh...")

        test_passed = 0
        test_failed = 0

        for schema, view in views:
            try:
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {schema}.{view}")
                conn.commit()
                print(f"✅ {schema}.{view} - concurrent refresh works!")
                test_passed += 1
            except Exception as e:
                conn.rollback()
                print(f"❌ {schema}.{view} - failed: {e}")
                test_failed += 1
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()

        print()
        print("=" * 70)
        print("✅ FIX COMPLETE")
        print("=" * 70)
        print(f"   Indexes fixed: {fixes_applied}")
        print(f"   Views working: {test_passed}/{len(views)}")

        if test_failed > 0:
            print(f"\n⚠️  Warning: {test_failed} view(s) still cannot refresh concurrently")
            print("   Check the error messages above for details")
        else:
            print("\n✅ All materialized views can now refresh concurrently!")
            print("\nYou can now run the sync script:")
            print("   python scripts/sync_square_to_postgres.py --days 90 --oldest")

        print()

        conn.close()
        return test_failed == 0

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_materialized_view_indexes()
