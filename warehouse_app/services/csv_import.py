"""
CSV import service for daily usage, inventory snapshots, and actual orders.

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
from warehouse_app.models.actual_order import ActualOrder


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


def _get_store_name_map():
    """Return dict mapping store name (uppercased) to store id."""
    stores = Store.query.filter_by(active=True).all()
    return {s.name.upper(): s.id for s in stores}


def _get_item_map():
    """Return dict mapping SKU (uppercased) to item id."""
    items = InventoryItem.query.filter_by(active=True).all()
    return {i.sku.upper(): i.id for i in items}


def _get_item_name_map():
    """Return dict mapping item name (uppercased) to item id."""
    items = InventoryItem.query.filter_by(active=True).all()
    return {i.item_name.upper(): i.id for i in items}


def _is_title_row(line):
    """Return True if a CSV line looks like a title/banner rather than headers.

    Heuristic: a title row has mostly empty trailing fields (commas with no
    content) — e.g. ``"Sales Enquiry as of 03/14/2026,,,,,,,,,,,"``
    """
    stripped = line.strip()
    if not stripped:
        return True
    parts = stripped.split(',')
    if len(parts) <= 1:
        return False
    empty = sum(1 for p in parts if p.strip() == '')
    return empty / len(parts) > 0.5


def _validate_csv_headers(reader, required_fields):
    """Check that required headers are present. Returns list of missing fields."""
    if reader.fieldnames is None:
        return required_fields
    actual = {f.strip().strip('\ufeff').lower() for f in reader.fieldnames}
    return [f for f in required_fields if f.lower() not in actual]


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
            errors.append(f'Row {i}: Unexpected error \u2014 {str(e)}')
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
            errors.append(f'Row {i}: Unexpected error \u2014 {str(e)}')
            skipped += 1

    db.session.commit()
    return {'imported': imported, 'skipped': skipped, 'errors': errors}


def _detect_actual_orders_format(fieldnames):
    """Detect whether CSV uses sales-enquiry or legacy column names.

    Returns a tuple (format, missing) where format is 'sales_enquiry' or
    'legacy', and missing is a list of missing required columns.
    """
    if fieldnames is None:
        return 'legacy', ['store_code', 'sku', 'order_date', 'quantity_ordered']

    actual = {f.strip().strip('\ufeff').lower() for f in fieldnames}

    # Sales enquiry format: Order Date, Customer, Product, Quantity
    sales_required = ['order date', 'customer', 'product', 'quantity']
    sales_missing = [f for f in sales_required if f not in actual]
    if not sales_missing:
        return 'sales_enquiry', []

    # Legacy format: store_code, sku, order_date, quantity_ordered
    legacy_required = ['store_code', 'sku', 'order_date', 'quantity_ordered']
    legacy_missing = [f for f in legacy_required if f not in actual]
    if not legacy_missing:
        return 'legacy', []

    # Neither format matched fully — return whichever has fewer missing
    if len(sales_missing) <= len(legacy_missing):
        return 'sales_enquiry', sales_missing
    return 'legacy', legacy_missing


def import_actual_orders_csv(file_content, source='csv_import'):
    """
    Import actual store orders from CSV content.

    Accepts two CSV formats:

    Sales enquiry format (preferred):
        Order No., Order Date, Required Date, Completed Date, Warehouse,
        Customer, Customer Type, Product, Product Group, Status, Quantity,
        Sub Total

    Legacy format:
        store_code, sku, order_date, quantity_ordered, notes (optional)

    Returns dict with imported, skipped, errors.
    """
    max_rows = _get_limit('CSV_MAX_ROWS', 10000)
    max_quantity = _get_limit('CSV_MAX_QUANTITY', 999999)
    max_note_len = _get_limit('CSV_MAX_NOTE_LENGTH', 500)

    clean_content = file_content.lstrip('\ufeff')

    # Skip title/banner rows that aren't real CSV headers (e.g.
    # "Sales Enquiry as of 03/14/2026,,,,,,,,,,,")
    lines = clean_content.split('\n')
    while lines and _is_title_row(lines[0]):
        lines.pop(0)
    clean_content = '\n'.join(lines)

    dialect = csv.Sniffer().sniff(clean_content[:2048], delimiters=',\t;|')
    reader = csv.DictReader(io.StringIO(clean_content), dialect=dialect)

    fmt, missing = _detect_actual_orders_format(reader.fieldnames)
    if missing:
        return {
            'imported': 0, 'skipped': 0,
            'errors': [f'Missing required columns: {", ".join(missing)}'],
        }

    store_code_map = _get_store_map()
    item_sku_map = _get_item_map()

    if fmt == 'sales_enquiry':
        store_name_map = _get_store_name_map()
        item_name_map = _get_item_name_map()

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
            # Normalise keys to lower-case for consistent lookup
            normalised = {k.strip().strip('\ufeff').lower(): v for k, v in row.items()}

            if fmt == 'sales_enquiry':
                customer = normalised.get('customer', '').strip().upper()
                product = normalised.get('product', '').strip().upper()
                date_str = normalised.get('order date', '').strip()
                qty_str = normalised.get('quantity', '').strip()
                notes = None  # sales enquiry has no notes column
            else:
                customer = normalised.get('store_code', '').strip().upper()
                product = normalised.get('sku', '').strip().upper()
                date_str = normalised.get('order_date', '').strip()
                qty_str = normalised.get('quantity_ordered', '').strip()
                notes = normalised.get('notes', '').strip() or None

            # Resolve store
            if fmt == 'sales_enquiry':
                store_id = store_name_map.get(customer) or store_code_map.get(customer)
            else:
                store_id = store_code_map.get(customer)

            if store_id is None:
                label = 'customer' if fmt == 'sales_enquiry' else 'store code'
                errors.append(f'Row {i}: Unknown {label} "{customer}"')
                skipped += 1
                continue

            # Resolve item — auto-create if missing in sales_enquiry format
            if fmt == 'sales_enquiry':
                item_id = item_name_map.get(product) or item_sku_map.get(product)
                if item_id is None:
                    # Auto-create the item using the product name from the CSV
                    product_original = normalised.get('product', '').strip()
                    category = normalised.get('product group', '').strip() or ''
                    # Generate a SKU from the product name
                    sku = product_original.upper().replace(' ', '-')[:100]
                    new_item = InventoryItem(
                        item_name=product_original,
                        sku=sku,
                        category=category,
                    )
                    db.session.add(new_item)
                    db.session.flush()  # get the new id without committing
                    item_id = new_item.id
                    # Update in-memory maps so later rows in this file find it
                    item_name_map[product] = item_id
                    item_sku_map[sku] = item_id
            else:
                item_id = item_sku_map.get(product)

            if item_id is None:
                errors.append(f'Row {i}: Unknown SKU "{product}"')
                skipped += 1
                continue

            order_date = _parse_date(date_str)
            if order_date is None:
                errors.append(f'Row {i}: Invalid date "{date_str}"')
                skipped += 1
                continue

            if order_date > date.today():
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

            existing = ActualOrder.query.filter_by(
                store_id=store_id, item_id=item_id, order_date=order_date,
            ).first()

            if existing:
                existing.quantity_ordered = quantity
                existing.source = source
                existing.notes = notes
            else:
                db.session.add(ActualOrder(
                    store_id=store_id, item_id=item_id,
                    order_date=order_date, quantity_ordered=quantity,
                    source=source, notes=notes,
                ))
            imported += 1

        except Exception as e:
            errors.append(f'Row {i}: Unexpected error \u2014 {str(e)}')
            skipped += 1

    db.session.commit()
    return {'imported': imported, 'skipped': skipped, 'errors': errors}
