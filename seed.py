"""
Seed script for warehouse replenishment app.

Usage:
    FLASK_APP=warehouse_app:create_app python seed.py

Loads real product data from:
  - Historical Sales Orders 0107 - 0309.csv
  - Historical Sales Orders 0310 - 0319.csv
  - Store Max Items.xlsx (par levels)

Environment variables:
    SEED_ADMIN_PASSWORD     - Admin user password (default: admin123)
    SEED_WAREHOUSE_PASSWORD - Warehouse user password (default: warehouse123)
"""
import csv
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import openpyxl

from warehouse_app import create_app
from warehouse_app.extensions import db
from warehouse_app.models.user import User
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine

from config.products import PRODUCT_ALIASES, OBSOLETE_PRODUCTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Store definitions ─────────────────────────────────────
STORES = [
    {'name': 'Gardena', 'code': 'GARDENA', 'address': '1234 W Gardena Blvd, Gardena, CA 90247',
     'delivery_schedule': 'daily'},
    {'name': 'K-Town', 'code': 'KTOWN', 'address': '5678 Wilshire Blvd, Los Angeles, CA 90036',
     'delivery_schedule': 'daily'},
]

# Map store names in CSV -> store codes in DB
STORE_NAME_MAP = {
    'Gardena': 'GARDENA',
    'KTOWN': 'KTOWN',
    'K-Town': 'KTOWN',
}

# Product categories inferred from the Excel "Product Group" and common sense
CATEGORY_MAP = {
    '2% Milk': 'Dairy', 'Whole Milk': 'Dairy', 'Half & Half': 'Dairy',
    'Oat Milk': 'Dairy', 'Almond Milk': 'Dairy', 'Condensed Milk': 'Dairy',
    'Ube Condensed Milk': 'Dairy',
    'Espresso Beans': 'Coffee', 'Decaf Beans': 'Coffee', 'Sanchez (retail)': 'Coffee',
    'Mirado (retail)': 'Coffee', 'Supremo (retail)': 'Coffee',
    'Coldbrew Concentrate': 'Coffee', 'Cold Brew Beans': 'Coffee',
    'Vanilla Syrup': 'Syrups', 'Caramel': 'Syrups', 'Dulce': 'Syrups',
    'Mocha': 'Syrups', 'Honey': 'Syrups', 'Rose': 'Syrups',
    'Lavender': 'Syrups', 'Musco Syrup': 'Syrups', 'Agave Cases': 'Syrups',
    'Chai': 'Beverages', 'Tonic Water': 'Beverages',
    'M1200 Matcha': 'Powders', 'Soyo Matcha': 'Powders',
    'Cinnamon Powder': 'Powders', 'Cocoa Box': 'Powders',
    'Matcha Drizzle': 'Powders', 'Buttercream': 'Powders', 'Vienna Cream': 'Powders',
    'CS Vienna Cream': 'Powders',
    'Passionfruit Puree': 'Purees', 'Passionfruit': 'Purees',
    'Strawberry Puree Cases': 'Purees', 'Strawberry Puree': 'Purees',
    'Sugar Tub': 'Sweeteners', 'Sugar in the raw': 'Sweeteners',
    'Tea Bag': 'Tea', 'Jasmine Tea Bag': 'Tea', 'Jasmine Tea': 'Tea',
    'Scarlet Tea': 'Tea', 'Early Grey Tea Bag': 'Tea', 'Mint Tea Bag': 'Tea',
    '10oz Hot Cup': 'Supplies', '8oz Hot Cup': 'Supplies',
    'Hot Lid': 'Supplies', 'Ice lid': 'Supplies', 'Ice Cups': 'Supplies',
    'Custom Ice Cups': 'Supplies', 'Cup Carriers': 'Supplies',
    'Cup Sleeves - Red': 'Supplies', 'Cup Sleeves - Green': 'Supplies',
    'Cup Sleeves': 'Supplies',
    'Black Straws': 'Supplies', 'Wooden Stir Stick': 'Supplies',
    'Lid Plug': 'Supplies', 'Beverage Napkin': 'Supplies',
    'Paper Bag': 'Supplies', 'Pastry Bag, Brown': 'Supplies',
    'Pasty Bag, Brown': 'Supplies',
    'Receipt rolls': 'Supplies', 'Forks': 'Supplies',
    '2 Cup Carrier': 'Supplies', 'Custom 2 Cup Carrier Bag': 'Supplies',
    'Custom 4 Cup Carrier Bag': 'Supplies',
    'Paper 2 Cup Carrier Bag': 'Supplies',
    'Paper 4 Cup Carrier Bag - Tamper Resistant': 'Supplies',
    'Bleach': 'Cleaning', 'Dish Detergent': 'Cleaning',
    'Hand Soap': 'Cleaning', 'Toilet Paper': 'Cleaning',
    'Toilet Solution': 'Cleaning', 'Paper Towel': 'Cleaning',
    'Black Trash Bag': 'Cleaning', 'Espresso Trash Bag': 'Cleaning',
    'Nitrile Gloves': 'Cleaning', 'Floor Cleaner': 'Cleaning',
    'Sanitizing solution': 'Cleaning', 'Toilet cover': 'Cleaning',
    'Rinza': 'Equipment', 'Cafiza': 'Equipment', 'Tumblers': 'Equipment',
    'Splenda': 'Sweeteners',
    'Pour Over Filter': 'Supplies', 'Sponge': 'Cleaning',
    'Dish gloves': 'Cleaning', 'Bottle Brush': 'Cleaning',
    'White trash bag': 'Cleaning',
}


