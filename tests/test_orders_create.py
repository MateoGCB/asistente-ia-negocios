"""POST /public/{slug}/orders: the server computes everything, and an order is created whole or not at all."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from models.business_models import Business_db
from models.menu_models import MenuItem_db
from models.order_models import Order_db, OrderItem_db, OrderStatus
from tests.conftest import TEST_CUSTOMER
from utils.datetime_utils import utc_now

PUBLIC_ORDER_KEYS = {"number", "status", "total", "customer_name", "created_at", "items"}
PUBLIC_ORDER_ITEM_KEYS = {"name", "unit_price", "quantity"}
NOT_AVAILABLE = {"detail": "One or more items are not available"}


# ---------------------------------------------------------------- helpers to look inside the test DB

def counter(db_session, business_id: int) -> int:
    db_session.expire_all()  # forget cached rows: read what the API really wrote
    return db_session.get(Business_db, business_id).next_order_number


def saved_rows(db_session) -> tuple[int, int]:
    db_session.expire_all()
    return db_session.query(Order_db).count(), db_session.query(OrderItem_db).count()


def assert_nothing_saved(db_session, business_id: int):
    # "All or nothing": no order, no items, and the counter did not move
    assert saved_rows(db_session) == (0, 0)
    assert counter(db_session, business_id) == 1


# ---------------------------------------------------------------- valid order

def test_valid_order_is_created_with_total_computed_by_the_server(shop, place_order, db_session):
    pizza, coffee = shop.items  # 8500.00 and 3500.50

    response = place_order(shop.business["slug"], [(pizza["id"], 1), (coffee["id"], 2)])

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["number"] == 1
    assert data["total"] == "15501.00"  # 8500 + 2 x 3500.50, computed by hand
    assert data["customer_name"] == TEST_CUSTOMER["customer_name"]

    order = db_session.query(Order_db).one()
    assert order.total == Decimal("15501.00")
    # Snapshots: name and price copied from the menu at the moment of the order
    snapshots = sorted((i.item_name, i.unit_price, i.quantity) for i in order.items)
    assert snapshots == [("Café con leche", Decimal("3500.50"), 2), ("Pizza Muzzarella", Decimal("8500.00"), 1)]


def test_public_response_has_only_the_public_keys(shop, place_order):
    data = place_order(shop.business["slug"], [(shop.items[0]["id"], 1)]).json()

    # No order id, no phone, no notes, no business or owner data
    assert set(data) == PUBLIC_ORDER_KEYS
    assert all(set(item) == PUBLIC_ORDER_ITEM_KEYS for item in data["items"])
    assert data["items"] == [{"name": "Pizza Muzzarella", "unit_price": "8500.00", "quantity": 1}]
    # created_at is sent explicitly as UTC
    assert datetime.fromisoformat(data["created_at"]).utcoffset() == timedelta(0)


def test_order_numbers_are_per_branch(shop, place_order, create_business, assign_menu):
    other = create_business(shop.owner, name="Otra Sucursal")
    assign_menu(shop.owner, other["id"], shop.menu["id"])  # same menu, different branch
    item = [(shop.items[0]["id"], 1)]

    numbers = [
        place_order(shop.business["slug"], item).json()["number"],
        place_order(shop.business["slug"], item).json()["number"],
        place_order(other["slug"], item).json()["number"],
    ]

    assert numbers == [1, 2, 1]


def test_fields_invented_by_the_client_are_ignored(client, shop, db_session):
    pizza = shop.items[0]
    body = {
        **TEST_CUSTOMER,
        "items": [{"menu_item_id": pizza["id"], "quantity": 2, "price": "1.00", "unit_price": "1.00"}],
        "total": "1.00",
        "status": "delivered",
        "number": 999,
    }

    response = client.post(f"/public/{shop.business['slug']}/orders", json=body)

    assert response.status_code == 201
    data = response.json()
    assert (data["total"], data["status"], data["number"]) == ("17000.00", "pending", 1)
    assert data["items"][0]["unit_price"] == "8500.00"
    assert db_session.query(OrderItem_db).one().unit_price == Decimal("8500.00")


def test_later_menu_changes_do_not_alter_an_existing_order(client, shop, place_order, db_session):
    pizza = shop.items[0]
    place_order(shop.business["slug"], [(pizza["id"], 1)])

    client.patch(
        f"/menus/{shop.menu['id']}/items/{pizza['id']}",
        json={"name": "Pizza Renombrada", "price": "9999.00"},
        headers=shop.owner.headers,
    )

    order = db_session.query(Order_db).one()
    detail = client.get(f"/businesses/{shop.business['id']}/orders/{order.id}", headers=shop.owner.headers).json()
    assert detail["items"] == [{"name": "Pizza Muzzarella", "unit_price": "8500.00", "quantity": 1}]
    assert detail["total"] == "8500.00"


# ---------------------------------------------------------------- items that cannot be ordered

@pytest.fixture
def unorderable_item_ids(client, shop, user_b, create_menu, create_item):
    """Three different reasons an item cannot be ordered at this branch."""
    menu_of_b = create_menu(user_b, name="Menú de B")
    item_of_b = create_item(user_b, menu_of_b["id"], name="Plato de B")
    sold_out = shop.items[1]
    client.patch(f"/menus/{shop.menu['id']}/items/{sold_out['id']}", json={"available": False}, headers=shop.owner.headers)
    return {"nonexistent": 9999, "of_another_business": item_of_b["id"], "sold_out": sold_out["id"]}


@pytest.mark.parametrize("reason", ["nonexistent", "of_another_business", "sold_out"])
def test_unorderable_item_gives_the_same_409_and_saves_nothing(shop, place_order, db_session, unorderable_item_ids, reason):
    # Mixed with a valid item: the whole order is rejected, not just the bad line.
    # Same body in the three cases: a customer cannot probe which ids exist in other businesses.
    items = [(shop.items[0]["id"], 1), (unorderable_item_ids[reason], 1)]

    response = place_order(shop.business["slug"], items)

    assert response.status_code == 409
    assert response.json() == NOT_AVAILABLE
    assert_nothing_saved(db_session, shop.business["id"])


# ---------------------------------------------------------------- 422: invalid input

MISSING = object()  # marks a key that must be removed from the body

INVALID_CASES = {
    "quantity_0": {"quantity": 0},
    "quantity_negative": {"quantity": -1},
    "quantity_51": {"quantity": 51},
    "empty_items": {"items": []},
    "31_items": {"items": [{"menu_item_id": n, "quantity": 1} for n in range(1, 32)]},
    "repeated_item": {"repeat_item": True},
    "name_1_char": {"customer_name": "A"},
    "name_101_chars": {"customer_name": "x" * 101},
    "name_only_spaces": {"customer_name": "      "},
    "phone_short": {"customer_phone": "12345"},
    "phone_long": {"customer_phone": "1" * 21},
    "phone_letters": {"customer_phone": "11 0000 ABCD"},
    "phone_plus_in_the_middle": {"customer_phone": "11+00000000"},
    "phone_double_plus": {"customer_phone": "++54110000000"},
    "phone_without_digits": {"customer_phone": "------"},
    "phone_5_digits_padded": {"customer_phone": "+1-2-3-4-5"},  # long enough, but only 5 digits
    "phone_16_digits": {"customer_phone": "1234567890123456"},
    "phone_16_digits_with_plus": {"customer_phone": "+5493511234567890"},
    "phone_double_space": {"customer_phone": "11  0000-0000"},
    "phone_double_hyphen": {"customer_phone": "11 0000--0000"},
    "notes_301": {"notes": "x" * 301},
    "phone_missing": {"customer_phone": MISSING},
}


def build_body(item_id: int, case: dict) -> dict:
    body = {**TEST_CUSTOMER, "items": [{"menu_item_id": item_id, "quantity": case.get("quantity", 1)}]}
    if case.get("repeat_item"):
        body["items"] = [{"menu_item_id": item_id, "quantity": 1}, {"menu_item_id": item_id, "quantity": 2}]
    for key in ("customer_name", "customer_phone", "notes", "items"):
        if key in case:
            body[key] = case[key]
    return {key: value for key, value in body.items() if value is not MISSING}


@pytest.mark.parametrize("case", INVALID_CASES.values(), ids=INVALID_CASES.keys())
def test_invalid_order_returns_422_and_saves_nothing(client, shop, db_session, case):
    body = build_body(shop.items[0]["id"], case)

    response = client.post(f"/public/{shop.business['slug']}/orders", json=body)

    assert response.status_code == 422
    assert_nothing_saved(db_session, shop.business["id"])


VALID_EDGES = {
    "name_2_chars": {"customer_name": "Al"},
    "name_100_chars": {"customer_name": "x" * 100},
    "phone_6_digits": {"customer_phone": "123456"},
    "phone_20_chars": {"customer_phone": "+54 11 0000-0000 000"},  # 20 characters, 15 digits
    "phone_15_digits": {"customer_phone": "123456789012345"},
    "phone_15_digits_with_plus": {"customer_phone": "+549351123456789"},
    "phone_argentine_mobile": {"customer_phone": "+54 9 351 123-4567"},
    "phone_mixed_separator": {"customer_phone": "351 - 1234567"},  # " - " is not a repeated separator
    "notes_300": {"notes": "x" * 300},
    "quantity_50": {"quantity": 50},
}


@pytest.mark.parametrize("case", VALID_EDGES.values(), ids=VALID_EDGES.keys())
def test_valid_edge_values_are_accepted(client, shop, case):
    body = build_body(shop.items[0]["id"], case)

    response = client.post(f"/public/{shop.business['slug']}/orders", json=body)

    assert response.status_code == 201, response.text


def test_order_with_30_items_is_accepted(shop, place_order, db_session):
    for n in range(28):  # the shop already has 2 items: add 28 more directly in the DB
        db_session.add(MenuItem_db(menu_id=shop.menu["id"], name=f"Extra {n}", description="d", price=Decimal("10.00"), category="postre"))
    db_session.commit()
    item_ids = [i.id for i in db_session.query(MenuItem_db).filter(MenuItem_db.menu_id == shop.menu["id"])]
    assert len(item_ids) == 30

    response = place_order(shop.business["slug"], [(item_id, 1) for item_id in item_ids])

    assert response.status_code == 201
    assert len(response.json()["items"]) == 30


@pytest.mark.parametrize("notes", ["", "     "])
def test_empty_notes_are_saved_as_null(shop, place_order, db_session, notes):
    assert place_order(shop.business["slug"], [(shop.items[0]["id"], 1)], notes=notes).status_code == 201

    assert db_session.query(Order_db).one().notes is None


# ---------------------------------------------------------------- maximum total

@pytest.mark.parametrize("price, expected_status", [("200000.00", 201), ("200000.01", 422)])
def test_maximum_total_is_10_million(shop, create_item, place_order, db_session, price, expected_status):
    # 50 x 200000.00 = 10,000,000.00 exactly (accepted); 50 x 200000.01 = 10,000,000.50 (rejected)
    expensive = create_item(shop.owner, shop.menu["id"], name="Banquete", price=price)

    response = place_order(shop.business["slug"], [(expensive["id"], 50)])

    assert response.status_code == expected_status
    if expected_status == 422:
        assert_nothing_saved(db_session, shop.business["id"])
    else:
        assert response.json()["total"] == "10000000.00"


# ---------------------------------------------------------------- branch that cannot take orders

def test_unknown_slug_no_menu_and_archived_give_the_same_404(client, shop, create_business, place_order, db_session):
    item = [(shop.items[0]["id"], 1)]
    without_menu = create_business(shop.owner, name="Sin Menu")
    unknown = place_order("este-slug-no-existe", item)
    no_menu = place_order(without_menu["slug"], item)
    client.delete(f"/businesses/{shop.business['id']}", headers=shop.owner.headers)
    archived = place_order(shop.business["slug"], item)

    assert [unknown.status_code, no_menu.status_code, archived.status_code] == [404, 404, 404]
    assert unknown.json() == no_menu.json() == archived.json()
    assert saved_rows(db_session) == (0, 0)


# ---------------------------------------------------------------- the order counter

def test_errors_do_not_consume_numbers(shop, place_order, create_item, db_session):
    slug, pizza = shop.business["slug"], shop.items[0]["id"]
    expensive = create_item(shop.owner, shop.menu["id"], name="Banquete", price="300000.00")
    assert place_order(slug, [(9999, 1)]).status_code == 409             # unavailable item
    assert place_order(slug, [(pizza, 0)]).status_code == 422            # invalid quantity
    assert place_order(slug, [(expensive["id"], 50)]).status_code == 422  # total too high
    assert counter(db_session, shop.business["id"]) == 1

    first = place_order(slug, [(pizza, 1)]).json()["number"]
    second = place_order(slug, [(pizza, 1)]).json()["number"]

    assert (first, second) == (1, 2)  # no gaps
    assert counter(db_session, shop.business["id"]) == 3


def test_forced_number_collision_returns_409_and_reverts_the_counter(shop, place_order, db_session):
    # Simulates the documented trap: an order inserted by hand WITHOUT moving the counter.
    # The next API order gets number 1 again and hits UNIQUE(business_id, number).
    business_id = shop.business["id"]
    db_session.add(Order_db(business_id=business_id, number=1, total=Decimal("1.00"), **TEST_CUSTOMER))
    db_session.commit()

    response = place_order(shop.business["slug"], [(shop.items[0]["id"], 1)])

    assert response.status_code == 409
    assert response.json() == {"detail": "Could not create the order, please try again"}
    assert counter(db_session, business_id) == 1  # the rollback also undid the increment
    assert saved_rows(db_session) == (1, 0)       # only the hand-made order, no half-saved one

    # The manual fix documented in CLAUDE.md puts the counter after the highest number
    db_session.execute(text(
        "UPDATE business SET next_order_number = "
        "(SELECT COALESCE(MAX(number), 0) + 1 FROM orders WHERE orders.business_id = business.id) "
        "WHERE id = :business_id"
    ), {"business_id": business_id})
    db_session.commit()
    assert place_order(shop.business["slug"], [(shop.items[0]["id"], 1)]).json()["number"] == 2


# ---------------------------------------------------------------- public endpoints do not expire orders

def test_public_endpoints_do_not_trigger_auto_cancel(client, shop, place_order, insert_order, db_session):
    # A ready order overdue by 2 days: only the OWNER side expires orders, never the public side
    overdue = insert_order(shop.business["id"], shop.items[0]["id"], status=OrderStatus.ready, ready_at=utc_now() - timedelta(hours=48))

    assert client.get(f"/public/{shop.business['slug']}/menu").status_code == 200
    assert place_order(shop.business["slug"], [(shop.items[0]["id"], 1)]).status_code == 201

    db_session.expire_all()
    assert db_session.get(Order_db, overdue.id).status == OrderStatus.ready

    # Control: the owner's listing DOES expire it (so the test above is not passing by accident)
    client.get(f"/businesses/{shop.business['id']}/orders", headers=shop.owner.headers)
    db_session.expire_all()
    assert db_session.get(Order_db, overdue.id).status == OrderStatus.cancelled
