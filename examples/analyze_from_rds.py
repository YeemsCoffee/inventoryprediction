"""
Pull data from Amazon RDS and run ML analysis.
Main script for analyzing Square data stored in RDS.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.database import RDSConnector
from src.app import CustomerTrendApp


def main():
    """Pull data from RDS and run comprehensive ML analysis."""

    print("=" * 70)
    print("📊 INVENTORY PREDICTION - RDS DATA ANALYSIS")
    print("=" * 70)

    # Step 1: Connect to RDS
    print("\n🔌 Connecting to Amazon RDS...")
    print("-" * 70)

    try:
        db = RDSConnector()
        result = db.test_connection()

        if not result['success']:
            print(f"❌ {result['message']}")
            print("\n⚠️  Make sure your .env file has:")
            print("   DATABASE_URL=postgresql://user:password@your-rds-endpoint:5432/dbname")
            return

        print(f"✅ Connected to: {result['database']}")
        print(f"   Host: {result['host']}")
        print(f"   Tables: {result['table_count']}")

    except ValueError as e:
        print(f"❌ {str(e)}")
        print("\n📝 Setup instructions:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("\n2. Edit .env and add your Amazon RDS connection:")
        print("   DATABASE_URL=postgresql://user:password@your-endpoint:5432/dbname")
        return
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return

    # Step 2: Check database stats
    print("\n📊 Database Statistics")
    print("-" * 70)

    try:
        stats = db.get_table_stats('sales_transactions')

        if stats.get('total_rows', 0) == 0:
            print("⚠️  No data found in database!")
            print("\n💡 First, sync your Square data to RDS:")
            print("   python examples/rds_sync_example.py")
            db.close()
            return

        print(f"✅ Found data in database:")
        print(f"   Total Transactions: {stats['total_rows']:,}")
        print(f"   Unique Customers: {stats['unique_customers']:,}")
        print(f"   Unique Products: {stats['unique_products']:,}")
        print(f"   Date Range: {stats['earliest_date']} to {stats['latest_date']}")
        print(f"   Total Revenue: ${stats['total_revenue']:,.2f}")

    except Exception as e:
        print(f"❌ Error reading database: {str(e)}")
        print("\n💡 You may need to sync data first:")
        print("   python examples/rds_sync_example.py")
        db.close()
        return

    # Step 3: Pull data from RDS
    print("\n📥 Pulling Data from RDS")
    print("-" * 70)

    # Option: Specify date range or pull all data
    # Uncomment to filter by date:
    # start_date = '2024-01-01'
    # end_date = '2024-12-31'
    # df = db.get_sales_data(start_date=start_date, end_date=end_date)

    # Pull all data
    df = db.get_sales_data()

    print(f"✅ Retrieved {len(df)} transactions")

    # Save to CSV for reference
    output_path = 'data/raw/from_rds.csv'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"💾 Data saved to: {output_path}")

    # Step 4: Run ML Analysis
    print("\n🤖 Running ML Analysis")
    print("-" * 70)

    app = CustomerTrendApp()
    app.data = df

    # Ensure date column is datetime
    if 'date' in df.columns:
        app.data['date'] = pd.to_datetime(app.data['date'])

    print("✅ Data loaded successfully")

    # Generate comprehensive analysis
    print("\n🔮 Generating Full Report...")
    report = app.generate_full_report(n_segments=4)

    # Display results
    print("\n" + "=" * 70)
    app.print_summary(report)
    print("=" * 70)

    # Additional insights
    print("\n📈 Key Recommendations:")
    print("-" * 70)

    if 'seasonal_analysis' in report and 'recommendations' in report['seasonal_analysis']:
        for rec in report['seasonal_analysis']['recommendations'][:3]:
            print(f"  • {rec}")

    print("\n💡 Next Steps:")
    print("-" * 70)
    print("  1. View interactive dashboard:")
    print("     python -m src.dashboard.app")
    print("\n  2. Get inventory recommendations:")
    print("     python examples/inventory_recommendations_example.py")
    print("\n  3. Schedule automatic daily sync:")
    print("     python examples/rds_sync_example.py")

    # Close database connection
    db.close()
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
