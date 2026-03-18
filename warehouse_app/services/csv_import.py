"""
CSV import service for daily usage and inventory snapshots.

Validates rows, skips bad data, returns a summary.
"""
import csv
import io
from datetime import date, datetime

from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot


def _parse_date(value):
    """Parse a date from common formats."""
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _get_store_map():
    """Return dict mapping store code (uppercased) to store id."""
    stores = Store.query.filter_by(active=True).all()
    return {s.code.upper(): s.id for s in stores}


def _get_item_map():
    """Return dict mapping SKU (uppercased) to item id."""
    items = InventoryItem.query.filter_by(active=True).all()
    return {i.sku.upper(): i.id for i in items}


def import_daily_usage_csv(file_content, source='csv_import'):
    """
    Import daily usage from CSV content.

    Expected columns: store_code, sku, usage_date, quantity_used, notes (optional)

    Returns dict with imported, skipped, errors.
    """
    store_map = _get_store_map()
    item_map = _get_item_map()

    reader = csv.DictReader(io.StringIO(file_content))
    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):  # line 2 = first data row
        try:
            store_code = row.get('store_code', '').strip().upper()
            sku = row.get('sku', '').strip().upper()
            date_str = row.get('usage_date', '').strip()
            qty_str = row.get('quantity_used', '').strip()
            notes = row.get('notes', '').strip() or None

            # Validate store
            store_id = store_map.get(store_code)
            if store_id is None:
                errors.append(f'Row {i}: Unknown store code "{store_code}"')
                skipped += 1
                continue

            # Validate item
            item_id = item_map.get(sku)
            if item_id is None:
                errors.append(f'Row {i}: Unknown SKU "{sku}"')
                skipped += 1
                continue

            # Validate date
            usage_date = _parse_date(date_str)
            if usage_date is None:
                errors.append(f'Row {i}: Invalid date "{date_str}"')
                skipped += 1
                continue

            # Validate quantity
            try:
                quantity = float(qty_str)
                if quantity < 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(f'Row {i}: Invalid quantity "{qty_str}"')
                skipped += 1
                continue

            # Upsert: update if exists, insert if not
            existing = DailyUsage.query.filter_by(
                store_id=store_id, item_id=item_id, usage_date=usage_date,
            ).first()

            if existing:
                existing.quantity_used = quantity
                existing.source = source
                existing.notes = notes
            else:
                db.session.add(DailyUsage(
                    store_id=store_id, item_id=item_id,
                    usage_date=usage_date, quantity_used=quantity,
                    source=source, notes=notes,
                ))
            imported += 1

        except Exception as e:
            errors.append(f'Row {i}: Unexpected error — {str(e)}')
            skipped += 1

    db.session.commit()
    return {'imported': imported, 'skipped': skipped, 'errors': errors}


def import_inventory_snapshot_csv(file_content, source='csv_import'):
    """
    Import inventory snapshots from CSV content.

    Expected columns: store_code, sku, snapshot_date, quantity_on_hand, notes (optional)

    Returns dict with imported, skipped, errors.
    """
    store_map = _get_store_map()
    item_map = _get_item_map()

    reader = csv.DictReader(io.StringIO(file_content))
    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            store_code = row.get('store_code', '').strip().upper()
            sku = row.get('sku', '').strip().upper()
            date_str = row.get('snapshot_date', '').strip()
            qty_str = row.get('quantity_on_hand', '').strip()
            notes = row.get('notes', '').strip() or None

            store_id = store_map.get(store_code)
            if store_id is None:
                errors.append(f'Row {i}: Unknown store code "{store_code}"')
                skipped += 1
                continue

            item_id = item_map.get(sku)
            if item_id is None:
                errors.append(f'Row {i}: Unknown SKU "{sku}"')
                skipped += 1
                continue

            snapshot_date = _parse_date(date_str)
            if snapshot_date is None:
                errors.append(f'Row {i}: Invalid date "{date_str}"')
                skipped += 1
                continue

            try:
                quantity = float(qty_str)
                if quantity < 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(f'Row {i}: Invalid quantity "{qty_str}"')
                skipped += 1
                continue

            existing = InventorySnapshot.query.filter_by(
                store_id=store_id, item_id=item_id, snapshot_date=snapshot_date,
            ).first()

            if existing:
                existing.quantity_on_hand = quantity
                existing.source = source
                existing.notes = notes
            else:
                db.session.add(InventorySnapshot(
                    store_id=store_id, item_id=item_id,
                    snapshot_date=snapshot_date, quantity_on_hand=quantity,
                    source=source, notes=notes,
                ))
            imported += 1

        except Exception as e:
            errors.append(f'Row {i}: Unexpected error — {str(e)}')
            skipped += 1

    db.session.commit()
    return {'imported': imported, 'skipped': skipped, 'errors': errors}
