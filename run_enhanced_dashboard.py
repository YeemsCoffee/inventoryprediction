"""
Launch the enhanced production dashboard
"""

import os
from dotenv import load_dotenv

load_dotenv()

from src.dashboard.enhanced_dashboard import EnhancedDashboard

if __name__ == "__main__":
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env")
        print("\nPlease add to your .env file:")
        print("DATABASE_URL=postgresql://user:password@host:5432/database")
        exit(1)

    print("\n" + "=" * 70)
    print("🚀 LAUNCHING ENHANCED BI DASHBOARD")
    print("=" * 70)
    print("\n✨ New Features:")
    print("  📅 Date Range Picker - Select any date range")
    print("  📍 Location Filter - Filter by store location")
    print("  ⚡ Quick Filters - 7D, 30D, 90D, YTD, All")
    print("  📊 Real-time KPIs - Orders, Revenue, AOV, Customers")
    print("  📈 Interactive Charts - Click and explore your data")
    print("  🎨 Modern UI - Professional, clean design")
    print("\n🔗 Data Source: AWS RDS PostgreSQL")
    print("🌐 Opening at: http://localhost:8050")
    print("\n⏹️  Press Ctrl+C to stop the server")
    print("=" * 70)
    print()

    dashboard = EnhancedDashboard(database_url)
    dashboard.run(host='0.0.0.0', port=8050, debug=False)
