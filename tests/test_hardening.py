"""Tests for Phase 6 operational hardening."""
from datetime import date

from warehouse_app.models.audit_log import AuditLog
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.csv_import import import_daily_usage_csv, import_inventory_snapshot_csv


class TestAuditLogging:
    def test_status_update_creates_audit_entry(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'picked'})
        assert resp.get_json()['success']

        entry = AuditLog.query.filter_by(entity_type='plan_line', entity_id=line.id).first()
        assert entry is not None
        assert 'picked' in entry.new_value

    def test_bulk_update_creates_audit_entries(self, admin_client, sample_plan, db):
        lines = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).limit(2).all()
        ids = [l.id for l in lines]
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': ids, 'status': 'loaded'})
        assert resp.get_json()['success']

        for lid in ids:
            entry = AuditLog.query.filter_by(
                entity_type='plan_line', entity_id=lid, action='bulk_update'
            ).first()
            assert entry is not None

    def test_plan_generation_creates_audit_entry(self, db, sample_stores, sample_items,
                                                  sample_settings, sample_usage, sample_snapshots):
        from warehouse_app.services.plan_generation import generate_plan
        result = generate_plan(date.today(), user_id=None)
        entry = AuditLog.query.filter_by(entity_type='plan', action='generate').first()
        assert entry is not None
        assert 'plan_date' in entry.new_value


class TestCSVValidationHardening:
    def test_missing_headers(self, db, sample_stores, sample_items):
        result = import_daily_usage_csv('bad_col1,bad_col2\nfoo,bar\n')
        assert result['imported'] == 0
        assert any('Missing required columns' in e for e in result['errors'])

    def test_snapshot_missing_headers(self, db, sample_stores, sample_items):
        result = import_inventory_snapshot_csv('bad_col1,bad_col2\nfoo,bar\n')
        assert result['imported'] == 0
        assert any('Missing required columns' in e for e in result['errors'])

    def test_future_date_rejected(self, db, sample_stores, sample_items):
        from datetime import timedelta
        future = (date.today() + timedelta(days=30)).isoformat()
        csv_data = f'store_code,sku,usage_date,quantity_used\nGARDENA,MILK-WHL,{future},5\n'
        result = import_daily_usage_csv(csv_data)
        assert result['imported'] == 0
        assert result['skipped'] == 1
        assert any('Future date' in e for e in result['errors'])


class TestAPIValidationHardening:
    def test_line_id_must_be_integer(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': 'abc', 'status': 'picked'})
        assert resp.status_code == 400
        assert 'integer' in resp.get_json()['error']

    def test_bulk_update_size_limit(self, admin_client, db):
        huge_list = list(range(1, 502))
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': huge_list, 'status': 'picked'})
        assert resp.status_code == 400
        assert '500' in resp.get_json()['error']

    def test_picker_note_length_limit(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'picker_note': 'x' * 501})
        assert resp.status_code == 400
        assert '500 characters' in resp.get_json()['error']


class TestActivityLogScreen:
    def test_activity_log_page(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/activity?plan_date={today}')
        assert resp.status_code == 200
        assert b'Activity Log' in resp.data

    def test_activity_log_no_plan(self, admin_client, db):
        resp = admin_client.get('/warehouse/activity?plan_date=2020-01-01')
        assert resp.status_code == 200
        assert b'No plan found' in resp.data


class TestPlanGenerationSafeguards:
    def test_no_active_settings_error(self, db, sample_stores, sample_items):
        import pytest
        from warehouse_app.services.plan_generation import generate_plan
        with pytest.raises(ValueError, match='No active store-item settings'):
            generate_plan(date.today(), user_id=None)

    def test_regenerate_confirmation_flow(self, admin_client, sample_plan):
        """Regenerating a draft plan should show a confirmation page first."""
        today = date.today().isoformat()
        resp = admin_client.post('/plans/', data={
            'plan_date': today, 'regenerate': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Confirm Regenerate' in resp.data


class TestDeliverySheetProgress:
    def test_progress_bar_in_delivery(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert resp.status_code == 200
        assert b'progress-bar' in resp.data
        assert b'pending' in resp.data
