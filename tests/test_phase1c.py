"""Tests for Phase 1C: service separation, admin enhancements, forecasting."""
from datetime import date, timedelta
from decimal import Decimal

from warehouse_app.services.forecasting import build_forecast, get_average_usage, get_latest_on_hand
from warehouse_app.services.replenishment import calculate_recommendation, apply_rounding
from warehouse_app.models.store_item_setting import StoreItemSetting


class TestForecastingService:
    """Tests for the separated forecasting service."""

    def test_build_forecast_no_data(self, db, sample_stores, sample_items, sample_settings):
        """With no usage data, forecast should return low confidence."""
        store = sample_stores[0]
        item = sample_items[0]
        forecast = build_forecast(store.id, item.id, date.today())

        assert forecast['confidence'] == 'low'
        assert forecast['avg_daily_usage'] == Decimal('0')
        assert forecast['data_points'] == 0
        assert 'sparse_usage_history' in forecast['warnings']
        assert 'low_confidence' in forecast['warnings']

    def test_build_forecast_with_data(self, db, sample_stores, sample_items,
                                       sample_settings, sample_usage, sample_snapshots):
        """With 7 days of usage and snapshot, forecast should be high confidence."""
        store = sample_stores[0]
        item = sample_items[0]
        forecast = build_forecast(store.id, item.id, date.today())

        assert forecast['confidence'] == 'high'
        assert forecast['avg_daily_usage'] > 0
        assert forecast['data_points'] >= 5
        assert forecast['on_hand'] is not None
        assert forecast['on_hand_date'] is not None
        assert forecast['window_days'] > 0

    def test_build_forecast_missing_snapshot(self, db, sample_stores, sample_items,
                                              sample_settings, sample_usage):
        """Missing snapshot should downgrade confidence and add warning."""
        store = sample_stores[0]
        item = sample_items[0]
        forecast = build_forecast(store.id, item.id, date.today())

        assert forecast['on_hand'] is None
        assert 'missing_snapshot' in forecast['warnings']
        assert forecast['confidence'] in ('medium', 'low')

    def test_build_forecast_respects_usage_window_override(self, db, sample_stores, sample_items):
        """When usage_window_days is set on the setting, it should be used."""
        from warehouse_app.models.daily_usage import DailyUsage

        store = sample_stores[0]
        item = sample_items[0]

        # Create setting with custom 3-day window
        setting = StoreItemSetting(
            store_id=store.id, item_id=item.id,
            par_level=10, safety_stock=2, rounding_rule='none',
            usage_window_days=3, active=True,
        )
        db.session.add(setting)

        # Create 3 days of usage data
        today = date.today()
        for d in range(1, 4):
            db.session.add(DailyUsage(
                store_id=store.id, item_id=item.id,
                usage_date=today - timedelta(days=d),
                quantity_used=10.0, source='test',
            ))
        db.session.commit()

        forecast = build_forecast(store.id, item.id, today)
        # 3 data points in a 3-day window should be high confidence
        assert forecast['window_days'] == 3
        assert forecast['data_points'] == 3

    def test_forecast_explanations_are_populated(self, db, sample_stores, sample_items,
                                                   sample_settings, sample_usage, sample_snapshots):
        """Forecast should include human-readable explanations."""
        store = sample_stores[0]
        item = sample_items[0]
        forecast = build_forecast(store.id, item.id, date.today())

        assert len(forecast['explanations']) > 0
        assert any('average' in e.lower() or 'on-hand' in e.lower()
                    for e in forecast['explanations'])


