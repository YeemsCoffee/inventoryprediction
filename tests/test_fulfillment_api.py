"""Tests for the fulfillment API endpoints."""
from datetime import date

import pytest

from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine


class TestUpdateLineAPI:
    def test_unauthenticated(self, client):
        resp = client.post('/warehouse/api/update-line',
                           json={'line_id': 1, 'status': 'picked'})
        assert resp.status_code == 302

    def test_no_json_body(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/update-line',
                                 data='not json',
                                 content_type='text/plain')
        assert resp.status_code == 400

    def test_missing_line_id(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'status': 'picked'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'line_id is required'

    def test_nonexistent_line(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': 99999, 'status': 'picked'})
        assert resp.status_code == 400
        assert 'not found' in resp.get_json()['error']

    def test_invalid_status(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'INVALID'})
        assert resp.status_code == 400

    def test_update_status(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'picked'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['status'] == 'picked'

    def test_update_actual_quantity(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': 7.5})
        data = resp.get_json()
        assert data['success'] is True
        assert data['actual_quantity'] == 7.5

    def test_update_picker_note(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'picker_note': 'Short on shelf'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['picker_note'] == 'Short on shelf'

    def test_negative_actual_quantity_rejected(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': -5})
        assert resp.status_code == 400
        assert 'non-negative' in resp.get_json()['error']

    def test_invalid_actual_quantity_type(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': 'abc'})
        assert resp.status_code == 400

    def test_full_workflow_pick_load_deliver(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()

        for status in ['picked', 'loaded', 'delivered']:
            resp = admin_client.post('/warehouse/api/update-line',
                                     json={'line_id': line.id, 'status': status})
            data = resp.get_json()
            assert data['success'] is True
            assert data['status'] == status


class TestBulkUpdateAPI:
    def test_unauthenticated(self, client):
        resp = client.post('/warehouse/api/bulk-update',
                           json={'line_ids': [1], 'status': 'picked'})
        assert resp.status_code == 302

    def test_no_json_body(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 data='not json',
                                 content_type='text/plain')
        assert resp.status_code == 400

    def test_missing_line_ids(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'status': 'picked'})
        assert resp.status_code == 400

    def test_missing_status(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': [1]})
        assert resp.status_code == 400

    def test_invalid_status(self, admin_client, db):
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': [1], 'status': 'INVALID'})
        assert resp.status_code == 400

    def test_bulk_update_success(self, admin_client, sample_plan, db):
        lines = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).limit(3).all()
        ids = [l.id for l in lines]
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': ids, 'status': 'loaded'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['updated'] == len(ids)

        # Verify in DB
        for line_id in ids:
            line = ReplenishmentPlanLine.query.get(line_id)
            assert line.status == 'loaded'

    def test_warehouse_user_can_update(self, warehouse_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        resp = warehouse_client.post('/warehouse/api/update-line',
                                     json={'line_id': line.id, 'status': 'picked'})
        data = resp.get_json()
        assert data['success'] is True
