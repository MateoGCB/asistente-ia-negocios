"""Shared fixtures for the whole test suite.

IMPORTANT: the environment variables below MUST be set before importing anything from the app.
- security.py reads SECRET_KEY when it is imported (and load_dotenv() never overrides a variable
  that already exists, so the real .env is ignored for SECRET_KEY).
- database.py builds its engine from DATABASE_URL when it is imported, and main.py runs
  create_all() on that engine. Pointing it to an in-memory SQLite means importing main
  never creates or touches the real businesses.db.
Every test then gets its OWN fresh SQLite file (a copy of an empty template, see db_engine)
through a get_db override.
"""
import os

os.environ["SECRET_KEY"] = "test-secret-key-not-used-anywhere-else"
os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, only used by main.py's import-time create_all
os.environ["CORS_ORIGINS"] = ""  # empty -> the default origin, whatever the developer's .env says

import copy
import hashlib
import itertools
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import security
from database import Base, get_db
from main import app
from models.business_models import Business_db
from models.menu_models import MenuItem_db
from models.order_models import Order_db, OrderItem_db

# bcrypt is slow ON PURPOSE (it makes brute force expensive). Tests do not need that protection,
# so ONLY here we use the minimum cost (4 rounds instead of the default 12). This updates the same
# pwd_context object that user_services uses; production (security.py) is not modified.
security.pwd_context.update(bcrypt__rounds=4)

PROJECT_DIR = Path(__file__).resolve().parent.parent
REAL_DB_PATH = PROJECT_DIR / "businesses.db"

# All test data is fictitious: example.com is a domain reserved for documentation and tests
TEST_PASSWORD = "test-password-123"
TEST_CUSTOMER = {"customer_name": "Cliente Prueba", "customer_phone": "11 0000-0000"}


# ---------------------------------------------------------------- real DB guard

def _fingerprint(path: Path) -> tuple | None:
    # None means "the file does not exist" (e.g. a fresh clone): it must still not exist afterwards
    if not path.exists():
        return None
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def real_db_untouched():
    """Runs once around the WHOLE session: the real businesses.db must end exactly as it started."""
    before = _fingerprint(REAL_DB_PATH)
    yield before
    after = _fingerprint(REAL_DB_PATH)
    assert after == before, f"The real database changed during the tests: {before} -> {after}"


# ---------------------------------------------------------------- per-test database and client

def _sqlite_engine(path: Path):
    return create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})


@pytest.fixture(scope="session")
def template_db(tmp_path_factory) -> Path:
    """Creates the tables ONCE per session in an empty template file (create_all is the slow part)."""
    path = tmp_path_factory.mktemp("template") / "template.db"
    engine = _sqlite_engine(path)
    Base.metadata.create_all(bind=engine)
    engine.dispose()  # closes the file so it can be copied safely
    return path


@pytest.fixture
def db_engine(request, tmp_path, template_db):
    # Each test gets its OWN copy of a template: a separate FILE (not memory, so real threads can
    # share it), so isolation is the same as creating it from scratch, only faster.
    # Tests that use the "shop" scenario start from the shop template (scenario already built).
    # It is requested HERE, before the client fixture installs its get_db override.
    if "shop" in request.fixturenames:
        source = request.getfixturevalue("shop_template").path
    else:
        source = template_db
    test_db = tmp_path / "test.db"
    shutil.copyfile(source, test_db)
    engine = _sqlite_engine(test_db)
    yield engine
    engine.dispose()  # releases the file (Windows cannot delete a file that is still open)


def _session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def _api_client(session_factory):
    # Every request (including get_current_user, which also depends on get_db) uses the given DB.
    # The previous overrides are restored at the end (not just cleared), so this can be nested safely.
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def session_factory(db_engine):
    return _session_factory(db_engine)


