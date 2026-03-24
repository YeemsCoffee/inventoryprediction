"""Tests for Phase 2: Weighted historical forecasting."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine
from warehouse_app.services.forecasting import (
    VALID_FORECAST_METHODS,
    get_average_usage,
    get_weighted_average_usage,
    build_forecast,
    _build_simple_forecast,
    _build_weighted_forecast,
    _compute_coverage,
)


# ── Config ───────────────────────────────────────────────────────────

class TestForecastConfig:
    def test_default_method_is_simple(self, app):
        with app.app_context():
            assert app.config['FORECAST_METHOD'] == 'historical_simple_v1'

    def test_weighted_config_defaults(self, app):
        with app.app_context():
            assert app.config['WEIGHTED_DECAY_FACTOR'] == 0.9
            assert app.config['WEIGHTED_DOW_MULTIPLIER'] == 0.0

    def test_valid_methods_constant(self):
        assert 'historical_simple_v1' in VALID_FORECAST_METHODS
        assert 'historical_weighted_v1' in VALID_FORECAST_METHODS


# ── Coverage helper ──────────────────────────────────────────────────

class TestComputeCoverage:
    def test_full_coverage(self):
        assert _compute_coverage(7, 7) == 1.0

    def test_partial_coverage(self):
        assert _compute_coverage(3, 7) == pytest.approx(3 / 7)

    def test_zero_window(self):
        assert _compute_coverage(5, 0) == 0.0

    def test_over_coverage_capped(self):
        assert _compute_coverage(10, 7) == 1.0


# ── Simple forecast (V1 behavior unchanged) ──────────────────────────

class TestSimpleForecastBuilder:
    def test_returns_correct_method(self, app, db, sample_stores, sample_items,
                                     sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_simple_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5)
            assert result['forecast_method'] == 'historical_simple_v1'

    def test_has_data_coverage(self, app, db, sample_stores, sample_items,
                               sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_simple_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5)
            assert 'data_coverage' in result
            assert result['data_coverage'] == 1.0  # 7 of 7 days

    def test_high_confidence_with_data(self, app, db, sample_stores, sample_items,
                                       sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_simple_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5)
            assert result['confidence'] == 'high'
            assert result['data_points'] == 7

    def test_no_data_returns_low_confidence(self, app, db, sample_stores, sample_items,
                                             sample_settings):
        with app.app_context():
            result = _build_simple_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5)
            assert result['confidence'] == 'low'
            assert result['data_points'] == 0
            assert 'sparse_usage_history' in result['warnings']


# ── Weighted average function ────────────────────────────────────────

class TestGetWeightedAverageUsage:
    def test_basic_weighted_avg(self, app, db, sample_stores, sample_items, sample_usage):
        """With uniform usage data, weighted avg should equal simple avg."""
        with app.app_context():
            simple_avg, simple_count = get_average_usage(
                sample_stores[0].id, sample_items[0].id, date.today(), 7)
            weighted_avg, weighted_count, _ = get_weighted_average_usage(
                sample_stores[0].id, sample_items[0].id, date.today(), 7,
                decay_factor=1.0)  # no decay = same as simple

            assert simple_count == weighted_count
            # With decay=1.0 and uniform data, weighted should equal simple
            assert abs(float(simple_avg) - float(weighted_avg)) < 0.01

    def test_decay_emphasizes_recent(self, app, db, sample_stores, sample_items):
        """With increasing usage, decay should produce higher avg than simple."""
        from warehouse_app.models.daily_usage import DailyUsage
        today = date.today()
        store_id = sample_stores[0].id
        item_id = sample_items[0].id

        # Create ascending usage: day -1 = 10, day -2 = 8, ..., day -7 = 2 (old)
        for d in range(1, 8):
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=today - timedelta(days=d),
                quantity_used=12 - d * 2 + 2,  # 12, 10, 8, 6, 4, 2, 0... wait
                source='test',
            ))
        # Simpler: day -1 = 10, day -7 = 1
        db.session.rollback()

        for d in range(1, 8):
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=today - timedelta(days=d),
                quantity_used=float(8 - d),  # 7, 6, 5, 4, 3, 2, 1
                source='test',
            ))
        db.session.commit()

        with app.app_context():
            simple_avg, _ = get_average_usage(store_id, item_id, today, 7)
            weighted_avg, _, _ = get_weighted_average_usage(
                store_id, item_id, today, 7, decay_factor=0.8)

            # Weighted avg should be higher because recent days (higher values)
            # get more weight
            assert weighted_avg > simple_avg

    def test_no_data_returns_zero(self, app, db, sample_stores, sample_items):
        with app.app_context():
            avg, count, dow = get_weighted_average_usage(
                sample_stores[0].id, sample_items[0].id, date.today(), 7,
                decay_factor=0.9)
            assert avg == Decimal('0')
            assert count == 0
            assert dow == 0

    def test_dow_multiplier_counted(self, app, db, sample_stores, sample_items, sample_usage):
        with app.app_context():
            _, _, dow_matches = get_weighted_average_usage(
                sample_stores[0].id, sample_items[0].id, date.today(), 7,
                decay_factor=0.9, dow_multiplier=1.5)
            # At least 1 day in the 7-day window should match the plan weekday
            assert dow_matches >= 1

    def test_dow_zero_means_disabled(self, app, db, sample_stores, sample_items, sample_usage):
        with app.app_context():
            _, _, dow_matches = get_weighted_average_usage(
                sample_stores[0].id, sample_items[0].id, date.today(), 7,
                decay_factor=0.9, dow_multiplier=0.0)
            # With multiplier=0, dow_matches should be 0
            assert dow_matches == 0


# ── Weighted forecast builder ────────────────────────────────────────

class TestWeightedForecastBuilder:
    def test_returns_correct_method(self, app, db, sample_stores, sample_items,
                                     sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=0.0)
            assert result['forecast_method'] == 'historical_weighted_v1'

    def test_has_data_coverage(self, app, db, sample_stores, sample_items,
                               sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=0.0)
            assert 'data_coverage' in result
            assert result['data_coverage'] == 1.0

    def test_has_dow_matches(self, app, db, sample_stores, sample_items,
                             sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=1.5)
            assert 'dow_matches' in result
            assert result['dow_matches'] >= 1

    def test_dow_explanation_added(self, app, db, sample_stores, sample_items,
                                   sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=1.5)
            assert any('DOW weighting' in e for e in result['explanations'])

    def test_no_dow_explanation_when_disabled(self, app, db, sample_stores, sample_items,
                                              sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=0.0)
            assert not any('DOW weighting' in e for e in result['explanations'])

    def test_high_confidence_with_full_data(self, app, db, sample_stores, sample_items,
                                             sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=0.0)
            assert result['confidence'] == 'high'

    def test_no_data_returns_low_confidence(self, app, db, sample_stores, sample_items,
                                             sample_settings):
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=0.0)
            assert result['confidence'] == 'low'
            assert result['data_points'] == 0

    def test_low_coverage_downgrades_confidence(self, app, db, sample_stores, sample_items,
                                                 sample_settings, sample_snapshots):
        """2 data points in a 7-day window = ~29% coverage → medium."""
        from warehouse_app.models.daily_usage import DailyUsage
        today = date.today()
        store_id = sample_stores[0].id
        item_id = sample_items[0].id
        for d in [1, 2]:
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=today - timedelta(days=d),
                quantity_used=5.0, source='test',
            ))
        db.session.commit()

        with app.app_context():
            result = _build_weighted_forecast(
                store_id, item_id, today,
                window_short=7, window_long=14,
                min_data_points=2,  # enough to pick short window
                decay_factor=0.9, dow_multiplier=0.0)
            # 2/7 = 28% coverage < 50% → should downgrade
            assert result['data_coverage'] < 0.5
            assert 'low_data_coverage' in result['warnings']
            assert result['confidence'] in ('medium', 'low')


# ── Dispatch via build_forecast ──────────────────────────────────────

class TestBuildForecastDispatch:
    def test_default_dispatches_to_simple(self, app, db, sample_stores, sample_items,
                                          sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
            assert result['forecast_method'] == 'historical_simple_v1'

    def test_weighted_dispatch(self, app, db, sample_stores, sample_items,
                               sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            app.config['FORECAST_METHOD'] = 'historical_weighted_v1'
            try:
                result = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
                assert result['forecast_method'] == 'historical_weighted_v1'
                assert 'data_coverage' in result
            finally:
                app.config['FORECAST_METHOD'] = 'historical_simple_v1'

    def test_simple_also_has_data_coverage(self, app, db, sample_stores, sample_items,
                                            sample_settings, sample_usage, sample_snapshots):
        with app.app_context():
            result = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
            assert 'data_coverage' in result

    def test_output_interface_unchanged(self, app, db, sample_stores, sample_items,
                                        sample_settings, sample_usage, sample_snapshots):
        """Both methods return the same core keys."""
        required_keys = {
            'avg_daily_usage', 'confidence', 'window_days', 'data_points',
            'data_coverage', 'on_hand', 'on_hand_date', 'explanations',
            'warnings', 'forecast_method',
        }
        with app.app_context():
            simple = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
            assert required_keys.issubset(simple.keys())

            app.config['FORECAST_METHOD'] = 'historical_weighted_v1'
            try:
                weighted = build_forecast(sample_stores[0].id, sample_items[0].id, date.today())
                assert required_keys.issubset(weighted.keys())
            finally:
                app.config['FORECAST_METHOD'] = 'historical_simple_v1'


# ── Downstream integration (replenishment + plan gen unchanged) ──────

class TestDownstreamIntegration:
    def test_replenishment_with_weighted(self, app, db, sample_stores, sample_items,
                                         sample_settings, sample_usage, sample_snapshots):
        from warehouse_app.services.replenishment import calculate_recommendation
        with app.app_context():
            app.config['FORECAST_METHOD'] = 'historical_weighted_v1'
            try:
                rec = calculate_recommendation(
                    sample_stores[0].id, sample_items[0].id, date.today())
                assert rec['forecast_method'] == 'historical_weighted_v1'
                assert rec['recommended_quantity'] >= 0
                assert rec['confidence_level'] in ('high', 'medium', 'low')
            finally:
                app.config['FORECAST_METHOD'] = 'historical_simple_v1'

    def test_plan_generation_with_weighted(self, app, db, sample_stores, sample_items,
                                           sample_settings, sample_usage, sample_snapshots):
        from warehouse_app.services.plan_generation import generate_plan
        with app.app_context():
            app.config['FORECAST_METHOD'] = 'historical_weighted_v1'
            try:
                result = generate_plan(date.today(), user_id=None)
                plan = result['plan']
                assert result['total_lines'] > 0

                # Verify method persisted on lines
                line = ReplenishmentPlanLine.query.filter_by(plan_id=plan.id).first()
                assert line.forecast_method == 'historical_weighted_v1'
            finally:
                app.config['FORECAST_METHOD'] = 'historical_simple_v1'

    def test_simple_and_weighted_produce_different_values(
            self, app, db, sample_stores, sample_items,
            sample_settings, sample_snapshots):
        """With non-uniform data, methods should produce different forecasts."""
        from warehouse_app.models.daily_usage import DailyUsage
        today = date.today()
        store_id = sample_stores[0].id
        item_id = sample_items[0].id

        # Create ascending usage: recent days higher
        for d in range(1, 8):
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=today - timedelta(days=d),
                quantity_used=float(8 - d),  # 7, 6, 5, 4, 3, 2, 1
                source='test',
            ))
        db.session.commit()

        with app.app_context():
            simple = build_forecast(store_id, item_id, today)

            app.config['FORECAST_METHOD'] = 'historical_weighted_v1'
            app.config['WEIGHTED_DECAY_FACTOR'] = 0.7  # strong decay
            try:
                weighted = build_forecast(store_id, item_id, today)
            finally:
                app.config['FORECAST_METHOD'] = 'historical_simple_v1'
                app.config['WEIGHTED_DECAY_FACTOR'] = 0.9

            # Weighted should be higher (recent days have higher usage)
            assert weighted['avg_daily_usage'] > simple['avg_daily_usage']


# ── DOW weighting edge cases ─────────────────────────────────────────

class TestDOWWeighting:
    def test_dow_with_full_week(self, app, db, sample_stores, sample_items,
                                sample_settings, sample_usage, sample_snapshots):
        """7 consecutive days should always have exactly 1 matching weekday."""
        with app.app_context():
            result = _build_weighted_forecast(
                sample_stores[0].id, sample_items[0].id, date.today(),
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=1.5)
            assert result['dow_matches'] == 1

    def test_dow_with_14_day_window(self, app, db, sample_stores, sample_items,
                                     sample_settings, sample_snapshots):
        """14-day window with data on all days should have 2 matching weekdays."""
        from warehouse_app.models.daily_usage import DailyUsage
        today = date.today()
        store_id = sample_stores[0].id
        item_id = sample_items[0].id
        for d in range(1, 15):
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=today - timedelta(days=d),
                quantity_used=5.0, source='test',
            ))
        db.session.commit()

        with app.app_context():
            result = _build_weighted_forecast(
                store_id, item_id, today,
                window_short=14, window_long=28, min_data_points=5,
                decay_factor=0.9, dow_multiplier=1.5)
            assert result['dow_matches'] == 2

    def test_sparse_dow_warning(self, app, db, sample_stores, sample_items,
                                 sample_settings, sample_snapshots):
        """With DOW enabled and sparse same-weekday data, should get warning."""
        from warehouse_app.models.daily_usage import DailyUsage
        today = date.today()
        plan_weekday = today.weekday()
        store_id = sample_stores[0].id
        item_id = sample_items[0].id

        # Create 7 days of data but skip the matching weekday
        for d in range(1, 8):
            usage_date = today - timedelta(days=d)
            if usage_date.weekday() == plan_weekday:
                continue  # skip same weekday
            db.session.add(DailyUsage(
                store_id=store_id, item_id=item_id,
                usage_date=usage_date,
                quantity_used=5.0, source='test',
            ))
        db.session.commit()

        with app.app_context():
            result = _build_weighted_forecast(
                store_id, item_id, today,
                window_short=7, window_long=14, min_data_points=5,
                decay_factor=0.9, dow_multiplier=1.5)
            assert result['dow_matches'] == 0
            # Confidence should be downgraded or warning added
            if result['data_points'] >= 5:
                assert 'sparse_dow_history' in result['warnings']


# ── Backward compatibility ───────────────────────────────────────────

class TestPhase2BackwardCompat:
    def test_recommendation_reexports_still_work(self):
        from warehouse_app.services.recommendation import (
            get_average_usage,
            get_latest_on_hand,
            build_forecast,
            apply_rounding,
            calculate_recommendation,
        )
        assert callable(get_average_usage)
        assert callable(build_forecast)

    def test_get_weighted_average_importable(self):
        from warehouse_app.services.forecasting import get_weighted_average_usage
        assert callable(get_weighted_average_usage)
