"""Owner side: GET /businesses/{id}/orders (active / history / status) and the order detail."""
from datetime import timedelta

import pytest

from models.order_models import CancelReason, OrderStatus
from utils.datetime_utils import utc_now

ACTIVE = [OrderStatus.pending, OrderStatus.confirmed, OrderStatus.preparing, OrderStatus.ready]
CLOSED = [OrderStatus.delivered, OrderStatus.cancelled]
OWNER_ORDER_KEYS = {
    "id", "number", "customer_name", "customer_phone", "notes", "items",
    "total", "status", "created_at", "ready_at", "cancel_reason",
}


def orders_url(business_id: int) -> str:
    return f"/businesses/{business_id}/orders"


@pytest.fixture
def add_order(shop, insert_order):
    """Inserts an order of the shop with a given status and age (minutes ago)."""
    def _add_order(status: OrderStatus, minutes_ago: int = 0, **fields):
        now = utc_now()
        if status == OrderStatus.ready:
            fields.setdefault("ready_at", now)  # recent: it must not expire during the test
        if status == OrderStatus.cancelled:
            fields.setdefault("cancel_reason", CancelReason.owner)
        fields.setdefault("created_at", now - timedelta(minutes=minutes_ago))
        return insert_order(shop.business["id"], shop.items[0]["id"], status=status, **fields)

    return _add_order


def listed_ids(client, shop, **params) -> list[int]:
    response = client.get(orders_url(shop.business["id"]), params=params, headers=shop.owner.headers)
    assert response.status_code == 200, response.text
    return [order["id"] for order in response.json()["items"]]


# ---------------------------------------------------------------- view=active

def test_active_view_shows_only_active_orders_oldest_first(client, shop, add_order):
    # One order per status, created in a shuffled order of age
    ages = {OrderStatus.ready: 50, OrderStatus.delivered: 40, OrderStatus.pending: 30,
            OrderStatus.cancelled: 20, OrderStatus.preparing: 10, OrderStatus.confirmed: 5}
    orders = {status: add_order(status, minutes_ago) for status, minutes_ago in ages.items()}

    ids = listed_ids(client, shop, view="active")

    expected = [orders[s].id for s in (OrderStatus.ready, OrderStatus.pending, OrderStatus.preparing, OrderStatus.confirmed)]
    assert ids == expected


def test_active_view_breaks_ties_by_id(client, shop, add_order, db_session):
    same_moment = utc_now() - timedelta(minutes=5)
    first = add_order(OrderStatus.pending, created_at=same_moment)
    second = add_order(OrderStatus.pending, created_at=same_moment)
    older = add_order(OrderStatus.pending, minutes_ago=30)

    assert listed_ids(client, shop, view="active") == [older.id, first.id, second.id]


def test_active_view_is_not_paginated(client, shop, add_order):
    for _ in range(25):
        add_order(OrderStatus.pending)

    data = client.get(orders_url(shop.business["id"]), params={"view": "active"}, headers=shop.owner.headers).json()

    assert (data["page"], data["page_size"], data["total"], len(data["items"])) == (None, None, 25, 25)


def test_without_parameters_the_active_view_is_used(client, shop, add_order):
    add_order(OrderStatus.pending)
    add_order(OrderStatus.delivered)

    default = client.get(orders_url(shop.business["id"]), headers=shop.owner.headers).json()
    active = client.get(orders_url(shop.business["id"]), params={"view": "active"}, headers=shop.owner.headers).json()

    assert default == active
    assert [o["status"] for o in default["items"]] == ["pending"]


# ---------------------------------------------------------------- view=history

def test_history_view_shows_only_closed_orders_newest_first(client, shop, add_order):
    old_delivered = add_order(OrderStatus.delivered, minutes_ago=30)
    add_order(OrderStatus.pending, minutes_ago=20)
    cancelled = add_order(OrderStatus.cancelled, minutes_ago=10)
    add_order(OrderStatus.ready, minutes_ago=5)
    same_moment = utc_now() - timedelta(minutes=1)
    tie_first = add_order(OrderStatus.delivered, created_at=same_moment)
    tie_second = add_order(OrderStatus.delivered, created_at=same_moment)

    ids = listed_ids(client, shop, view="history")

    # Newest first; on a tie, the higher id first
    assert ids == [tie_second.id, tie_first.id, cancelled.id, old_delivered.id]


def test_history_is_paginated_without_repeating_or_losing_orders(client, shop, add_order):
    closed_ids = {add_order(CLOSED[n % 2], minutes_ago=n).id for n in range(45)}

    pages = []
    for page in (1, 2, 3):
        data = client.get(orders_url(shop.business["id"]), params={"view": "history", "page": page}, headers=shop.owner.headers).json()
        assert (data["page"], data["page_size"], data["total"]) == (page, 20, 45)
        pages.append([o["id"] for o in data["items"]])

    assert [len(p) for p in pages] == [20, 20, 5]
    all_ids = [order_id for page in pages for order_id in page]
    assert len(all_ids) == len(set(all_ids))  # no order repeated between pages
    assert set(all_ids) == closed_ids          # and none lost


