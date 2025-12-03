"""
Master setup script for ML pipeline and dashboard integration.
Sets up predictions schema, runs initial TFT forecasts, and prepares dashboard.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import setup_predictions_schema
import run_tft_pipeline


def setup_ml_pipeline():
    """
    Complete ML pipeline setup.

    Steps:
    1. Create predictions schema and tables
    2. Run initial TFT training and forecasting
    3. Save forecasts to RDS
    4. Dashboard ready to display predictions
    """

    print("=" * 70)
    print("🚀 ML PIPELINE SETUP")
    print("=" * 70)
    print()
    print("This will:")
    print("  1️⃣  Create predictions schema in RDS")
    print("  2️⃣  Train Temporal Fusion Transformer (TFT) model")
    print("  3️⃣  Generate 30-day demand forecasts")
    print("  4️⃣  Save forecasts to predictions.demand_forecasts")
    print("  5️⃣  Enable ML predictions in dashboard")
    print()
    print("⚠️  This may take 10-15 minutes on first run")
    print()

    proceed = input("Continue? (y/n): ")
    if proceed.lower() != 'y':
        print("Setup cancelled.")
        return

    print()

    try:
        # Step 1: Setup predictions schema (drop existing for clean setup)
        print("STEP 1/2: Setting up predictions schema...")
        print("=" * 70)
        setup_predictions_schema.setup_predictions_schema(drop_existing=True)
        print()

        # Step 2: Run TFT pipeline
        print("STEP 2/2: Running TFT forecasting pipeline...")
        print("=" * 70)
        run_tft_pipeline.run_tft_pipeline(
            forecast_days=30,
            max_epochs=30,
            batch_size=128,
            save_to_db=True
        )

        print()
        print("=" * 70)
        print("✅ ML PIPELINE SETUP COMPLETE!")
        print("=" * 70)
        print()
        print("🎯 Next Steps:")
        print()
        print("  1. Start your dashboard:")
        print("     python -m src.dashboard.production_dashboard")
        print()
        print("  2. View predictions at:")
        print("     http://localhost:8050")
        print()
        print("  3. Schedule automatic updates (optional):")
        print("     python schedule_tft_updates.py")
        print()
        print("  4. Manually refresh forecasts anytime:")
        print("     python run_tft_pipeline.py")
        print()
        print("=" * 70)

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ SETUP FAILED")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("💡 Troubleshooting:")
        print("  • Make sure your RDS database is accessible")
        print("  • Verify Gold layer data exists: python check_database.py")
        print("  • Check PyTorch is installed: pip install torch pytorch-lightning pytorch-forecasting")
        print()
        raise


if __name__ == "__main__":
    setup_ml_pipeline()
