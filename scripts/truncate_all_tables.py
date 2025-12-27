"""
Truncate all tables for a clean resync
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from src.utils.database import RDSConnector
from sqlalchemy import text

def truncate_all():
    """Truncate all tables in reverse dependency order"""

    print("=" * 70)
    print("🗑️  TRUNCATING ALL TABLES FOR CLEAN RESYNC")
    print("=" * 70)
    print()

    db = RDSConnector()

    try:
        with db.engine.begin() as conn:
            # Gold layer first
            print("📊 Truncating gold layer...")
            conn.execute(text("TRUNCATE gold.fact_sales CASCADE"))
            conn.execute(text("TRUNCATE gold.customer_metrics CASCADE"))
            conn.execute(text("TRUNCATE gold.dim_customer CASCADE"))
            conn.execute(text("TRUNCATE gold.dim_product CASCADE"))
            conn.execute(text("TRUNCATE gold.dim_location CASCADE"))
            print("  ✅ Gold layer cleared")
            print()

            # Silver layer
            print("📊 Truncating silver layer...")
            conn.execute(text("TRUNCATE silver.transactions CASCADE"))
            conn.execute(text("TRUNCATE silver.customers CASCADE"))
            conn.execute(text("TRUNCATE silver.products CASCADE"))
            conn.execute(text("TRUNCATE silver.locations CASCADE"))
            print("  ✅ Silver layer cleared")
            print()

            # Bronze layer
            print("📊 Truncating bronze layer...")
            conn.execute(text("TRUNCATE bronze.sales_transactions CASCADE"))
            conn.execute(text("TRUNCATE bronze.square_orders CASCADE"))
            conn.execute(text("TRUNCATE bronze.square_line_items CASCADE"))
            print("  ✅ Bronze layer cleared")
            print()

        print("=" * 70)
        print("✅ ALL TABLES TRUNCATED - Ready for clean resync")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    truncate_all()