@pytest.fixture
def db_session(session_factory):
    """Direct access to the test DB, to check what was saved or to prepare data by hand."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def client(session_factory):
    with _api_client(session_factory) as test_client:
        yield test_client


# ---------------------------------------------------------------- helpers (fictitious data only)

@dataclass
class TestUser:
    __test__ = False  # tells pytest this is not a test class despite its name

    id: int
    name: str
    email: str
    password: str
    headers: dict


@pytest.fixture
def make_user(client):
    """Registers + logs in a new user and returns a TestUser with its Authorization headers."""
    counter = itertools.count(1)

    def _make_user(name: str | None = None, password: str = TEST_PASSWORD) -> TestUser:
        n = next(counter)
        name = name or f"Usuario {n}"
        email = f"usuario{n}@example.com"
        response = client.post("/auth/register", json={"name": name, "email": email, "password": password})
        assert response.status_code == 201, response.text
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        return TestUser(id=response.json()["id"], name=name, email=email, password=password, headers=headers)

    return _make_user


@pytest.fixture
def user_a(make_user) -> TestUser:
    return make_user(name="Dueña A")


@pytest.fixture
def user_b(make_user) -> TestUser:
    return make_user(name="Dueño B")


@pytest.fixture
def create_business(client):
    def _create_business(user: TestUser, name: str = "Sucursal Centro", industry: str = "gastronomia") -> dict:
        response = client.post("/businesses/", json={"name": name, "industry": industry}, headers=user.headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_business


@pytest.fixture
def create_menu(client):
    def _create_menu(user: TestUser, name: str = "Menú de prueba") -> dict:
        response = client.post("/menus/", json={"name": name}, headers=user.headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_menu


@pytest.fixture
def create_item(client):
    def _create_item(
        user: TestUser,
        menu_id: int,
        name: str = "Plato de prueba",
        price: str = "1000.00",
        category: str = "plato_principal",
        description: str = "Descripción ficticia",
    ) -> dict:
        body = {"name": name, "description": description, "price": price, "category": category}
        response = client.post(f"/menus/{menu_id}/items", json=body, headers=user.headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_item


@pytest.fixture
def assign_menu(client):
    def _assign_menu(user: TestUser, business_id: int, menu_id: int) -> dict:
        response = client.patch(f"/businesses/{business_id}", json={"menu_id": menu_id}, headers=user.headers)
        assert response.status_code == 200, response.text
        return response.json()

    return _assign_menu


@pytest.fixture
def place_order(client):
    """Sends a public order. Returns the raw response: error cases are part of what we test."""
    def _place_order(slug: str, items: list[tuple[int, int]], **overrides):
        body = {
            **TEST_CUSTOMER,
            "items": [{"menu_item_id": item_id, "quantity": quantity} for item_id, quantity in items],
            **overrides,
        }
        return client.post(f"/public/{slug}/orders", json=body)

    return _place_order


@pytest.fixture
def insert_order(db_session):
    """Inserts an order DIRECTLY in the test DB (skipping the API), e.g. to prepare a state by hand.
    It also moves the branch counter, like create_order does: an order inserted by hand without
    moving it would make every later order of that branch fail with 409 (manual fix: set the
    branch's next_order_number = MAX(number) + 1)."""
    def _insert_order(business_id: int, menu_item_id: int, quantity: int = 1, **order_fields) -> Order_db:
        db_session.expire_all()  # the API may have moved the counter since this session last read it
        business = db_session.get(Business_db, business_id)
        menu_item = db_session.get(MenuItem_db, menu_item_id)
        number = business.next_order_number
        business.next_order_number = number + 1
        order = Order_db(
            business_id=business_id,
            number=number,
            customer_name=TEST_CUSTOMER["customer_name"],
            customer_phone=TEST_CUSTOMER["customer_phone"],
            total=menu_item.price * quantity,
            items=[OrderItem_db(menu_item_id=menu_item.id, item_name=menu_item.name, unit_price=menu_item.price, quantity=quantity)],
            **order_fields,
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        return order

    return _insert_order


@dataclass
class Shop:
    __test__ = False

    owner: TestUser
    business: dict
    menu: dict
    items: list[dict]


@dataclass
class ShopTemplate:
    path: Path
    owner_id: int
    business: dict
    menu: dict
    items: list[dict]


# Its own email, so it never collides with the users that make_user registers (usuarioN@example.com)
SHOP_OWNER = {"name": "Dueña Shop", "email": "duena.shop@example.com", "password": TEST_PASSWORD}


@pytest.fixture(scope="session")
def shop_template(template_db, tmp_path_factory) -> ShopTemplate:
    """Builds the "shop" scenario ONCE per session THROUGH THE API (end to end: register, login,
    business, menu, two items, menu assigned) and keeps the resulting DB file as a second template."""
    path = tmp_path_factory.mktemp("shop_template") / "shop.db"
    shutil.copyfile(template_db, path)
    engine = _sqlite_engine(path)

    with _api_client(_session_factory(engine)) as api:
        def ok(response, status=201):
            assert response.status_code == status, response.text
            return response.json()

        owner = ok(api.post("/auth/register", json=SHOP_OWNER))
        token = ok(api.post("/auth/login", json={k: SHOP_OWNER[k] for k in ("email", "password")}), 200)["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        business = ok(api.post("/businesses/", json={"name": "Pizzería de Prueba", "industry": "gastronomia"}, headers=headers))
        menu = ok(api.post("/menus/", json={"name": "Carta de Prueba"}, headers=headers))
        items = [
            ok(api.post(f"/menus/{menu['id']}/items", headers=headers, json={
                "name": "Pizza Muzzarella", "description": "Descripción ficticia", "price": "8500.00", "category": "plato_principal"})),
            ok(api.post(f"/menus/{menu['id']}/items", headers=headers, json={
                "name": "Café con leche", "description": "Descripción ficticia", "price": "3500.50", "category": "cafeteria"})),
        ]
        business = ok(api.patch(f"/businesses/{business['id']}", json={"menu_id": menu["id"]}, headers=headers), 200)

    engine.dispose()  # closes the file so every test can copy it
    return ShopTemplate(path=path, owner_id=owner["id"], business=business, menu=menu, items=items)


@pytest.fixture
def shop(client, shop_template) -> Shop:
    """A ready-to-sell branch: business + menu with two items (8500.00 and 3500.50), menu assigned.
    The test DB is already a copy of the shop template (see db_engine); here we only log in."""
    login = client.post("/auth/login", json={k: SHOP_OWNER[k] for k in ("email", "password")})
    assert login.status_code == 200, "the test DB is not a copy of the shop template"
    owner = TestUser(
        id=shop_template.owner_id,
        name=SHOP_OWNER["name"],
        email=SHOP_OWNER["email"],
        password=SHOP_OWNER["password"],
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    # deepcopy: a test that edits these dicts must not affect the next test
    return Shop(
        owner=owner,
        business=copy.deepcopy(shop_template.business),
        menu=copy.deepcopy(shop_template.menu),
        items=copy.deepcopy(shop_template.items),
    )
