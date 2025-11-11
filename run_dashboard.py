#!/usr/bin/env python3
"""
Entry point script to run the Business Intelligence Dashboard.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dashboard.modern_dashboard import ModernDashboard

if __name__ == '__main__':
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables.")
        print("Please make sure your .env file contains DATABASE_URL")
        sys.exit(1)

    # Create and run dashboard
    dashboard = ModernDashboard(database_url=database_url)
    dashboard.run()
