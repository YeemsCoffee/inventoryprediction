"""
CSV import service for daily usage and inventory snapshots.

Validates rows, skips bad data, returns a summary.
"""
import csv
import io
import math
from datetime import date, datetime

from flask import current_app

from warehouse_app.extensions import db
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot


def _get_limit(key, fallback):
    """Read a config value, falling back if outside app context."""
    try:
        return current_app.config.get(key, fallback)
    except RuntimeError:
        return fallback


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


def _validate_csv_headers(reader, required_fields):
    """Check that required headers are present. Returns list of missing fields."""
    if reader.fieldnames is None:
        return required_fields
    actual = {f.strip().lower() for f in reader.fieldnames}
    return [f for f in required_fields if f not in actual]


def import_daily_usage_csv(file_content, source='csv_import'):
    """
    Import daily usage from CSV content.

    Expected columns: store_code, sku, usage_date, quantity_used, notes (optional)

    Returns dict with imported, skipped, errors.
    """
    max_rows = _get_limit('CSV_MAX_ROWS', 10000)
    max_quantity = _get_limit('CSV_MAX_QUANTITY', 999999)
    max_note_len = _get_limit('CSV_MAX_NOTE_LENGTH', 500)

    store_map = _get_store_map()
    item_map = _get_item_map()

    reader = csv.DictReader(io.StringIO(file_content))

    # Validate headers
    missing = _validate_csv_headers(reader, ['store_code', 'sku', 'usage_date', 'quantity_used'])
    if missing:
        return {
            'imported': 0, 'skipped': 0,
            'errors': [f'Missing required columns: {", ".join(missing)}'],
        }

    imported = 0
    skipped = 0
    errors = []

    row_count = 0
    for i, row in enumerate(reader, start=2):  # line 2 = first data row
        if row_count >= max_rows:
            errors.append(f'Row limit of {max_rows} exceeded. Remaining rows skipped.')
            break
        row_count += 1

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

            # Reject future dates
            if usage_date > date.today():
                errors.append(f'Row {i}: Future date "{date_str}" not allowed')
                skipped += 1
                continue

            # Validate quantity
            try:
                quantity = float(qty_str)
                if not math.isfinite(quantity):
                    raise ValueError('non-finite')
                if quantity < 0:
                    raise ValueError('negative')
                if quantity > max_quantity:
                    raise ValueError('too large')
            except (ValueError, TypeError):
                errors.append(f'Row {i}: Invalid quantity "{qty_str}"')
                skipped += 1
                continue

            # Truncate notes
            if notes and len(notes) > max_note_len:
                notes = notes[:max_note_len]

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
    max_rows = _get_limit('CSV_MAX_ROWS', 10000)
    max_quantity = _get_limit('CSV_MAX_QUANTITY', 999999)
    max_note_len = _get_limit('CSV_MAX_NOTE_LENGTH', 500)

    store_map = _get_store_map()
    item_map = _get_item_map()

    reader = csv.DictReader(io.StringIO(file_content))

    # Validate headers
    missing = _validate_csv_headers(reader, ['store_code', 'sku', 'snapshot_date', 'quantity_on_hand'])
    if missing:
        return {
            'imported': 0, 'skipped': 0,
            'errors': [f'Missing required columns: {", ".join(missing)}'],
        }

    imported = 0
    skipped = 0
    errors = []

    row_count = 0
    for i, row in enumerate(reader, start=2):
        if row_count >= max_rows:
            errors.append(f'Row limit of {max_rows} exceeded. Remaining rows skipped.')
            break
        row_count += 1

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

            # Reject future dates
            if snapshot_date > date.today():
                errors.append(f'Row {i}: Future date "{date_str}" not allowed')
                skipped += 1
                continue

            try:
                quantity = float(qty_str)
                if not math.isfinite(quantity):
                    raise ValueError('non-finite')
                if quantity < 0:
                    raise ValueError('negative')
                if quantity > max_quantity:
                    raise ValueError('too large')
            except (ValueError, TypeError):
                errors.append(f'Row {i}: Invalid quantity "{qty_str}"')
                skipped += 1
                continue

            if notes and len(notes) > max_note_len:
                notes = notes[:max_note_len]

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
