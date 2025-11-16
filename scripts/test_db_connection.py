"""
Quick database connection test
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test database connection and list schemas"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL not set")
        return False

    print(f"🔗 Testing connection to: {database_url.split('@')[1].split('/')[0]}")
    print(f"📊 Database: {database_url.split('/')[-1]}")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check current database
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"✅ Connected to database: {db_name}")

        # List schemas
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = cursor.fetchall()
        print(f"\n📂 Schemas in database:")
        for schema in schemas:
            print(f"   - {schema[0]}")

        # Check if bronze schema exists
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.schemata
                WHERE schema_name = 'bronze'
            );
        """)
        bronze_exists = cursor.fetchone()[0]

        if bronze_exists:
            print("\n✅ Bronze schema exists")

            # Check for square_orders table
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'bronze' AND table_name = 'square_orders'
                );
            """)
            table_exists = cursor.fetchone()[0]

            if table_exists:
                print("✅ bronze.square_orders table exists")

                # Check for customer_id column
                cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='bronze'
                        AND table_name='square_orders'
                        AND column_name='customer_id'
                    );
                """)
                column_exists = cursor.fetchone()[0]

                if column_exists:
                    print("✅ customer_id column exists")
                else:
                    print("❌ customer_id column MISSING")
            else:
                print("❌ bronze.square_orders table does NOT exist")
        else:
            print("\n❌ Bronze schema does NOT exist - needs setup")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
