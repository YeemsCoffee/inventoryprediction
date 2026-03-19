"""Tests for Phase 1D: UI optimizations, progress tracking, fulfillment workflow."""
from datetime import date

from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine


class TestStaticAssets:
    """Verify CSS and JS files are served."""

    def test_css_served(self, admin_client):
        resp = admin_client.get('/static/css/style.css')
        assert resp.status_code == 200
        assert b'warehouse' in resp.data.lower() or b'.navbar' in resp.data

    def test_js_served(self, admin_client):
        resp = admin_client.get('/static/js/app.js')
        assert resp.status_code == 200
        assert b'toggleBreakdown' in resp.data

    def test_css_has_progress_bar(self, admin_client):
        resp = admin_client.get('/static/css/style.css')
        assert b'.progress-bar' in resp.data
        assert b'.progress-segment' in resp.data

    def test_css_has_toast(self, admin_client):
        resp = admin_client.get('/static/css/style.css')
        assert b'.toast' in resp.data

    def test_css_has_print_styles(self, admin_client):
        resp = admin_client.get('/static/css/style.css')
        assert b'@media print' in resp.data
        assert b'no-print' in resp.data

    def test_css_has_mobile_styles(self, admin_client):
        resp = admin_client.get('/static/css/style.css')
        assert b'max-width: 768px' in resp.data or b'max-width:768px' in resp.data

    def test_js_has_toast_function(self, admin_client):
        resp = admin_client.get('/static/js/app.js')
        assert b'showToast' in resp.data


class TestDashboardProgressBar:
    """Dashboard should show visual progress bar when plan exists."""

    def test_progress_bar_rendered(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert resp.status_code == 200
        assert b'progress-bar' in resp.data
        assert b'progress-segment' in resp.data

    def test_stats_grid_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert b'stats-grid' in resp.data

    def test_store_buttons_grid(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/?plan_date={today}')
        assert b'store-buttons' in resp.data

    def test_empty_state_class(self, admin_client, db):
        resp = admin_client.get('/?plan_date=2020-01-01')
        assert resp.status_code == 200
        assert b'empty-state' in resp.data


class TestDeliverySheetEnhancements:
    """Delivery sheet should have progress bar, toast support, action buttons."""

    def test_progress_bar_in_delivery(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert resp.status_code == 200
        assert b'progress-bar' in resp.data
        assert b'progress-segment' in resp.data

    def test_progress_badges(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert b'progress-badges' in resp.data

    def test_action_btns_class(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert b'action-btns' in resp.data

    def test_bulk_actions_class(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert b'bulk-actions' in resp.data

    def test_inline_js_has_toast(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        assert b'showToast' in resp.data

    def test_row_class_updates_in_js(self, admin_client, sample_plan, sample_stores):
        today = date.today().isoformat()
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date={today}')
        # JS should update row class on status change
        assert b'line-row line-' in resp.data

    def test_empty_state_no_plan(self, admin_client, sample_stores):
        store_id = sample_stores[0].id
        resp = admin_client.get(f'/warehouse/delivery/{store_id}?plan_date=2020-01-01')
        assert b'empty-state' in resp.data


class TestPickListEnhancements:
    """Pick list should use enhanced CSS classes."""

    def test_page_header_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert b'page-header' in resp.data

    def test_meta_line_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert b'meta-line' in resp.data

    def test_filter_bar_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert b'filter-bar' in resp.data

    def test_print_only_footer(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/pick-list?plan_date={today}')
        assert b'print-only' in resp.data


class TestExceptionsEnhancements:
    """Exceptions page should use enhanced classes."""

    def test_page_header_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/exceptions?plan_date={today}')
        assert b'page-header' in resp.data

    def test_meta_line_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/exceptions?plan_date={today}')
        assert b'meta-line' in resp.data

    def test_shorted_row_styling(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        line.status = 'shorted'
        db.session.commit()

        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/exceptions?plan_date={today}')
        assert b'line-shorted' in resp.data


class TestActivityLogEnhancements:
    """Activity log should use enhanced classes."""

    def test_page_header_class(self, admin_client, sample_plan):
        today = date.today().isoformat()
        resp = admin_client.get(f'/warehouse/activity?plan_date={today}')
        assert b'page-header' in resp.data

    def test_empty_state(self, admin_client, db):
        resp = admin_client.get('/warehouse/activity?plan_date=2020-01-01')
        assert b'empty-state' in resp.data


class TestFulfillmentWorkflowEnd2End:
    """End-to-end tests for the full pick → load → deliver workflow."""

    def test_pick_then_load_then_deliver(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()

        # Pick
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'picked'})
        assert resp.get_json()['success'] is True

        # Set actual qty
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': 8.0})
        assert resp.get_json()['success'] is True

        # Add note
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'picker_note': 'Grabbed from back'})
        assert resp.get_json()['success'] is True

        # Load
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'loaded'})
        assert resp.get_json()['success'] is True

        # Deliver
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'delivered'})
        assert resp.get_json()['success'] is True

        # Verify final state
        db.session.refresh(line)
        assert line.status == 'delivered'
        assert float(line.actual_quantity) == 8.0
        assert line.picker_note == 'Grabbed from back'

    def test_short_workflow(self, admin_client, sample_plan, db):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()

        # Pick with partial qty
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'actual_quantity': 2.0})
        assert resp.get_json()['success'] is True

        # Short it
        resp = admin_client.post('/warehouse/api/update-line',
                                 json={'line_id': line.id, 'status': 'shorted'})
        assert resp.get_json()['success'] is True

        db.session.refresh(line)
        assert line.status == 'shorted'

    def test_bulk_pick_then_bulk_load(self, admin_client, sample_plan, db):
        lines = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).limit(4).all()
        ids = [l.id for l in lines]

        # Bulk pick
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': ids, 'status': 'picked'})
        assert resp.get_json()['success'] is True
        assert resp.get_json()['updated'] == 4

        # Bulk load
        resp = admin_client.post('/warehouse/api/bulk-update',
                                 json={'line_ids': ids, 'status': 'loaded'})
        assert resp.get_json()['success'] is True

        # Verify
        for line_id in ids:
            line = db.session.get(ReplenishmentPlanLine, line_id)
            assert line.status == 'loaded'
