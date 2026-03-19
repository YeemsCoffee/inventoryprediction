"""Tests for Phase 1E: validation hardening, architecture readiness, final cleanup."""
import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.fulfillment import VALID_STATUSES


# ── CSV import hardening ─────────────────────────────────────────────

class TestCSVImportHardening:
    """Tests for CSV import fixes: off-by-one, NaN/Infinity."""

    def test_nan_quantity_rejected(self, app, db, sample_stores, sample_items):
        from warehouse_app.services.csv_import import import_daily_usage_csv
        csv_content = (
            "store_code,sku,usage_date,quantity_used\n"
            f"GARDENA,MILK-WHL,{date.today() - timedelta(days=1)},nan\n"
        )
        with app.app_context():
            result = import_daily_usage_csv(csv_content)
        assert result['imported'] == 0
        assert result['skipped'] == 1
        assert any('Invalid quantity' in e for e in result['errors'])

    def test_infinity_quantity_rejected(self, app, db, sample_stores, sample_items):
        from warehouse_app.services.csv_import import import_daily_usage_csv
        csv_content = (
            "store_code,sku,usage_date,quantity_used\n"
            f"GARDENA,MILK-WHL,{date.today() - timedelta(days=1)},inf\n"
        )
        with app.app_context():
            result = import_daily_usage_csv(csv_content)
        assert result['imported'] == 0
        assert result['skipped'] == 1

    def test_snapshot_nan_rejected(self, app, db, sample_stores, sample_items):
        from warehouse_app.services.csv_import import import_inventory_snapshot_csv
        csv_content = (
            "store_code,sku,snapshot_date,quantity_on_hand\n"
            f"GARDENA,MILK-WHL,{date.today() - timedelta(days=1)},nan\n"
        )
        with app.app_context():
            result = import_inventory_snapshot_csv(csv_content)
        assert result['imported'] == 0
        assert result['skipped'] == 1

    def test_row_limit_exact(self, app, db, sample_stores, sample_items):
        """Row limit should be exact — not off-by-one."""
        from warehouse_app.services.csv_import import import_daily_usage_csv
        yesterday = date.today() - timedelta(days=1)
        # Build CSV with 5 rows, set limit to 3
        lines = ["store_code,sku,usage_date,quantity_used"]
        for i in range(5):
            lines.append(f"GARDENA,MILK-WHL,{yesterday},{i + 1}")
        csv_content = "\n".join(lines) + "\n"

        with app.app_context():
            app.config['CSV_MAX_ROWS'] = 3
            result = import_daily_usage_csv(csv_content)
            app.config['CSV_MAX_ROWS'] = 10000  # restore

        # Should import exactly 3, then stop
        assert result['imported'] == 3
        assert any('limit' in e.lower() for e in result['errors'])


# ── Warehouse API status validation ──────────────────────────────────

class TestAPIStatusValidation:
    """Status is validated before service call to prevent unnecessary work."""

    def test_update_line_invalid_status_early_rejection(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'BOGUS'})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'Invalid status' in data['error']
        assert 'pending' in data['error']  # lists valid statuses

    def test_bulk_update_invalid_status_early_rejection(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': [line.id], 'status': 'BOGUS'})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'Invalid status' in data['error']

    def test_update_line_nan_quantity_rejected(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': float('nan')})
        assert resp.status_code == 400

    def test_update_line_infinity_quantity_rejected(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': float('inf')})
        assert resp.status_code == 400


# ── Admin route validation hardening ─────────────────────────────────

class TestAdminValidationHardening:
    """Tests for new validation rules in admin routes."""

    def test_store_name_too_long(self, admin_client, db):
        resp = admin_client.post('/admin/stores/new', data={
            'name': 'A' * 201,
            'code': 'TEST',
            'active': 'on',
        }, follow_redirects=True)
        assert b'200 characters or fewer' in resp.data

    def test_store_code_too_long(self, admin_client, db):
        resp = admin_client.post('/admin/stores/new', data={
            'name': 'Test Store',
            'code': 'A' * 51,
            'active': 'on',
        }, follow_redirects=True)
        assert b'50 or fewer' in resp.data

    def test_item_name_too_long(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': 'B' * 201,
            'sku': 'TEST-SKU',
            'category': 'Test',
            'unit_of_measure': 'each',
            'case_pack_quantity': '1',
            'active': 'on',
        }, follow_redirects=True)
        assert b'200 characters or fewer' in resp.data

    def test_item_sku_too_long(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': 'Test Item',
            'sku': 'S' * 51,
            'category': 'Test',
            'unit_of_measure': 'each',
            'case_pack_quantity': '1',
            'active': 'on',
        }, follow_redirects=True)
        assert b'50 or fewer' in resp.data

    def test_setting_negative_par_level(self, admin_client, sample_stores, sample_items, db):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id,
            'item_id': sample_items[0].id,
            'par_level': '-5',
            'safety_stock': '0',
            'reorder_threshold': '0',
            'min_send_quantity': '0',
            'rounding_rule': 'none',
            'active': 'on',
        }, follow_redirects=True)
        assert b'non-negative' in resp.data

    def test_setting_negative_safety_stock(self, admin_client, sample_stores, sample_items, db):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id,
            'item_id': sample_items[0].id,
            'par_level': '10',
            'safety_stock': '-2',
            'reorder_threshold': '0',
            'min_send_quantity': '0',
            'rounding_rule': 'none',
            'active': 'on',
        }, follow_redirects=True)
        assert b'non-negative' in resp.data


