"""
Production startup script for the BI Dashboard.
Runs the dashboard with production settings.
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename=f'logs/dashboard_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dashboard.simple_dashboard import create_simple_dashboard

def main():
    """Start the production dashboard."""

    print("=" * 70)
    print("🚀 STARTING PRODUCTION BI DASHBOARD")
    print("=" * 70)
    print()

    # Check for data file
    data_path = os.getenv('DASHBOARD_DATA_PATH', 'data/raw/square_sales.csv')

    if not os.path.exists(data_path):
        print(f"⚠️  Warning: Data file not found at {data_path}")
        print("   Using sample data instead...")
        print("   To use real data:")
        print("   1. Run: python sync_square_daily.py backfill")
        print("   2. Or set DASHBOARD_DATA_PATH environment variable")
        print()
        data_path = None
    else:
        print(f"✅ Data loaded from: {data_path}")

    # Get settings from environment
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')  # 0.0.0.0 for external access
    port = int(os.getenv('DASHBOARD_PORT', '8050'))
    debug = os.getenv('DASHBOARD_DEBUG', 'False').lower() == 'true'

    print(f"📊 Dashboard URL: http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print()

    logging.info(f"Starting dashboard on {host}:{port}")

    try:
        # Create and run dashboard
        dashboard = create_simple_dashboard(data_path)
        dashboard.run(host=host, port=port, debug=debug)

    except Exception as e:
        logging.error(f"Dashboard failed to start: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
