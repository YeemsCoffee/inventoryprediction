"""Tests for the dashboard."""
from datetime import date


class TestDashboard:
    def test_unauthenticated_redirect(self, client):
        resp = client.get('/')
        assert resp.status_code == 302

    def test_dashboard_no_plan(self, admin_client, db):
        resp = admin_client.get('/')
        assert resp.status_code == 200
        assert b'No plan exists' in resp.data

    def test_dashboard_with_plan(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert resp.status_code == 200
        assert b'Master Pick List' in resp.data
        assert b'Exceptions' in resp.data

    def test_dashboard_stats(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert resp.status_code == 200
        html = resp.data.decode().lower()
        assert 'stores' in html
        assert 'total lines' in html

    def test_dashboard_store_links(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert resp.status_code == 200
        assert b'Gardena' in resp.data
        assert b'K-Town' in resp.data

    def test_dashboard_invalid_date_fallback(self, admin_client, db):
        resp = admin_client.get('/?plan_date=not-a-date')
        assert resp.status_code == 200

    def test_warehouse_user_sees_dashboard(self, warehouse_client, sample_plan):
        resp = warehouse_client.get('/')
        assert resp.status_code == 200
