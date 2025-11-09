"""
Test Production Setup
Validates that your production environment is ready to deploy.
"""

import os
import sys
from pathlib import Path

def test_environment():
    """Test environment configuration."""
    print("=" * 70)
    print("🧪 TESTING PRODUCTION SETUP")
    print("=" * 70)
    print()

    results = []

    # Test 1: Check .env file
    print("📋 Test 1: Environment Configuration")
    env_path = Path('.env')
    if env_path.exists():
        print("   ✅ .env file exists")
        results.append(True)

        # Read and check for placeholder
        with open(env_path) as f:
            content = f.read()
            if 'your_square_access_token_here' in content:
                print("   ⚠️  Warning: Square token not configured (using placeholder)")
                print("   💡 This is OK - you can use sample data for now")
            else:
                print("   ✅ Square token appears to be configured")
    else:
        print("   ❌ .env file not found")
        results.append(False)
    print()

    # Test 2: Check Python packages
    print("📦 Test 2: Required Packages")
    try:
        import pandas
        import plotly
        import dash
        import sklearn
        import tensorflow
        print("   ✅ All core packages installed")
        results.append(True)
    except ImportError as e:
        print(f"   ❌ Missing package: {e}")
        results.append(False)
    print()

    # Test 3: Check data directory
    print("📁 Test 3: Data Directory Structure")
    data_dir = Path('data/raw')
    if data_dir.exists():
        print("   ✅ data/raw directory exists")

        square_data = data_dir / 'square_sales.csv'
        if square_data.exists():
            print(f"   ✅ Square data file found ({square_data.stat().st_size:,} bytes)")
        else:
            print("   ℹ️  No Square data yet (will use sample data)")
        results.append(True)
    else:
        print("   ❌ data/raw directory missing")
        results.append(False)
    print()

    # Test 4: Try loading the app
    print("🚀 Test 4: Application Import")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.app import CustomerTrendApp
        from src.dashboard.simple_dashboard import create_simple_dashboard
        print("   ✅ Application modules load successfully")
        results.append(True)
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        results.append(False)
    print()

    # Test 5: Test sample data generation
    print("🎲 Test 5: Sample Data Generation")
    try:
        app = CustomerTrendApp()
        app.create_sample_data(n_customers=50, n_transactions=1000)
        print(f"   ✅ Sample data created ({len(app.processed_data):,} transactions)")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Error creating sample data: {e}")
        results.append(False)
    print()

    # Test 6: Test dashboard creation
    print("📊 Test 6: Dashboard Creation")
    try:
        dashboard = create_simple_dashboard()
        print("   ✅ Dashboard created successfully")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Error creating dashboard: {e}")
        results.append(False)
    print()

    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print()
        print("🎉 Your production environment is ready!")
        print()
        print("Next Steps:")
        print("1. Configure Square token in .env (or keep using sample data)")
        print("2. Run: python start_production.py")
        print("3. Access dashboard at: http://localhost:8050")
    else:
        print(f"⚠️  {passed}/{total} TESTS PASSED ({percentage:.0f}%)")
        print()
        print("Please fix the failed tests before deploying to production.")

    print("=" * 70)

    return all(results)


if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)
