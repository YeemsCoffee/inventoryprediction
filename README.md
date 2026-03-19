# Warehouse Replenishment App

A Flask web application for managing daily warehouse-to-store replenishment for a multi-location coffee shop business. The system calculates how much of each item to send to each store based on usage history, current inventory levels, and configurable par levels.

## Features

- **Dashboard** — Plan overview with visual progress bar, status cards, and store delivery links
- **Plan Generation** — Rules-based recommendation engine with confidence levels and warning flags
- **Master Pick List** — Aggregated warehouse pick view with category/search filters and per-store breakdowns
- **Store Delivery Sheets** — Per-store item lists with inline AJAX status updates (pick, load, deliver, short)
- **Exceptions Screen** — Shorted lines, low-confidence items, and warning flag summary
- **Activity Log** — Audit trail of all fulfillment actions
- **Fulfillment API** — JSON endpoints for single-line and bulk status updates
- **Admin Panel** — CRUD for stores, inventory items, and store-item settings (par levels, safety stock, rounding rules)
- **Data Entry** — Manual entry and CSV import for daily usage and inventory snapshots
- **Role-Based Access** — Admin and warehouse roles with appropriate permissions
- **Print-Optimized** — Clean print layouts for pick lists and delivery sheets

## Tech Stack

- Python 3.11+, Flask 3.1, SQLAlchemy, Flask-Migrate (Alembic)
- SQLite (development) / PostgreSQL (production)
- Server-rendered HTML with vanilla JavaScript for AJAX updates
- pytest for testing (202 tests)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the database
flask --app "warehouse_app:create_app" db upgrade

# Seed demo data
python seed.py

# Run the development server
flask --app "warehouse_app:create_app" run --debug
```

Open http://localhost:5000 and log in:

| Role      | Email                  | Password      |
|-----------|------------------------|---------------|
| Admin     | admin@yeems.com        | admin123      |
| Warehouse | warehouse@yeems.com    | warehouse123  |

Passwords are configurable via `ADMIN_PASSWORD` and `WAREHOUSE_PASSWORD` environment variables.

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
warehouse_app/
├── __init__.py              # App factory with logging and error handlers
├── config.py                # Dev/Test/Prod configs + engine constants
├── extensions.py            # SQLAlchemy, Migrate, Login, CSRF
├── auth_helpers.py          # admin_required decorator
├── models/
│   ├── user.py              # User with last_login_at tracking
│   ├── store.py             # Store with address and delivery schedule
│   ├── inventory_item.py    # Item with description and storage type
│   ├── store_item_setting.py # Per-store-item settings (par, safety, rounding)
│   ├── daily_usage.py       # Daily usage records
│   ├── inventory_snapshot.py # On-hand inventory snapshots
│   ├── replenishment_plan.py # Plan header
│   ├── replenishment_plan_line.py # Plan lines with forecast metadata
│   └── audit_log.py         # Change audit trail
├── services/
│   ├── forecasting.py       # Pure demand forecasting (avg daily usage)
│   ├── replenishment.py     # Business rules (par, safety stock, rounding)
│   ├── recommendation.py    # Backward-compatible re-export wrapper
│   ├── plan_generation.py   # Plan orchestration
│   ├── fulfillment.py       # Status update logic
│   ├── csv_import.py        # CSV import with validation
│   └── audit.py             # Audit log helper
├── blueprints/
│   ├── auth/                # Login/logout
│   ├── dashboard/           # Main dashboard with progress bar
│   ├── plans/               # Plan generation with confirmation
│   ├── warehouse/           # Pick list, delivery sheets, exceptions, API
│   ├── admin/               # Store/item/setting CRUD
│   └── data_entry/          # Usage & snapshot entry + CSV import
├── templates/               # Jinja2 templates
└── static/
    ├── css/style.css         # Responsive, print-optimized CSS
    └── js/app.js             # Toast notifications, UI helpers
```

## Architecture

### 3-Layer Service Separation

```
forecasting.py          → Pure demand forecasting (data → forecast)
replenishment.py        → Business rules (forecast → recommendation)
plan_generation.py      → Orchestration (recommendation → plan lines)
fulfillment.py          → Execution (plan lines → status updates)
```

