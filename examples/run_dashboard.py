"""
Example: Launch the interactive BI dashboard.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dashboard.app import create_dashboard


def main():
    """Launch the interactive dashboard."""

    print("=" * 70)
    print("LAUNCHING INTERACTIVE BI DASHBOARD")
    print("=" * 70)
    print()
    print("Features:")
    print("  📊 Real-time sales analytics")
    print("  📈 ML-powered forecasts")
    print("  👥 Customer segmentation")
    print("  🔮 Predictive insights")
    print("  📦 Inventory recommendations")
    print()
    print("=" * 70)

    # Create dashboard with sample data
    # To use your own data, pass the CSV path:
    # dashboard = create_dashboard('data/raw/your_sales.csv')

    dashboard = create_dashboard()

    # Run the server
    print("\n🚀 Starting server...")
    print("📱 Dashboard will open in your browser automatically")
    print("⏹️  Press Ctrl+C to stop the server")
    print()

    dashboard.run(host='127.0.0.1', port=8050, debug=True)


if __name__ == "__main__":
    main()