class TestReplenishmentService:
    """Tests for the separated replenishment service."""

    def test_calculate_recommendation_uses_forecast(self, db, sample_stores, sample_items,
                                                     sample_settings, sample_usage, sample_snapshots):
        """Recommendation should include forecast metadata."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())

        assert 'recommended_quantity' in rec
        assert 'confidence_level' in rec
        assert 'forecast_avg_daily_usage' in rec
        assert 'forecast_on_hand' in rec
        assert 'forecast_target' in rec
        assert 'forecast_window_days' in rec

    def test_replenishment_skips_no_order_history(self, db, sample_stores, sample_items, sample_settings):
        """With no order history, replenishment should return zero (not fabricate demand)."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())

        assert rec['recommended_quantity'] == 0
        assert rec['confidence_level'] == 'low'

    def test_replenishment_applies_rounding(self, db, sample_stores, sample_items,
                                             sample_settings, sample_usage, sample_snapshots):
        """Rounding rules should be applied to recommendation."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())

        # Settings use round_up_case_pack with case_pack=4
        # So recommendation should be divisible by 4
        if rec['recommended_quantity'] > 0:
            assert rec['recommended_quantity'] % 4 == 0

    def test_backward_compatible_imports(self):
        """Old import paths via recommendation.py should still work."""
        from warehouse_app.services.recommendation import (
            calculate_recommendation,
            apply_rounding,
            get_average_usage,
            get_latest_on_hand,
            build_forecast,
        )
        # All functions should be callable
        assert callable(calculate_recommendation)
        assert callable(apply_rounding)
        assert callable(get_average_usage)
        assert callable(get_latest_on_hand)
        assert callable(build_forecast)


class TestServiceSeparation:
    """Tests verifying the three services are properly separated."""

    def test_forecasting_module_exists(self):
        import warehouse_app.services.forecasting
        assert hasattr(warehouse_app.services.forecasting, 'build_forecast')
        assert hasattr(warehouse_app.services.forecasting, 'get_average_usage')
        assert hasattr(warehouse_app.services.forecasting, 'get_latest_on_hand')

    def test_replenishment_module_exists(self):
        import warehouse_app.services.replenishment
        assert hasattr(warehouse_app.services.replenishment, 'calculate_recommendation')
        assert hasattr(warehouse_app.services.replenishment, 'apply_rounding')

    def test_fulfillment_module_exists(self):
        import warehouse_app.services.fulfillment
        assert hasattr(warehouse_app.services.fulfillment, 'update_line_status')
        assert hasattr(warehouse_app.services.fulfillment, 'bulk_update_status')

    def test_plan_generation_uses_replenishment(self):
        """plan_generation should import from replenishment, not recommendation."""
        import inspect
        import warehouse_app.services.plan_generation as pg
        source = inspect.getsource(pg)
        assert 'from warehouse_app.services.replenishment import' in source


class TestAdminScreenEnhancements:
    """Tests for new admin form fields."""

    def test_create_store_with_new_fields(self, admin_client, db):
        resp = admin_client.post('/admin/stores/new', data={
            'name': 'Test Store', 'code': 'TSTST', 'active': 'on',
            'address': '123 Test St', 'delivery_schedule': 'MWF',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Test Store' in resp.data
        assert b'123 Test St' in resp.data
        assert b'MWF' in resp.data

    def test_create_item_with_new_fields(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': 'Test Item', 'sku': 'TST-NEW', 'category': 'Test',
            'description': 'A test item description',
            'unit_of_measure': 'each', 'case_pack_quantity': '6',
            'storage_type': 'refrigerated', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Test Item' in resp.data
        assert b'refrigerated' in resp.data

    def test_create_setting_with_usage_window(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'par_level': '10', 'safety_stock': '2', 'reorder_threshold': '3',
            'min_send_quantity': '2', 'rounding_rule': 'round_up_case_pack',
            'usage_window_days': '5', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200

        setting = StoreItemSetting.query.filter_by(
            store_id=sample_stores[0].id, item_id=sample_items[0].id
        ).first()
        assert setting is not None
        assert setting.usage_window_days == 5

    def test_create_setting_blank_usage_window(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'par_level': '10', 'safety_stock': '2', 'reorder_threshold': '3',
            'min_send_quantity': '2', 'rounding_rule': 'none',
            'usage_window_days': '', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200

        setting = StoreItemSetting.query.filter_by(
            store_id=sample_stores[0].id, item_id=sample_items[0].id
        ).first()
        assert setting is not None
        assert setting.usage_window_days is None

    def test_create_setting_invalid_usage_window(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': str(sample_stores[0].id), 'item_id': str(sample_items[0].id),
            'par_level': '10', 'safety_stock': '2', 'reorder_threshold': '3',
            'min_send_quantity': '2', 'rounding_rule': 'none',
            'usage_window_days': '100', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'between 1 and 90' in resp.data

    def test_stores_list_shows_new_columns(self, admin_client, db):
        from warehouse_app.models.store import Store
        store = Store(name='ColumnTest', code='COLTEST', address='Addr', delivery_schedule='daily', active=True)
        db.session.add(store)
        db.session.commit()
        resp = admin_client.get('/admin/stores')
        assert b'Addr' in resp.data
        assert b'daily' in resp.data

    def test_items_list_shows_storage_type(self, admin_client, db):
        from warehouse_app.models.inventory_item import InventoryItem
        item = InventoryItem(
            item_name='StorageTest', sku='STRG-01', category='Test',
            case_pack_quantity=1, storage_type='frozen', active=True,
        )
        db.session.add(item)
        db.session.commit()
        resp = admin_client.get('/admin/items')
        assert b'frozen' in resp.data
