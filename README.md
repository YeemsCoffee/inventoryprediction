# Warehouse Replenishment App

A Flask web application for managing daily warehouse-to-store replenishment for a multi-location coffee shop business. The system calculates how much of each item to send to each store based on usage history, current inventory levels, and configurable par levels.

## Features

- **Dashboard** — Plan overview with status cards, store links, and quick actions
- **Plan Generation** — Rules-based recommendation engine (no ML) with confidence levels and warning flags
- **Master Pick List** — Aggregated warehouse pick view with category/search filters and per-store breakdowns
- **Store Delivery Sheets** — Per-store item lists with inline AJAX status updates (pick, load, deliver, short)
- **Exceptions Screen** — Shorted lines, low-confidence items, and warning flag summary
- **Fulfillment API** — JSON endpoints for single-line and bulk status updates
- **Admin Panel** — CRUD for stores, inventory items, and store-item settings (par levels, safety stock, rounding rules)
- **Data Entry** — Manual entry and CSV import for daily usage and inventory snapshots
- **Role-Based Access** — Admin and warehouse roles with appropriate permissions

## Tech Stack

- Python 3.11+, Flask 3.1, SQLAlchemy, Flask-Migrate (Alembic)
- SQLite (development) / PostgreSQL (production)
- Server-rendered HTML with vanilla JavaScript for AJAX updates
- pytest for testing (100 tests)

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

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
warehouse_app/
├── __init__.py              # App factory
├── config.py                # Dev/Test/Prod configs
├── extensions.py            # SQLAlchemy, Migrate, Login, CSRF
├── auth_helpers.py          # admin_required decorator
├── models/
│   ├── user.py
│   ├── store.py
│   ├── inventory_item.py
│   ├── store_item_setting.py
│   ├── daily_usage.py
│   ├── inventory_snapshot.py
│   ├── replenishment_plan.py
│   └── replenishment_plan_line.py
├── services/
│   ├── recommendation.py    # Rules-based replenishment engine
│   ├── plan_generation.py   # Plan orchestration
│   ├── fulfillment.py       # Status update logic
│   └── csv_import.py        # CSV import for usage/snapshots
├── blueprints/
│   ├── auth/                # Login/logout
│   ├── dashboard/           # Main dashboard
│   ├── plans/               # Plan generation
│   ├── warehouse/           # Pick list, delivery sheets, exceptions, API
│   ├── admin/               # Store/item/setting CRUD
│   └── data_entry/          # Usage & snapshot entry + CSV import
├── templates/               # Jinja2 templates
└── static/                  # CSS, JS
```

## Recommendation Engine

The engine (`services/recommendation.py`) uses a transparent, rules-based approach:

1. **Forecast daily usage** — 7-day average (high confidence), 14-day fallback (medium), or par level (low)
2. **Get current on-hand** — Latest inventory snapshot
3. **Calculate target** — max(par_level, forecast + safety_stock)
4. **Compute needed quantity** — target - on_hand (floored at 0)
5. **Apply minimum send** — Raise to min_send_quantity if below threshold
6. **Apply rounding** — None, round up to integer, or round up to case pack
7. **Flag anomalies** — Unusual recommendations (>2x par), missing data, sparse history

Each line includes a confidence level (high/medium/low), human-readable explanation, and machine-readable warning flags.

## API Endpoints

| Method | Endpoint                      | Description                    |
|--------|-------------------------------|--------------------------------|
| POST   | `/warehouse/api/update-line`  | Update single line (status, qty, note) |
| POST   | `/warehouse/api/bulk-update`  | Bulk update line statuses      |

Both accept JSON and return `{"success": true, ...}` or `{"error": "..."}`.
