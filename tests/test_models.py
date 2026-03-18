"""Tests for model creation and basic relationships."""
from warehouse_app.models.user import User
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting


class TestUserModel:
    def test_create_user(self, db):
        user = User(full_name='Test User', email='test@test.com', role='admin', active=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.check_password('password123')
        assert not user.check_password('wrong')
        assert user.is_admin

    def test_warehouse_role(self, db):
        user = User(full_name='Worker', email='worker@test.com', role='warehouse', active=True)
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

        assert not user.is_admin

    def test_email_unique(self, db):
        import pytest
        u1 = User(full_name='A', email='dup@test.com', role='admin')
        u1.set_password('p')
        u2 = User(full_name='B', email='dup@test.com', role='warehouse')
        u2.set_password('p')
        db.session.add(u1)
        db.session.commit()
        db.session.add(u2)
        with pytest.raises(Exception):
            db.session.commit()


class TestStoreModel:
    def test_create_store(self, db):
        store = Store(name='Test Store', code='TEST', active=True)
        db.session.add(store)
        db.session.commit()
        assert store.id is not None
        assert store.code == 'TEST'


class TestStoreItemSettingModel:
    def test_unique_constraint(self, db, sample_stores, sample_items):
        import pytest
        s1 = StoreItemSetting(store_id=sample_stores[0].id, item_id=sample_items[0].id,
                               par_level=10, safety_stock=2, rounding_rule='none')
        s2 = StoreItemSetting(store_id=sample_stores[0].id, item_id=sample_items[0].id,
                               par_level=5, safety_stock=1, rounding_rule='none')
        db.session.add(s1)
        db.session.commit()
        db.session.add(s2)
        with pytest.raises(Exception):
            db.session.commit()