def test_history_with_custom_page_size(client, shop, add_order):
    for n in range(7):
        add_order(OrderStatus.delivered, minutes_ago=n)

    data = client.get(orders_url(shop.business["id"]), params={"view": "history", "page": 2, "page_size": 3}, headers=shop.owner.headers).json()

    assert (data["page"], data["page_size"], data["total"], len(data["items"])) == (2, 3, 7, 3)


def test_page_after_the_last_one_is_empty(client, shop, add_order):
    add_order(OrderStatus.delivered)

    data = client.get(orders_url(shop.business["id"]), params={"view": "history", "page": 5}, headers=shop.owner.headers).json()

    assert (data["items"], data["total"]) == ([], 1)


@pytest.mark.parametrize(
    "params",
    [
        {"view": "history", "page_size": 51},
        {"view": "history", "page_size": 0},
        {"view": "history", "page": 0},
        {"view": "active", "status": "pending"},   # view and status together
        {"view": "todos"},                           # unknown view
        {"status": "perdido"},                       # unknown status
    ],
)
def test_invalid_list_parameters_return_422(client, shop, params):
    response = client.get(orders_url(shop.business["id"]), params=params, headers=shop.owner.headers)

    assert response.status_code == 422


# ---------------------------------------------------------------- status filter

def test_status_filter_with_an_active_status_follows_active_rules(client, shop, add_order):
    newer = add_order(OrderStatus.ready, minutes_ago=5)
    older = add_order(OrderStatus.ready, minutes_ago=30)
    add_order(OrderStatus.pending)

    data = client.get(orders_url(shop.business["id"]), params={"status": "ready"}, headers=shop.owner.headers).json()

    assert [o["id"] for o in data["items"]] == [older.id, newer.id]  # oldest first
    assert data["page"] is None                                       # not paginated


def test_status_filter_with_a_closed_status_follows_history_rules(client, shop, add_order):
    older = add_order(OrderStatus.cancelled, minutes_ago=30)
    newer = add_order(OrderStatus.cancelled, minutes_ago=5)
    add_order(OrderStatus.delivered)

    data = client.get(orders_url(shop.business["id"]), params={"status": "cancelled", "page_size": 1}, headers=shop.owner.headers).json()

    assert [o["id"] for o in data["items"]] == [newer.id]  # newest first
    assert (data["page"], data["page_size"], data["total"]) == (1, 1, 2)
    assert older.id not in [o["id"] for o in data["items"]]


# ---------------------------------------------------------------- detail

def test_order_detail_has_every_field(client, shop, add_order):
    ready_at = utc_now() - timedelta(minutes=10)
    order = add_order(OrderStatus.cancelled, ready_at=ready_at, notes="Sin cebolla")

    response = client.get(f"{orders_url(shop.business['id'])}/{order.id}", headers=shop.owner.headers)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == OWNER_ORDER_KEYS
    assert data["customer_phone"] == order.customer_phone  # the owner DOES see the phone
    assert data["notes"] == "Sin cebolla"
    assert data["cancel_reason"] == "owner"
    assert data["ready_at"] is not None
    assert data["items"] == [{"name": "Pizza Muzzarella", "unit_price": "8500.00", "quantity": 1}]


def test_unknown_order_returns_404(client, shop):
    assert client.get(f"{orders_url(shop.business['id'])}/9999", headers=shop.owner.headers).status_code == 404


# ---------------------------------------------------------------- isolation

@pytest.fixture
def order_of_a(add_order):
    return add_order(OrderStatus.pending)


def test_b_gets_404_on_orders_of_a(client, shop, user_b, order_of_a, db_session):
    base = orders_url(shop.business["id"])

    assert client.get(base, headers=user_b.headers).status_code == 404
    assert client.get(f"{base}/{order_of_a.id}", headers=user_b.headers).status_code == 404
    assert client.patch(f"{base}/{order_of_a.id}/status", json={"status": "confirmed"}, headers=user_b.headers).status_code == 404
    db_session.expire_all()
    assert order_of_a.status == OrderStatus.pending


def test_order_of_a_through_the_business_of_b_returns_404(client, order_of_a, user_b, create_business):
    # B owns the business in the URL, but the order belongs to another business
    business_of_b = create_business(user_b)

    response = client.get(f"{orders_url(business_of_b['id'])}/{order_of_a.id}", headers=user_b.headers)

    assert response.status_code == 404


def test_order_through_another_branch_of_the_same_owner_returns_404(client, shop, order_of_a, create_business):
    other_branch = create_business(shop.owner, name="Otra Sucursal")
    url = f"{orders_url(other_branch['id'])}/{order_of_a.id}"

    assert client.get(url, headers=shop.owner.headers).status_code == 404
    assert client.patch(f"{url}/status", json={"status": "confirmed"}, headers=shop.owner.headers).status_code == 404


@pytest.mark.parametrize("method, suffix, body", [("get", "", None), ("get", "/1", None), ("patch", "/1/status", {"status": "confirmed"})])
def test_owner_endpoints_without_token_return_401(client, shop, method, suffix, body):
    response = client.request(method, orders_url(shop.business["id"]) + suffix, json=body)

    assert response.status_code == 401