def _normalize(name):
    """Apply alias mapping to normalize a product name."""
    return PRODUCT_ALIASES.get(name, name)


def _make_sku(name):
    """Generate a SKU from a product name."""
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').upper()
    return clean


def _parse_date_mdy(s):
    """Parse M/D/YYYY date string."""
    try:
        return datetime.strptime(s.strip(), '%m/%d/%Y').date()
    except ValueError:
        return None


def _load_old_csv():
    """Load Historical Sales Orders 0107 - 0309.csv.
    Returns list of (store_code, product_name, order_date, quantity)."""
    path = os.path.join(BASE_DIR, 'Historical Sales Orders 0107 - 0309.csv')
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            customer = row['CustomerName'].strip()
            product = row['ProductDescription'].strip()
            date_str = row['OrderDate'].strip()
            qty_str = row['OrderQuantity'].strip()

            if not product or not customer:
                continue

            store_code = STORE_NAME_MAP.get(customer)
            if not store_code:
                continue

            order_date = _parse_date_mdy(date_str)
            if not order_date:
                continue

            try:
                qty = float(qty_str)
            except (ValueError, TypeError):
                continue

            product = _normalize(product)
            rows.append((store_code, product, order_date, qty))
    return rows


def _load_new_csv():
    """Load Historical Sales Orders 0310 - 0319.csv.
    Returns list of (store_code, product_name, order_date, quantity)."""
    path = os.path.join(BASE_DIR, 'Historical Sales Orders 0310 - 0319.csv')
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        # Skip the title row ("Sales Enquiry as of ...")
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            customer = row['Customer'].strip()
            product = row['Product'].strip()
            date_str = row['Order Date'].strip()
            qty_str = row['Quantity'].strip()

            if not product or not customer:
                continue

            store_code = STORE_NAME_MAP.get(customer)
            if not store_code:
                continue

            order_date = _parse_date_mdy(date_str)
            if not order_date:
                continue

            try:
                qty = float(qty_str)
            except (ValueError, TypeError):
                continue

            product = _normalize(product)
            rows.append((store_code, product, order_date, qty))
    return rows


def _load_par_levels():
    """Load par levels from Store Max Items.xlsx.
    Returns dict: {(store_code, canonical_product_name): max_quantity}."""
    path = os.path.join(BASE_DIR, 'Store Max Items.xlsx')
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    pars = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        store_name, product, max_qty = row
        if not product or not store_name:
            continue
        store_code = STORE_NAME_MAP.get(store_name.strip(), store_name.strip().upper())
        product = _normalize(product.strip())
        try:
            max_qty = float(max_qty)
        except (ValueError, TypeError):
            continue
        pars[(store_code, product)] = max_qty
    wb.close()
    return pars


