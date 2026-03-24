"""Tests for the warehouse screens: pick list, delivery sheet, exceptions."""
from datetime import date


class TestMasterPickList:
    def test_unauthenticated_redirect(self, client):
        resp = client.get('/warehouse/pick-list')
        assert resp.status_code == 302

    def test_no_plan(self, admin_client, db):
        resp = admin_client.get('/warehouse/pick-list?plan_date=2020-01-01')
        assert resp.status_code == 200
        assert b'No plan found' in resp.data

    def test_with_plan(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert resp.status_code == 200
        assert b'Master Pick List' in resp.data
        assert b'Whole Milk' in resp.data

    def test_category_filter(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}&category=Dairy')
        assert resp.status_code == 200
        assert b'Whole Milk' in resp.data
        # Coffee items should not appear
        assert b'Espresso Beans' not in resp.data

    def test_search_filter(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}&q=espresso')
        assert resp.status_code == 200
        assert b'Espresso Beans' in resp.data
        assert b'Whole Milk' not in resp.data

    def test_warehouse_user_access(self, warehouse_client, sample_plan):
        today = date.today().isoformat()
        resp = warehouse_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert resp.status_code == 200


class TestStoreDeliverySheet:
    def test_unauthenticated_redirect(self, client):
        resp = client.get('/warehouse/delivery/1')
        assert resp.status_code == 302

    def test_invalid_store_404(self, admin_client, db):
        resp = admin_client.get('/warehouse/delivery/99999')
        assert resp.status_code == 404

    def test_no_plan(self, admin_client, sample_stores):
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date=2020-01-01')
        assert resp.status_code == 200
        assert b'No plan found' in resp.data

    def test_with_plan(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert resp.status_code == 200
        assert b'Gardena' in resp.data
        assert b'Delivery Sheet' in resp.data

    def test_line_items_shown(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert resp.status_code == 200
        assert b'Whole Milk' in resp.data
        assert b'pending' in resp.data


class TestExceptions:
    def test_unauthenticated_redirect(self, client):
        resp = client.get('/warehouse/exceptions')
        assert resp.status_code == 302

    def test_no_plan(self, admin_client, db):
        resp = admin_client.get('/warehouse/exceptions?plan_date=2020-01-01')
        assert resp.status_code == 200
        assert b'No plan found' in resp.data

    def test_with_plan_clean(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/exceptions?plan_date={today}')
        assert resp.status_code == 200
        # Page should load
        assert b'Exceptions' in resp.data

    def test_shorted_lines_shown(self, admin_client, sample_plan, db):
        from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        line.status = 'shorted'
        db.session.commit()

        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/exceptions?plan_date={today}')
        assert resp.status_code == 200
        assert b'shorted' in resp.data
