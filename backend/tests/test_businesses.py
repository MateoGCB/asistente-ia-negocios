import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from models.business_models import Business_db

# Exactly the fields of the Business response schema: never owner_id nor next_order_number
BUSINESS_KEYS = {"id", "name", "industry", "slug", "pickup_timeout_hours", "menu_id"}


# ---------------------------------------------------------------- create, list, get

def test_create_business_returns_201_with_defaults(client, user_a):
    response = client.post("/businesses/", json={"name": "Sucursal Norte", "industry": "gastronomia"}, headers=user_a.headers)

    assert response.status_code == 201
    data = response.json()
    assert set(data) == BUSINESS_KEYS
    assert data["name"] == "Sucursal Norte"
    assert data["industry"] == "gastronomia"
    assert data["slug"] == "sucursal-norte"
    assert data["pickup_timeout_hours"] == 24
    assert data["menu_id"] is None


def test_create_business_stores_the_owner_from_the_token(client, user_a, db_session):
    created = client.post("/businesses/", json={"name": "Sucursal", "industry": "gastronomia"}, headers=user_a.headers).json()

    stored = db_session.get(Business_db, created["id"])
    assert stored.owner_id == user_a.id
    assert stored.deleted_at is None
    assert stored.next_order_number == 1


def test_list_returns_only_my_businesses(client, user_a, user_b, create_business):
    mine = [create_business(user_a, name="A Uno"), create_business(user_a, name="A Dos")]
    create_business(user_b, name="B Uno")

    response = client.get("/businesses/", headers=user_a.headers)

    assert response.status_code == 200
    assert sorted(b["id"] for b in response.json()) == sorted(b["id"] for b in mine)
    assert all(set(b) == BUSINESS_KEYS for b in response.json())