Each layer has a single responsibility and takes primitives (store_id, item_id, date) rather than model objects, making them independently testable.

### Forecasting Engine

The forecasting service (`services/forecasting.py`) uses a transparent, rules-based approach:

1. **Calculate average daily usage** — Short window (7-day) for high confidence, long window (14-day) fallback
2. **Get current on-hand** — Latest inventory snapshot before plan date
3. **Assess confidence** — Based on data point count and snapshot availability

Per-item `usage_window_days` overrides are supported via store-item settings.

### Replenishment Rules

The replenishment service (`services/replenishment.py`) applies business rules:

1. **Set target** — max(par_level, forecast + safety_stock)
2. **Compute needed** — target - on_hand (floored at 0)
3. **Apply min send** — Raise to min_send_quantity if below threshold
4. **Apply rounding** — None, round up to integer, or round up to case pack
5. **Flag anomalies** — Unusual recommendations (>2x par), missing data, sparse history

### Forecast Metadata Persistence

Each plan line stores the forecast inputs that generated it:
- `forecast_method` — Algorithm used (currently `simple_average`)
- `forecast_avg_daily_usage` — Calculated daily demand
- `forecast_on_hand` — On-hand quantity at generation time
- `forecast_target` — Calculated target level
- `forecast_window_days` — Usage window used

This provides full audit transparency and enables future A/B testing of forecast methods.

### Future Extension Points

The architecture is designed for incremental enhancement:

| Extension | Where | How |
|-----------|-------|-----|
| **Weighted average** | `forecasting.py` | Branch on `FORECAST_METHOD` config, add `weighted_average` strategy |
| **ML model** | `forecasting.py` | Add `ml_model` strategy that calls a prediction service |
| **Forecast persistence** | `forecast_method` column | Already tracked per plan line for comparison |
| **Day-of-week weighting** | `forecasting.py` | Extend `get_average_usage()` with weekday weights |
| **Seasonality** | `forecasting.py` | Add seasonal multiplier before returning forecast |
| **External data** | `forecasting.py` | Add weather/event factors as forecast adjustments |

The `FORECAST_METHOD` config constant (`simple_average` in V1) allows switching strategies without changing the replenishment or plan generation layers.

## Configuration

Key constants in `config.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `FORECAST_METHOD` | `simple_average` | Forecasting algorithm |
| `DEFAULT_USAGE_WINDOW_SHORT` | 7 | Short-term average window (days) |
| `DEFAULT_USAGE_WINDOW_LONG` | 14 | Long-term fallback window (days) |
| `MIN_DATA_POINTS_HIGH_CONFIDENCE` | 5 | Minimum data points for high confidence |
| `CSV_MAX_ROWS` | 10000 | Max rows per CSV import |
| `CSV_MAX_QUANTITY` | 999999 | Max quantity value |
| `BULK_UPDATE_MAX_LINES` | 500 | Max lines per bulk status update |

## API Endpoints

| Method | Endpoint                      | Description                    |
|--------|-------------------------------|--------------------------------|
| POST   | `/warehouse/api/update-line`  | Update single line (status, qty, note) |
| POST   | `/warehouse/api/bulk-update`  | Bulk update line statuses      |

Both accept JSON, are CSRF-exempt, and return `{"success": true, ...}` or `{"error": "..."}`.

### Example: Update a line

```json
POST /warehouse/api/update-line
{"line_id": 42, "status": "picked", "actual_quantity": 8.0, "picker_note": "Grabbed from back"}
```

### Example: Bulk update

```json
POST /warehouse/api/bulk-update
{"line_ids": [42, 43, 44], "status": "loaded"}
```

## Validation

Input validation is applied at multiple layers:

- **Routes** — Type checking, length limits, status validation, NaN/Infinity rejection
- **Services** — Business rule validation, status enum enforcement, note truncation
- **Database** — CHECK constraints on status, confidence, quantity ranges; unique constraints
- **CSV Import** — Row limits, date format parsing, future date rejection, quantity bounds

## License

Proprietary — Yeems Coffee internal use.
