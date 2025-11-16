"""
Diagnostic script to identify and fix None value issues in sync

This helps identify where None values are causing arithmetic errors.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

def test_sync_with_traceback():
    """Run sync with full error traceback"""

    print("=" * 70)
    print("🔍 RUNNING SYNC WITH DETAILED ERROR TRACKING")
    print("=" * 70)
    print()

    try:
        # Import here to catch import errors
        from scripts.sync_square_to_postgres import SquareToPostgresSync

        database_url = os.getenv('DATABASE_URL')
        square_env = os.getenv('SQUARE_ENVIRONMENT', 'production')

        if not database_url:
            print("❌ DATABASE_URL not set in .env file")
            return False

        syncer = SquareToPostgresSync(database_url, square_env)
        syncer.connect()

        # Try with just 1 day first to isolate the issue
        print("🧪 Testing with 1 day of data to isolate issue...")
        print()

        syncer.backfill_historical_data(days_back=1, oldest_first=True)

        print("\n✅ Sync completed successfully!")
        return True

    except TypeError as e:
        print("\n❌ TypeError detected!")
        print(f"Error: {e}")
        print("\n📍 Full traceback:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)
        print()

        # Provide specific guidance based on the error
        error_str = str(e)
        if "unsupported operand type" in error_str and "NoneType" in error_str:
            print("💡 This error occurs when trying to perform arithmetic on None values")
            print()
            print("Common causes:")
            print("  1. Missing/null values in Square API response")
            print("  2. Field that's expected to be numeric is None")
            print("  3. Missing null handling in calculations")
            print()
            print("Check the traceback above to see which line is causing the issue.")

        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\n📍 Full traceback:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)
        return False

if __name__ == "__main__":
    success = test_sync_with_traceback()
    sys.exit(0 if success else 1)
