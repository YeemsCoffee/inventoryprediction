"""Tests for the recommendation engine and plan generation service."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from warehouse_app.services.recommendation import (
    calculate_recommendation,
    get_average_usage,
    get_latest_on_hand,
    apply_rounding,
)
from warehouse_app.services.plan_generation import generate_plan
from warehouse_app.services.fulfillment import update_line_status, bulk_update_status
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot


class TestRounding:
    def test_round_up_integer(self):
        assert apply_rounding(Decimal('3.2'), 'round_up_integer', 1) == Decimal('4')

    def test_round_up_case_pack(self):
        assert apply_rounding(Decimal('5'), 'round_up_case_pack', 4) == Decimal('8')

    def test_round_up_case_pack_exact(self):
        assert apply_rounding(Decimal('8'), 'round_up_case_pack', 4) == Decimal('8')

    def test_no_rounding(self):
        assert apply_rounding(Decimal('3.2'), 'none', 4) == Decimal('3.2')

    def test_zero_quantity(self):
        assert apply_rounding(Decimal('0'), 'round_up_case_pack', 4) == Decimal('0')

    def test_negative_quantity(self):
        assert apply_rounding(Decimal('-1'), 'round_up_case_pack', 4) == Decimal('0')


class TestRecommendation:
    def test_no_data_uses_par_level(self, db, sample_stores, sample_items, sample_settings):
        """With no usage or snapshot data, recommendation uses par level."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())
        assert rec['confidence_level'] == 'low'
        assert rec['recommended_quantity'] > 0
        assert 'sparse_usage_history' in rec['warning_flags']

    def test_with_full_data(self, db, sample_stores, sample_items, sample_settings,
                            sample_usage, sample_snapshots):
        """With 7 days of data and a snapshot, confidence should be high."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())
        assert rec['confidence_level'] == 'high'
        assert rec['recommended_quantity'] >= 0

    def test_no_snapshot_lowers_confidence(self, db, sample_stores, sample_items,
                                           sample_settings, sample_usage):
        """Missing snapshot should reduce confidence."""
        store = sample_stores[0]
        item = sample_items[0]
        rec = calculate_recommendation(store.id, item.id, date.today())
        assert 'missing_snapshot' in rec['warning_flags']
        assert rec['confidence_level'] in ('medium', 'low')

    def test_min_send_quantity_enforced(self, db, sample_stores, sample_items):
        """When needed qty < min_send, it should be raised."""
        from warehouse_app.models.store_item_setting import StoreItemSetting
        store = sample_stores[0]
        item = sample_items[0]

        # High par level + high on-hand = tiny need, but min_send is large
        setting = StoreItemSetting(
            store_id=store.id, item_id=item.id,
            par_level=5, safety_stock=0, reorder_threshold=0,
            min_send_quantity=10, rounding_rule='none', active=True,
        )
        db.session.add(setting)
        # Snapshot with on-hand = 4 (need = 1, but min_send = 10)
        db.session.add(InventorySnapshot(
            store_id=store.id, item_id=item.id,
            snapshot_date=date.today() - timedelta(days=1),
            quantity_on_hand=4, source='test',
        ))
        db.session.commit()

        rec = calculate_recommendation(store.id, item.id, date.today())
        assert rec['recommended_quantity'] >= 10


class TestGetAverageUsage:
    def test_no_data(self, db, sample_stores, sample_items):
        avg, count = get_average_usage(sample_stores[0].id, sample_items[0].id,
                                       date.today(), 7)
        assert count == 0

    def test_with_data(self, db, sample_stores, sample_items, sample_usage):
        avg, count = get_average_usage(sample_stores[0].id, sample_items[0].id,
                                       date.today(), 7)
        assert count == 7
        assert float(avg) == pytest.approx(5.0, rel=0.01)


class TestGetLatestOnHand:
    def test_no_snapshot(self, db, sample_stores, sample_items):
        qty, snap_date = get_latest_on_hand(sample_stores[0].id, sample_items[0].id,
                                             date.today())
        assert qty is None
        assert snap_date is None

    def test_with_snapshot(self, db, sample_stores, sample_items, sample_snapshots):
        qty, snap_date = get_latest_on_hand(sample_stores[0].id, sample_items[0].id,
                                             date.today())
        assert float(qty) == 3.0
        assert snap_date is not None


class TestPlanGeneration:
    def test_generate_plan(self, db, sample_stores, sample_items, sample_settings,
                           sample_usage, sample_snapshots):
        result = generate_plan(date.today(), user_id=None)
        plan = result['plan']

        assert plan.status == 'draft'
        assert plan.plan_date == date.today()
        assert result['total_lines'] > 0
        assert result['total_stores'] == 2

    def test_regenerate_draft(self, db, sample_stores, sample_items, sample_settings,
                              sample_usage, sample_snapshots):
        result1 = generate_plan(date.today(), user_id=None)
        old_id = result1['plan'].id
        result2 = generate_plan(date.today(), user_id=None, regenerate=True)
        # The old plan should no longer exist
        assert ReplenishmentPlan.query.get(old_id) is None or result2['plan'].id >= old_id
        # New plan should be a fresh draft
        assert result2['plan'].status == 'draft'
        assert result2['total_lines'] > 0

    def test_cannot_regenerate_non_draft(self, db, sample_stores, sample_items,
                                         sample_settings, sample_usage, sample_snapshots):
        result = generate_plan(date.today(), user_id=None)
        plan = result['plan']
        plan.status = 'in_progress'
        db.session.commit()

        with pytest.raises(ValueError, match='Cannot regenerate'):
            generate_plan(date.today(), user_id=None, regenerate=True)

    def test_duplicate_plan_without_regenerate(self, db, sample_stores, sample_items,
                                               sample_settings, sample_usage,
                                               sample_snapshots):
        generate_plan(date.today(), user_id=None)
        with pytest.raises(ValueError, match='already exists'):
            generate_plan(date.today(), user_id=None, regenerate=False)


class TestFulfillmentService:
    def test_update_status(self, db, sample_plan):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        updated = update_line_status(line.id, new_status='picked')
        assert updated.status == 'picked'
        assert updated.last_status_change_at is not None

    def test_update_actual_quantity_only(self, db, sample_plan):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        updated = update_line_status(line.id, actual_quantity=12.5)
        assert float(updated.actual_quantity) == 12.5
        assert updated.status == 'pending'  # unchanged

    def test_update_note_only(self, db, sample_plan):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        updated = update_line_status(line.id, picker_note='Damaged pallet')
        assert updated.picker_note == 'Damaged pallet'

    def test_invalid_status_raises(self, db, sample_plan):
        line = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).first()
        with pytest.raises(ValueError, match='Invalid status'):
            update_line_status(line.id, new_status='BOGUS')

    def test_nonexistent_line_raises(self, db):
        with pytest.raises(ValueError, match='not found'):
            update_line_status(99999, new_status='picked')

    def test_bulk_update(self, db, sample_plan):
        lines = ReplenishmentPlanLine.query.filter_by(plan_id=sample_plan.id).limit(4).all()
        ids = [l.id for l in lines]
        count = bulk_update_status(ids, 'delivered')
        assert count == len(ids)
        for l_id in ids:
            assert ReplenishmentPlanLine.query.get(l_id).status == 'delivered'

    def test_bulk_update_invalid_status(self, db):
        with pytest.raises(ValueError, match='Invalid status'):
            bulk_update_status([1], 'BOGUS')