# ── Data entry validation hardening ──────────────────────────────────

class TestDataEntryHardening:
    """Tests for quantity bounds in manual data entry."""

    def test_daily_usage_excessive_quantity(self, admin_client, sample_stores, sample_items, db):
        resp = admin_client.post('/data/daily-usage', data={
            'store_id': sample_stores[0].id,
            'item_id': sample_items[0].id,
            'usage_date': date.today().isoformat(),
            'quantity_used': '1000001',
        }, follow_redirects=True)
        assert b'max 999,999' in resp.data

    def test_snapshot_excessive_quantity(self, admin_client, sample_stores, sample_items, db):
        resp = admin_client.post('/data/inventory-snapshots', data={
            'store_id': sample_stores[0].id,
            'item_id': sample_items[0].id,
            'snapshot_date': date.today().isoformat(),
            'quantity_on_hand': '1000001',
        }, follow_redirects=True)
        assert b'max 999,999' in resp.data


# ── Forecast method architecture ─────────────────────────────────────

class TestForecastMethodArchitecture:
    """Tests for forecast_method field and config."""

    def test_forecast_method_in_config(self, app):
        with app.app_context():
            method = app.config.get('FORECAST_METHOD')
            assert method == 'simple_average'

    def test_forecast_method_in_build_forecast(self, app, db, sample_stores, sample_items,
                                                sample_settings, sample_usage, sample_snapshots):
        from warehouse_app.services.forecasting import build_forecast
        with app.app_context():
            forecast = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
            assert forecast['forecast_method'] == 'simple_average'

    def test_forecast_method_in_recommendation(self, app, db, sample_stores, sample_items,
                                                sample_settings, sample_usage, sample_snapshots):
        from warehouse_app.services.replenishment import calculate_recommendation
        with app.app_context():
            rec = calculate_recommendation(sample_stores[0].id, sample_items[0].id, date.today())
            assert rec['forecast_method'] == 'simple_average'

    def test_forecast_method_persisted_on_plan_line(self, app, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        assert line.forecast_method == 'simple_average'

    def test_plan_line_has_forecast_metadata(self, app, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        assert line.forecast_avg_daily_usage is not None
        assert line.forecast_on_hand is not None
        assert line.forecast_target is not None
        assert line.forecast_window_days is not None


# ── Fulfillment service hardening ────────────────────────────────────

class TestFulfillmentServiceHardening:
    """Tests for fulfillment service validation improvements."""

    def test_picker_note_truncated_in_service(self, app, sample_plan, db):
        from warehouse_app.services.fulfillment import update_line_status
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        long_note = 'X' * 600
        with app.app_context():
            updated = update_line_status(line.id, picker_note=long_note)
            assert len(updated.picker_note) == 500

    def test_valid_statuses_constant(self):
        assert 'pending' in VALID_STATUSES
        assert 'picked' in VALID_STATUSES
        assert 'loaded' in VALID_STATUSES
        assert 'delivered' in VALID_STATUSES
        assert 'shorted' in VALID_STATUSES


# ── Backward compatibility ───────────────────────────────────────────

class TestBackwardCompatibility:
    """Ensure recommendation.py re-exports still work."""

    def test_recommendation_reexports(self):
        from warehouse_app.services.recommendation import (
            get_average_usage,
            get_latest_on_hand,
            build_forecast,
            apply_rounding,
            calculate_recommendation,
        )
        assert callable(get_average_usage)
        assert callable(get_latest_on_hand)
        assert callable(build_forecast)
        assert callable(apply_rounding)
        assert callable(calculate_recommendation)
