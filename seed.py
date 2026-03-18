"""
Seed script for warehouse replenishment app.

Usage:
    FLASK_APP=warehouse_app:create_app python seed.py

Creates realistic demo data for 2 stores (Gardena, K-Town) with
15-25 inventory items, 30+ days of usage history, recent snapshots,
and example replenishment plans.
"""
import random
from datetime import date, datetime, timedelta, timezone

from warehouse_app import create_app
from warehouse_app.extensions import db
from warehouse_app.models.user import User
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine


def seed():
    app = create_app()
    with app.app_context():
        print("Clearing existing data...")
        ReplenishmentPlanLine.query.delete()
        ReplenishmentPlan.query.delete()
        InventorySnapshot.query.delete()
        DailyUsage.query.delete()
        StoreItemSetting.query.delete()
        InventoryItem.query.delete()
        Store.query.delete()
        User.query.delete()
        db.session.commit()

        # ── Users ──────────────────────────────────────────────
        print("Creating users...")
        admin = User(full_name='Admin User', email='admin@yeems.com', role='admin', active=True)
        admin.set_password('admin123')

        warehouse_user = User(full_name='Warehouse Worker', email='warehouse@yeems.com', role='warehouse', active=True)
        warehouse_user.set_password('warehouse123')

        db.session.add_all([admin, warehouse_user])
        db.session.flush()

        # ── Stores ─────────────────────────────────────────────
        print("Creating stores...")
        stores = [
            Store(name='Gardena', code='GARDENA', active=True),
            Store(name='K-Town', code='KTOWN', active=True),
        ]
        db.session.add_all(stores)
        db.session.flush()

        # ── Inventory Items ────────────────────────────────────
        print("Creating inventory items...")
        items_data = [
            # (name, sku, category, unit_of_measure, case_pack_quantity)
            ('Whole Milk', 'MILK-WHL-GAL', 'Dairy', 'gallon', 4),
            ('Oat Milk', 'MILK-OAT-HG', 'Dairy', 'half_gallon', 6),
            ('Heavy Cream', 'CRM-HVY-QT', 'Dairy', 'quart', 12),
            ('Vanilla Syrup', 'SYR-VAN-750', 'Syrups', 'bottle', 6),
            ('Caramel Syrup', 'SYR-CAR-750', 'Syrups', 'bottle', 6),
            ('Hazelnut Syrup', 'SYR-HAZ-750', 'Syrups', 'bottle', 6),
            ('Mocha Sauce', 'SAU-MOC-64', 'Syrups', 'bottle', 4),
            ('Espresso Beans (House)', 'BEA-HSE-5LB', 'Coffee', 'bag', 4),
            ('Espresso Beans (Single Origin)', 'BEA-SOR-5LB', 'Coffee', 'bag', 4),
            ('Drip Coffee Beans', 'BEA-DRP-5LB', 'Coffee', 'bag', 4),
            ('Matcha Powder', 'PWD-MAT-1LB', 'Powders', 'bag', 12),
            ('Chai Concentrate', 'CHA-CON-32', 'Beverages', 'bottle', 6),
            ('Cup 12oz', 'CUP-12OZ', 'Supplies', 'sleeve', 20),
            ('Cup 16oz', 'CUP-16OZ', 'Supplies', 'sleeve', 20),
            ('Lid 12oz/16oz', 'LID-1216', 'Supplies', 'sleeve', 20),
            ('Straw', 'STR-STD', 'Supplies', 'box', 24),
            ('Napkin', 'NAP-STD', 'Supplies', 'pack', 12),
            ('Croissant', 'PST-CRO', 'Pastry', 'piece', 12),
            ('Blueberry Muffin', 'PST-BMF', 'Pastry', 'piece', 12),
            ('Chocolate Chip Cookie', 'PST-CCC', 'Pastry', 'piece', 24),
        ]

        items = []
        for name, sku, category, uom, cpq in items_data:
            item = InventoryItem(
                item_name=name, sku=sku, category=category,
                unit_of_measure=uom, case_pack_quantity=cpq, active=True,
            )
            items.append(item)
        db.session.add_all(items)
        db.session.flush()

        # ── Store Item Settings ────────────────────────────────
        print("Creating store item settings...")
        # Define per-item defaults; Gardena is higher-volume than K-Town
        volume_multiplier = {'GARDENA': 1.0, 'KTOWN': 0.7}

        settings_defaults = {
            # sku: (par_level, safety_stock, reorder_threshold, min_send, rounding_rule)
            'MILK-WHL-GAL': (8, 2, 3, 2, 'round_up_case_pack'),
            'MILK-OAT-HG': (6, 2, 2, 2, 'round_up_case_pack'),
            'CRM-HVY-QT': (4, 1, 2, 1, 'round_up_integer'),
            'SYR-VAN-750': (4, 1, 2, 1, 'round_up_case_pack'),
            'SYR-CAR-750': (3, 1, 1, 1, 'round_up_integer'),
            'SYR-HAZ-750': (2, 1, 1, 1, 'none'),
            'SAU-MOC-64': (3, 1, 1, 1, 'round_up_integer'),
            'BEA-HSE-5LB': (6, 2, 2, 1, 'round_up_case_pack'),
            'BEA-SOR-5LB': (3, 1, 1, 1, 'round_up_integer'),
            'BEA-DRP-5LB': (4, 1, 2, 1, 'round_up_case_pack'),
            'PWD-MAT-1LB': (3, 1, 1, 1, 'round_up_integer'),
            'CHA-CON-32': (3, 1, 1, 1, 'round_up_integer'),
            'CUP-12OZ': (10, 3, 4, 2, 'round_up_case_pack'),
            'CUP-16OZ': (8, 2, 3, 2, 'round_up_case_pack'),
            'LID-1216': (10, 3, 4, 2, 'round_up_case_pack'),
            'STR-STD': (4, 1, 2, 1, 'round_up_case_pack'),
            'NAP-STD': (4, 1, 2, 1, 'round_up_case_pack'),
            'PST-CRO': (12, 3, 4, 6, 'round_up_case_pack'),
            'PST-BMF': (8, 2, 3, 6, 'round_up_case_pack'),
            'PST-CCC': (10, 2, 3, 6, 'round_up_case_pack'),
        }

        all_settings = []
        for store in stores:
            mult = volume_multiplier[store.code]
            for item in items:
                defaults = settings_defaults[item.sku]
                par = round(defaults[0] * mult)
                safety = round(defaults[1] * mult)
                reorder = round(defaults[2] * mult)
                min_send = defaults[3]
                rounding = defaults[4]

                setting = StoreItemSetting(
                    store_id=store.id, item_id=item.id,
                    par_level=par, safety_stock=safety,
                    reorder_threshold=reorder, min_send_quantity=min_send,
                    rounding_rule=rounding, active=True,
                )
                all_settings.append(setting)
        db.session.add_all(all_settings)
        db.session.flush()

        # ── Daily Usage (35 days of history) ───────────────────
        print("Creating daily usage data (35 days)...")
        today = date.today()
        usage_rows = []

        # Base daily usage per item (approximate)
        base_usage = {
            'MILK-WHL-GAL': 4.0, 'MILK-OAT-HG': 3.0, 'CRM-HVY-QT': 1.5,
            'SYR-VAN-750': 1.2, 'SYR-CAR-750': 0.8, 'SYR-HAZ-750': 0.4,
            'SAU-MOC-64': 0.7, 'BEA-HSE-5LB': 2.5, 'BEA-SOR-5LB': 1.0,
            'BEA-DRP-5LB': 1.5, 'PWD-MAT-1LB': 0.8, 'CHA-CON-32': 0.6,
            'CUP-12OZ': 5.0, 'CUP-16OZ': 4.0, 'LID-1216': 5.0,
            'STR-STD': 2.0, 'NAP-STD': 2.0,
            'PST-CRO': 8.0, 'PST-BMF': 5.0, 'PST-CCC': 6.0,
        }

        for day_offset in range(35, 0, -1):
            usage_date = today - timedelta(days=day_offset)
            for store in stores:
                mult = volume_multiplier[store.code]
                for item in items:
                    base = base_usage[item.sku] * mult
                    # Add realistic variance (±30%)
                    qty = max(0, round(base * random.uniform(0.7, 1.3), 1))

                    # Make some items have sparse data for K-Town to demo low-confidence
                    if store.code == 'KTOWN' and item.sku == 'SYR-HAZ-750' and day_offset > 7:
                        continue  # Skip older data — sparse usage history

                    usage_rows.append(DailyUsage(
                        store_id=store.id, item_id=item.id,
                        usage_date=usage_date, quantity_used=qty,
                        source='seed',
                    ))

        db.session.add_all(usage_rows)
        db.session.flush()
        print(f"  Created {len(usage_rows)} usage records.")

        # ── Inventory Snapshots (yesterday) ────────────────────
        print("Creating inventory snapshots...")
        snapshot_date = today - timedelta(days=1)
        snapshot_rows = []

        for store in stores:
            mult = volume_multiplier[store.code]
            for item in items:
                # Simulate on-hand as roughly par_level minus some usage
                par = settings_defaults[item.sku][0] * mult
                on_hand = max(0, round(par * random.uniform(0.2, 0.8), 1))

                snapshot_rows.append(InventorySnapshot(
                    store_id=store.id, item_id=item.id,
                    snapshot_date=snapshot_date, quantity_on_hand=on_hand,
                    source='seed',
                ))

        db.session.add_all(snapshot_rows)
        db.session.flush()
        print(f"  Created {len(snapshot_rows)} snapshot records.")

        # ── Example Replenishment Plan (yesterday, completed) ──
        print("Creating example replenishment plan...")
        plan = ReplenishmentPlan(
            plan_date=today - timedelta(days=1),
            status='completed',
            generated_at=datetime.now(timezone.utc) - timedelta(days=1),
            generated_by_user_id=admin.id,
            notes='Seed data example plan',
        )
        db.session.add(plan)
        db.session.flush()

        plan_lines = []
        statuses_pool = ['delivered', 'delivered', 'delivered', 'delivered', 'shorted']

        for store in stores:
            mult = volume_multiplier[store.code]
            for item in items:
                par = settings_defaults[item.sku][0] * mult
                base = base_usage[item.sku] * mult
                recommended = max(0, round(par - par * random.uniform(0.2, 0.6) + base, 1))

                status = random.choice(statuses_pool)
                actual = recommended if status == 'delivered' else round(recommended * 0.5, 1)

                # Determine confidence
                confidence = 'high'
                warnings = []
                explanation = 'Based on 7-day average usage and current on-hand.'

                if store.code == 'KTOWN' and item.sku == 'SYR-HAZ-750':
                    confidence = 'low'
                    warnings = ['sparse_usage_history', 'low_confidence']
                    explanation = 'Low confidence due to limited recent usage history. Used par level fallback.'

                if recommended > par * 2:
                    warnings.append('unusual_recommendation')

                plan_lines.append(ReplenishmentPlanLine(
                    plan_id=plan.id, store_id=store.id, item_id=item.id,
                    recommended_quantity=recommended, actual_quantity=actual,
                    status=status, confidence_level=confidence,
                    explanation_text=explanation, warning_flags=warnings,
                    last_status_change_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 12)),
                ))

        db.session.add_all(plan_lines)
        db.session.commit()
        print(f"  Created plan with {len(plan_lines)} lines.")

        print("\nSeed complete!")
        print(f"  Users: {User.query.count()}")
        print(f"  Stores: {Store.query.count()}")
        print(f"  Items: {InventoryItem.query.count()}")
        print(f"  Store Item Settings: {StoreItemSetting.query.count()}")
        print(f"  Daily Usage Records: {DailyUsage.query.count()}")
        print(f"  Inventory Snapshots: {InventorySnapshot.query.count()}")
        print(f"  Plans: {ReplenishmentPlan.query.count()}")
        print(f"  Plan Lines: {ReplenishmentPlanLine.query.count()}")
        print("\nLogin credentials:")
        print("  Admin: admin@yeems.com / admin123")
        print("  Warehouse: warehouse@yeems.com / warehouse123")


if __name__ == '__main__':
    seed()
