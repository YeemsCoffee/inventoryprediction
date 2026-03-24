"""Tests for admin routes and data entry routes."""
from datetime import date


class TestAdminRoutes:
    def test_admin_stores(self, admin_client, sample_stores):
        resp = admin_client.get('/admin/stores')
        assert resp.status_code == 200
        assert b'Gardena' in resp.data

    def test_admin_items(self, admin_client, sample_items):
        resp = admin_client.get('/admin/items')
        assert resp.status_code == 200
        assert b'Whole Milk' in resp.data

    def test_admin_settings(self, admin_client, sample_settings):
        resp = admin_client.get('/admin/store-item-settings')
        assert resp.status_code == 200

    def test_create_store(self, admin_client, db):
        resp = admin_client.post('/admin/stores/new', data={
            'name': 'New Store', 'code': 'NEWST', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'New Store' in resp.data

    def test_create_store_missing_name(self, admin_client, db):
        resp = admin_client.post('/admin/stores/new', data={
            'name': '', 'code': 'X',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'required' in resp.data

    def test_create_store_duplicate_code(self, admin_client, sample_stores):
        resp = admin_client.post('/admin/stores/new', data={
            'name': 'Another', 'code': 'GARDENA', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already exists' in resp.data

    def test_edit_store(self, admin_client, sample_stores):
        store = sample_stores[0]
        resp = admin_client.post(f'/admin/stores/{store.id}/edit', data={
            'name': 'Updated Gardena', 'code': 'GARDENA', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Updated Gardena' in resp.data

    def test_create_item(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': 'Chai Tea', 'sku': 'CHAI-01', 'category': 'Tea',
            'unit_of_measure': 'bag', 'case_pack_quantity': '4', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Chai Tea' in resp.data

    def test_create_item_missing_fields(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': '', 'sku': '', 'category': 'X',
            'unit_of_measure': 'x', 'case_pack_quantity': '1',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'required' in resp.data

    def test_create_item_invalid_cpq(self, admin_client, db):
        resp = admin_client.post('/admin/items/new', data={
            'item_name': 'X', 'sku': 'X', 'category': 'X',
            'unit_of_measure': 'x', 'case_pack_quantity': '0',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'positive integer' in resp.data

    def test_create_setting(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'par_level': '10', 'safety_stock': '2', 'reorder_threshold': '3',
            'min_send_quantity': '2', 'rounding_rule': 'round_up_case_pack', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_create_setting_invalid_rounding(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/admin/store-item-settings/new', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'par_level': '10', 'safety_stock': '2', 'reorder_threshold': '3',
            'min_send_quantity': '2', 'rounding_rule': 'INVALID', 'active': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Invalid rounding' in resp.data

    def test_warehouse_user_denied(self, warehouse_client, db):
        resp = warehouse_client.get('/admin/stores')
        assert resp.status_code == 403


class TestPlanGeneration:
    def test_generate_plan_page(self, admin_client, db):
        resp = admin_client.get('/plans/')
        assert resp.status_code == 200

    def test_generate_plan_post(self, admin_client, sample_settings, sample_usage,
                                sample_snapshots):
        today = date.today().isoformat()
        resp = admin_client.post('/plans/', data={
            'plan_date': today, 'regenerate': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Plan generated' in resp.data

    def test_generate_plan_missing_date(self, admin_client, db):
        resp = admin_client.post('/plans/', data={
            'plan_date': '',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'required' in resp.data

    def test_generate_plan_invalid_date(self, admin_client, db):
        resp = admin_client.post('/plans/', data={
            'plan_date': 'not-a-date',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Invalid date' in resp.data

    def test_warehouse_user_denied(self, warehouse_client, db):
        resp = warehouse_client.get('/plans/')
        assert resp.status_code == 403


class TestDataEntry:
    def test_daily_usage_page(self, admin_client, db):
        resp = admin_client.get('/data/daily-usage')
        assert resp.status_code == 200

    def test_inventory_snapshot_page(self, admin_client, db):
        resp = admin_client.get('/data/inventory-snapshots')
        assert resp.status_code == 200

    def test_daily_usage_post(self, admin_client, sample_stores, sample_items):
        today = date.today().isoformat()
        resp = admin_client.post('/data/daily-usage', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'usage_date': today, 'quantity_used': '5.0',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'saved' in resp.data

    def test_daily_usage_missing_fields(self, admin_client, db):
        resp = admin_client.post('/data/daily-usage', data={
            'store_id': '', 'item_id': '', 'usage_date': '', 'quantity_used': '',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'required' in resp.data

    def test_daily_usage_negative_qty(self, admin_client, sample_stores, sample_items):
        resp = admin_client.post('/data/daily-usage', data={
            'store_id': sample_stores[0].id, 'item_id': sample_items[0].id,
            'usage_date': date.today().isoformat(), 'quantity_used': '-5',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'non-negative' in resp.data

    def test_warehouse_user_denied(self, warehouse_client, db):
        resp = warehouse_client.get('/data/daily-usage')
        assert resp.status_code == 403
