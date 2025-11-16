#!/usr/bin/env python3
"""
Full Data Sync Pipeline
Syncs Square data → PostgreSQL → Trains ML models → Ready for Dashboard

Usage:
    python full_sync.py              # Sync last 90 days
    python full_sync.py --days 180   # Sync last 180 days
    python full_sync.py --all        # Sync all 3 years
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

print("=" * 80)
print("🔄 FULL DATA SYNC PIPELINE")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Parse arguments
days = 90
if '--all' in sys.argv:
    days_arg = '--all'
elif '--days' in sys.argv:
    idx = sys.argv.index('--days')
    days = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 90
    days_arg = f'--days {days}'
else:
    days_arg = f'--days {days}'

# Step 1: Sync Square → PostgreSQL
print("=" * 80)
print("STEP 1: SYNCING SQUARE DATA → POSTGRESQL")
print("=" * 80)
print()

try:
    result = subprocess.run(
        f'python scripts/sync_square_to_postgres.py {days_arg}',
        shell=True,
        check=True,
        cwd=Path(__file__).parent
    )
    print()
    print("✅ Step 1 Complete: Data synced to PostgreSQL")
    print()
except subprocess.CalledProcessError as e:
    print()
    print(f"❌ Step 1 Failed: Square sync error")
    print(f"   Error code: {e.returncode}")
    print()
    print("Possible issues:")
    print("  - Square API credentials not configured")
    print("  - Network connectivity issue")
    print("  - Database connection error")
    print()
    sys.exit(1)

# Step 2: Train ML Models
print("=" * 80)
print("STEP 2: TRAINING ML MODELS")
print("=" * 80)
print()

try:
    result = subprocess.run(
        'python train_ml_models.py',
        shell=True,
        check=True,
        cwd=Path(__file__).parent
    )
    print()
    print("✅ Step 2 Complete: ML models trained and predictions saved")
    print()
except subprocess.CalledProcessError as e:
    print()
    print(f"❌ Step 2 Failed: ML training error")
    print(f"   Error code: {e.returncode}")
    print()
    print("Note: Data sync completed successfully. You can:")
    print("  - View existing data in dashboard")
    print("  - Re-run training later: python train_ml_models.py")
    print()
    sys.exit(1)

# Success!
print("=" * 80)
print("✅ FULL SYNC COMPLETE!")
print("=" * 80)
print()
print("📊 Your database is now fully synced and predictions are fresh!")
print()
print("Next steps:")
print("  1. python run_dashboard.py    # Launch dashboard")
print("  2. Open http://localhost:8050")
print()
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