def seed():
    app = create_app()
    with app.app_context():
        print("Clearing existing data...")
        ReplenishmentPlanLine.query.delete()
        ReplenishmentPlan.query.delete()
        InventorySnapshot.query.delete()
        DailyUsage.query.delete()
        StoreItemSetting.query.delete()
        InventoryItem.query.delete()
        Store.query.delete()
        User.query.delete()
        db.session.commit()

        # ── Users ──────────────────────────────────────────────
        admin_pw = os.environ.get('SEED_ADMIN_PASSWORD', 'admin123')
        warehouse_pw = os.environ.get('SEED_WAREHOUSE_PASSWORD', 'warehouse123')

        print("Creating users...")
        admin = User(full_name='Admin User', email='admin@yeems.com', role='admin', active=True)
        admin.set_password(admin_pw)

        warehouse_user = User(full_name='Warehouse Worker', email='warehouse@yeems.com', role='warehouse', active=True)
        warehouse_user.set_password(warehouse_pw)

        db.session.add_all([admin, warehouse_user])
        db.session.flush()

        # ── Stores ─────────────────────────────────────────────
        print("Creating stores...")
        store_objs = {}
        for store_def in STORES:
            store = Store(
                name=store_def['name'],
                code=store_def['code'],
                address=store_def['address'],
                delivery_schedule=store_def['delivery_schedule'],
                active=True,
            )
            db.session.add(store)
            db.session.flush()
            store_objs[store_def['code']] = store

        # ── Load raw data ─────────────────────────────────────
        print("Loading sales order CSVs...")
        old_rows = _load_old_csv()
        new_rows = _load_new_csv()
        all_rows = old_rows + new_rows
        print(f"  Old CSV: {len(old_rows)} order lines")
        print(f"  New CSV: {len(new_rows)} order lines")

        print("Loading par levels from Excel...")
        par_levels = _load_par_levels()
        print(f"  {len(par_levels)} par level entries")

        # ── Discover all unique products ──────────────────────
        all_product_names = set()
        for _, product, _, _ in all_rows:
            all_product_names.add(product)
        # Also include products from par levels that may not appear in sales
        for (_, product) in par_levels:
            all_product_names.add(product)

        # Remove empty strings and obsolete products
        all_product_names.discard('')
        all_product_names -= OBSOLETE_PRODUCTS

        print(f"\nTotal unique products: {len(all_product_names)}")

        # ── Create Inventory Items ────────────────────────────
        print("Creating inventory items...")
        item_objs = {}
        for name in sorted(all_product_names):
            sku = _make_sku(name)
            category = CATEGORY_MAP.get(name, 'Other')
            item = InventoryItem(
                item_name=name,
                sku=sku,
                category=category,
                unit_of_measure='each',
                case_pack_quantity=1,
                storage_type='dry',
                active=True,
            )
            db.session.add(item)
            item_objs[name] = item
        db.session.flush()
        print(f"  Created {len(item_objs)} items")

        # ── Aggregate daily usage from sales orders ───────────
        # Sum quantities per (store, product, date)
        print("Aggregating daily usage from sales orders...")
        daily_agg = defaultdict(float)
        for store_code, product, order_date, qty in all_rows:
            daily_agg[(store_code, product, order_date)] += qty

        usage_count = 0
        for (store_code, product, usage_date), total_qty in daily_agg.items():
            store = store_objs.get(store_code)
            item = item_objs.get(product)
            if not store or not item:
                continue

            db.session.add(DailyUsage(
                store_id=store.id,
                item_id=item.id,
                usage_date=usage_date,
                quantity_used=total_qty,
                source='sales_order_csv',
            ))
            usage_count += 1

        db.session.flush()
        print(f"  Created {usage_count} daily usage records")

        # ── Store Item Settings (par levels) ──────────────────
        print("Creating store item settings with par levels...")
        settings_count = 0
        # Create settings for every store-item combo
        for name, item in item_objs.items():
            for code, store in store_objs.items():
                par = par_levels.get((code, name), 0)
                setting = StoreItemSetting(
                    store_id=store.id,
                    item_id=item.id,
                    par_level=par,
                    safety_stock=0,
                    reorder_threshold=0,
                    min_send_quantity=0,
                    rounding_rule='none',
                    active=True,
                )
                db.session.add(setting)
                settings_count += 1

        db.session.flush()
        print(f"  Created {settings_count} store item settings")

        # ── Summary of par levels ─────────────────────────────
        items_with_par = 0
        items_without_par = 0
        for name, item in item_objs.items():
            has_par = False
            for code in store_objs:
                if par_levels.get((code, name), 0) > 0:
                    has_par = True
                    break
            if has_par:
                items_with_par += 1
            else:
                items_without_par += 1

        print(f"\n  Items with par levels: {items_with_par}")
        print(f"  Items needing par levels: {items_without_par}")
        if items_without_par > 0:
            print("  Products needing par levels:")
            for name in sorted(item_objs):
                has_par = False
                for code in store_objs:
                    if par_levels.get((code, name), 0) > 0:
                        has_par = True
                        break
                if not has_par:
                    print(f"    - {name}")

        db.session.commit()

        print(f"\nSeed complete!")
        print(f"  Users: {User.query.count()}")
        print(f"  Stores: {Store.query.count()}")
        print(f"  Items: {InventoryItem.query.count()}")
        print(f"  Store Item Settings: {StoreItemSetting.query.count()}")
        print(f"  Daily Usage Records: {DailyUsage.query.count()}")
        print(f"\nLogin credentials:")
        print(f"  Admin: admin@yeems.com / {admin_pw}")
        print(f"  Warehouse: warehouse@yeems.com / {warehouse_pw}")


if __name__ == '__main__':
    seed()
