"""
Quick check of what's in your RDS database.
"""

from src.utils.database import RDSConnector

db = RDSConnector()

print("=" * 70)
print("📊 DATABASE SUMMARY")
print("=" * 70)

stats = db.get_table_stats('sales_transactions')

print(f"\nTotal Transactions: {stats.get('total_rows', 0):,}")
print(f"Unique Customers: {stats.get('unique_customers', 0):,}")
print(f"Unique Products: {stats.get('unique_products', 0):,}")
print(f"Date Range: {stats.get('earliest_date')} to {stats.get('latest_date')}")
print(f"Total Revenue: ${stats.get('total_revenue', 0):,.2f}")

print("\n" + "=" * 70)

db.close()
