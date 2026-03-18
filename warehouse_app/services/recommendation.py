"""
Backward-compatible recommendation API.

This module re-exports the public interfaces from the separated
forecasting and replenishment services so that existing code
(blueprints, tests) continues to work without import changes.

Service separation:
    forecasting.py  — demand forecasting (avg usage, confidence, on-hand)
    replenishment.py — business rules (par level, rounding, min-send)
    fulfillment.py  — execution (status tracking, picker notes)
"""
# Re-export forecasting functions
from warehouse_app.services.forecasting import (  # noqa: F401
    get_average_usage,
    get_latest_on_hand,
    build_forecast,
)

# Re-export replenishment functions
from warehouse_app.services.replenishment import (  # noqa: F401
    apply_rounding,
    calculate_recommendation,
)
