import pytest
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

from warehouse_app import create_app
from warehouse_app.extensions import db as _db
from warehouse_app.models.user import User
from warehouse_app.models.store import Store
from warehouse_app.models.inventory_item import InventoryItem
from warehouse_app.models.store_item_setting import StoreItemSetting
from warehouse_app.models.daily_usage import DailyUsage
from warehouse_app.models.inventory_snapshot import InventorySnapshot
from warehouse_app.models.replenishment_plan import ReplenishmentPlan
from warehouse_app.models.replenishment_plan_line import ReplenishmentPlanLine


@pytest.fixture(scope='session')
def app():
    """Create the Flask application for testing."""
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User(
        full_name='Test Admin',
        email='admin@test.com',
        password_hash=generate_password_hash('admin123'),
        role='admin',
        active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def warehouse_user(db):
    """Create a warehouse user."""
    user = User(
        full_name='Test Warehouse',
        email='warehouse@test.com',
        password_hash=generate_password_hash('warehouse123'),
        role='warehouse',
        active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_stores(db):
    """Create sample stores."""
    stores = [
        Store(name='Gardena', code='GARDENA', active=True),
        Store(name='K-Town', code='KTOWN', active=True),
    ]
    db.session.add_all(stores)
    db.session.commit()
    return stores


@pytest.fixture
def sample_items(db):
    """Create sample inventory items."""
    items = [
        InventoryItem(item_name='Whole Milk', sku='MILK-WHL', category='Dairy',
                       unit_of_measure='gallon', case_pack_quantity=4, active=True),
        InventoryItem(item_name='Oat Milk', sku='MILK-OAT', category='Dairy',
                       unit_of_measure='half_gallon', case_pack_quantity=6, active=True),
        InventoryItem(item_name='Espresso Beans', sku='BEA-HSE', category='Coffee',
                       unit_of_measure='bag', case_pack_quantity=4, active=True),
        InventoryItem(item_name='Cup 12oz', sku='CUP-12', category='Supplies',
                       unit_of_measure='sleeve', case_pack_quantity=20, active=True),
    ]
    db.session.add_all(items)
    db.session.commit()
    return items


@pytest.fixture
def sample_settings(db, sample_stores, sample_items):
    """Create store item settings for all store-item combinations."""
    settings = []
    for store in sample_stores:
        for item in sample_items:
            setting = StoreItemSetting(
                store_id=store.id, item_id=item.id,
                par_level=10, safety_stock=2, reorder_threshold=3,
                min_send_quantity=2, rounding_rule='round_up_case_pack',
                active=True,
            )
            settings.append(setting)
    db.session.add_all(settings)
    db.session.commit()
    return settings


@pytest.fixture
def sample_usage(db, sample_stores, sample_items):
    """Create 7 days of daily usage for all store-item pairs."""
    today = date.today()
    records = []
    for store in sample_stores:
        for item in sample_items:
            for d in range(1, 8):
                records.append(DailyUsage(
                    store_id=store.id, item_id=item.id,
                    usage_date=today - timedelta(days=d),
                    quantity_used=5.0, source='test',
                ))
    db.session.add_all(records)
    db.session.commit()
    return records


@pytest.fixture
def sample_snapshots(db, sample_stores, sample_items):
    """Create inventory snapshots for all store-item pairs."""
    today = date.today()
    records = []
    for store in sample_stores:
        for item in sample_items:
            records.append(InventorySnapshot(
                store_id=store.id, item_id=item.id,
                snapshot_date=today - timedelta(days=1),
                quantity_on_hand=3.0, source='test',
            ))
    db.session.add_all(records)
    db.session.commit()
    return records


@pytest.fixture
def sample_plan(db, sample_stores, sample_items, sample_settings,
                sample_usage, sample_snapshots):
    """Generate a plan for today with lines for all store-item pairs."""
    from warehouse_app.services.plan_generation import generate_plan
    result = generate_plan(date.today(), user_id=None, regenerate=False)
    return result['plan']


def _login(client, email, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'email': email, 'password': password,
    }, follow_redirects=True)


@pytest.fixture
def admin_client(client, admin_user):
    """Test client logged in as admin."""
    _login(client, 'admin@test.com', 'admin123')
    return client


@pytest.fixture
def warehouse_client(client, warehouse_user):
    """Test client logged in as warehouse user."""
    _login(client, 'warehouse@test.com', 'warehouse123')
    return client