def test_get_business_by_id(client, user_a, create_business):
    created = create_business(user_a)

    response = client.get(f"/businesses/{created['id']}", headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_business_returns_404(client, user_a):
    assert client.get("/businesses/9999", headers=user_a.headers).status_code == 404


# ---------------------------------------------------------------- patch

def test_patch_changes_only_the_field_sent(client, user_a, create_business):
    created = create_business(user_a, name="Nombre Viejo", industry="gastronomia")

    response = client.patch(f"/businesses/{created['id']}", json={"name": "Nombre Nuevo"}, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == {**created, "name": "Nombre Nuevo"}


def test_patch_with_nulls_is_ignored_and_does_not_break_the_business(client, user_a, create_business):
    # exclude_none: a null sent on purpose must not erase NOT NULL columns
    created = create_business(user_a)
    body = {"name": None, "industry": None, "menu_id": None, "pickup_timeout_hours": None}

    response = client.patch(f"/businesses/{created['id']}", json=body, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == created
    # And it can still be read (a broken row with name NULL would fail the response schema)
    assert client.get(f"/businesses/{created['id']}", headers=user_a.headers).json() == created


def test_client_cannot_choose_id_owner_or_slug_on_create(client, user_a, user_b, db_session):
    body = {"name": "Sucursal Sur", "industry": "gastronomia", "id": 999, "owner_id": user_b.id, "slug": "slug-elegido"}

    data = client.post("/businesses/", json=body, headers=user_a.headers).json()

    assert data["id"] != 999
    assert data["slug"] == "sucursal-sur"
    assert db_session.get(Business_db, data["id"]).owner_id == user_a.id


def test_client_cannot_change_id_owner_or_slug_on_patch(client, user_a, user_b, create_business, db_session):
    created = create_business(user_a)
    body = {"id": 999, "owner_id": user_b.id, "slug": "slug-elegido"}

    response = client.patch(f"/businesses/{created['id']}", json=body, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == created
    assert db_session.get(Business_db, created["id"]).owner_id == user_a.id
    assert client.get("/businesses/", headers=user_b.headers).json() == []


# ---------------------------------------------------------------- pickup_timeout_hours

@pytest.mark.parametrize("hours", [1, 24, 72])
def test_pickup_timeout_valid_values_are_saved(client, user_a, create_business, hours):
    created = create_business(user_a)

    response = client.patch(f"/businesses/{created['id']}", json={"pickup_timeout_hours": hours}, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json()["pickup_timeout_hours"] == hours


@pytest.mark.parametrize("hours", [0, 73, -5])
def test_pickup_timeout_out_of_range_returns_422_and_keeps_the_value(client, user_a, create_business, hours):
    created = create_business(user_a)

    response = client.patch(f"/businesses/{created['id']}", json={"pickup_timeout_hours": hours}, headers=user_a.headers)

    assert response.status_code == 422
    assert client.get(f"/businesses/{created['id']}", headers=user_a.headers).json()["pickup_timeout_hours"] == 24


@pytest.mark.parametrize("hours", [0, 73])
def test_database_check_rejects_pickup_timeout_out_of_range(user_a, create_business, db_session, hours):
    # Second barrier: even writing directly to the DB (skipping the schema), the CHECK constraint says no
    created = create_business(user_a)

    with pytest.raises(IntegrityError, match="ck_business_pickup_timeout_range"):
        db_session.execute(update(Business_db).where(Business_db.id == created["id"]).values(pickup_timeout_hours=hours))
        db_session.commit()
    db_session.rollback()

    assert db_session.get(Business_db, created["id"]).pickup_timeout_hours == 24


# ---------------------------------------------------------------- name and industry validation

INVALID_FIELDS = [
    ("name", ""),
    ("name", "   "),        # only spaces: stripped to "" -> too short
    ("name", "x" * 101),
    ("industry", ""),
    ("industry", "   "),
    ("industry", "x" * 61),
]

VALID_EDGES = [
    ("name", "X", "X"),
    ("name", "x" * 100, "x" * 100),
    ("name", "  Sucursal Oeste  ", "Sucursal Oeste"),  # spaces at the edges are removed
    ("industry", "g", "g"),
    ("industry", "x" * 60, "x" * 60),
    ("industry", "  cafeteria  ", "cafeteria"),
]


@pytest.mark.parametrize("field, value", INVALID_FIELDS)
def test_create_with_invalid_name_or_industry_returns_422_and_saves_nothing(client, user_a, db_session, field, value):
    body = {"name": "Sucursal", "industry": "gastronomia", field: value}

    response = client.post("/businesses/", json=body, headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(Business_db).count() == 0


@pytest.mark.parametrize("field, value", INVALID_FIELDS)
def test_patch_with_invalid_name_or_industry_returns_422_and_keeps_the_value(client, user_a, create_business, field, value):
    created = create_business(user_a)

    response = client.patch(f"/businesses/{created['id']}", json={field: value}, headers=user_a.headers)

    assert response.status_code == 422
    assert client.get(f"/businesses/{created['id']}", headers=user_a.headers).json() == created


@pytest.mark.parametrize("field, value, saved", VALID_EDGES)
def test_create_accepts_edge_values_and_strips_spaces(client, user_a, field, value, saved):
    body = {"name": "Sucursal", "industry": "gastronomia", field: value}

    response = client.post("/businesses/", json=body, headers=user_a.headers)

    assert response.status_code == 201
    assert response.json()[field] == saved


@pytest.mark.parametrize("field, value, saved", VALID_EDGES)
def test_patch_accepts_edge_values_and_strips_spaces(client, user_a, create_business, field, value, saved):
    created = create_business(user_a)

    response = client.patch(f"/businesses/{created['id']}", json={field: value}, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json()[field] == saved


# ---------------------------------------------------------------- pickup_timeout_hours on create

def test_create_without_pickup_timeout_uses_24(client, user_a, db_session):
    data = client.post("/businesses/", json={"name": "Sucursal", "industry": "gastronomia"}, headers=user_a.headers).json()

    assert data["pickup_timeout_hours"] == 24
    assert db_session.get(Business_db, data["id"]).pickup_timeout_hours == 24


@pytest.mark.parametrize("hours", [1, 2, 72])
def test_create_with_valid_pickup_timeout_saves_it(client, user_a, db_session, hours):
    body = {"name": "Sucursal", "industry": "gastronomia", "pickup_timeout_hours": hours}

    data = client.post("/businesses/", json=body, headers=user_a.headers).json()

    assert data["pickup_timeout_hours"] == hours
    assert db_session.get(Business_db, data["id"]).pickup_timeout_hours == hours


@pytest.mark.parametrize("hours", [0, 73, -5])
def test_create_with_pickup_timeout_out_of_range_returns_422_and_saves_nothing(client, user_a, db_session, hours):
    body = {"name": "Sucursal", "industry": "gastronomia", "pickup_timeout_hours": hours}

    response = client.post("/businesses/", json=body, headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(Business_db).count() == 0


# ---------------------------------------------------------------- API rule about null
# In an OPTIONAL field with a default, null means "not sent" (create: use the default; PATCH: ignore).
# In a REQUIRED field, null is an error (422).

def test_create_with_null_pickup_timeout_uses_the_default_24(client, user_a, db_session):
    body = {"name": "Sucursal", "industry": "gastronomia", "pickup_timeout_hours": None}

    response = client.post("/businesses/", json=body, headers=user_a.headers)

    assert response.status_code == 201
    assert response.json()["pickup_timeout_hours"] == 24
    assert db_session.get(Business_db, response.json()["id"]).pickup_timeout_hours == 24


@pytest.mark.parametrize("required_field", ["name", "industry"])
def test_create_with_null_in_a_required_field_returns_422(client, user_a, db_session, required_field):
    body = {"name": "Sucursal", "industry": "gastronomia", required_field: None}

    response = client.post("/businesses/", json=body, headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(Business_db).count() == 0
