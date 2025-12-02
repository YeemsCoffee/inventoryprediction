"""
Complete Bronze/Silver/Gold pipeline setup.
Runs all steps in correct order.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import setup_medallion_architecture
import migrate_to_medallion
import populate_dim_date
import transform_bronze_to_gold


def main():
    """Run complete pipeline setup."""

    print("=" * 70)
    print("🚀 COMPLETE MEDALLION ARCHITECTURE SETUP")
    print("=" * 70)
    print()
    print("This will:")
    print("  1. Create Bronze/Silver/Gold schemas and tables")
    print("  2. Migrate existing sales_transactions to Bronze")
    print("  3. Populate date dimension")
    print("  4. Transform Bronze → Silver → Gold")
    print()

    response = input("Continue? (yes/no): ").lower()

    if response not in ['yes', 'y']:
        print("Cancelled.")
        return

    print()

    try:
        # Step 1: Create architecture
        print("\n" + "=" * 70)
        print("STEP 1: Creating Architecture")
        print("=" * 70 + "\n")
        setup_medallion_architecture.setup_medallion_architecture()

        # Step 2: Migrate data
        print("\n" + "=" * 70)
        print("STEP 2: Migrating Existing Data")
        print("=" * 70 + "\n")
        migrate_to_medallion.migrate_existing_data()

        # Step 3: Populate date dimension
        print("\n" + "=" * 70)
        print("STEP 3: Populating Date Dimension")
        print("=" * 70 + "\n")
        populate_dim_date.populate_dim_date()

        # Step 4: Transform data
        print("\n" + "=" * 70)
        print("STEP 4: Transforming Data")
        print("=" * 70 + "\n")
        transform_bronze_to_gold.main()

        # Final summary
        print("\n" + "=" * 70)
        print("🎉 SETUP COMPLETE!")
        print("=" * 70)
        print()
        print("✅ Your RDS database now has:")
        print()
        print("📊 Bronze Layer (Raw Data):")
        print("   • bronze.sales_transactions")
        print()
        print("📊 Silver Layer (Cleaned Data):")
        print("   • silver.locations")
        print("   • silver.customers")
        print("   • silver.products")
        print("   • silver.transactions")
        print()
        print("📊 Gold Layer (Analytics):")
        print("   • gold.dim_date")
        print("   • gold.dim_customer")
        print("   • gold.dim_product")
        print("   • gold.dim_location")
        print("   • gold.fact_sales")
        print("   • gold.customer_metrics")
        print()
        print("💡 What you can do now:")
        print()
        print("   1. Query analytics data:")
        print("      SELECT * FROM gold.fact_sales LIMIT 10;")
        print()
        print("   2. Get customer RFM metrics:")
        print("      SELECT * FROM gold.customer_metrics ORDER BY monetary_total DESC;")
        print()
        print("   3. Run ML models on gold data:")
        print("      python examples/analyze_from_rds.py")
        print()
        print("   4. Future Square syncs will automatically flow through:")
        print("      Square → Bronze → Silver → Gold")
        print()

    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
