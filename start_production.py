"""
Production startup script for the BI Dashboard.
Runs the production-grade dashboard with PostgreSQL backend.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename=f'logs/dashboard_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dashboard.production_dashboard import ProductionDashboard

def main():
    """Start the production dashboard."""

    print("\n" + "=" * 70)
    print("🚀 PRODUCTION BUSINESS INTELLIGENCE DASHBOARD")
    print("=" * 70)
    print()

    # Check for database connection
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        print()
        print("Setup instructions:")
        print("  1. Copy .env.example to .env")
        print("  2. Set DATABASE_URL to your PostgreSQL connection string")
        print("  3. Run: python database/init_database.py (if not already done)")
        print("  4. Run: python scripts/sync_square_to_postgres.py --all")
        print()
        sys.exit(1)

    print("✅ Database connection configured")

    # Get settings from environment
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')  # 0.0.0.0 for external access
    port = int(os.getenv('DASHBOARD_PORT', '8050'))
    debug = os.getenv('DASHBOARD_DEBUG', 'False').lower() == 'true'

    print()
    print("✨ Production Features:")
    print("  🔒 Connection pooling (no memory leaks)")
    print("  ⚡ Query caching (fast performance)")
    print("  🤖 ML predictions integrated (churn, forecasts, LTV)")
    print("  📊 Period-over-period comparisons")
    print("  📈 Cohort analysis & customer insights")
    print("  📥 CSV export functionality")
    print("  🛡️  Comprehensive error handling")
    print("  📝 Production logging")
    print()
    print(f"🌐 Dashboard URL: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print()
    print("⏹️  Press Ctrl+C to stop")
    print()

    logging.info(f"Starting production dashboard on {host}:{port}")

    try:
        # Create and run dashboard
        dashboard = ProductionDashboard(database_url)
        dashboard.run(host=host, port=port, debug=debug)

    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped by user")
        logging.info("Dashboard stopped by user")
    except Exception as e:
        logging.error(f"Dashboard failed to start: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Verify DATABASE_URL is correct")
        print("  2. Ensure database is initialized: python database/init_database.py")
        print("  3. Check if data is loaded: python scripts/sync_square_to_postgres.py --all")
        print("  4. Check logs in logs/ directory for details")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
