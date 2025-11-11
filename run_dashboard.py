#!/usr/bin/env python3
"""
Entry point script to run the Business Intelligence Dashboard.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dashboard.modern_dashboard import ModernBusinessDashboard

if __name__ == '__main__':
    dashboard = ModernBusinessDashboard()
    dashboard.run()
