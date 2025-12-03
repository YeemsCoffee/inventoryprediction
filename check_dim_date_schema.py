"""
Check what columns actually exist in gold.dim_date table.
"""

from src.utils.database import RDSConnector
from sqlalchemy import text

db = RDSConnector()

try:
    with db.engine.connect() as conn:
        # Get column names from the table
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'gold'
            AND table_name = 'dim_date'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()

        if columns:
            print("Current columns in gold.dim_date:")
            print("-" * 50)
            for col in columns:
                print(f"  {col[0]:<20} {col[1]}")
        else:
            print("Table gold.dim_date does not exist or has no columns")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
