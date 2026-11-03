"""A ready order not picked up within the branch's CURRENT pickup_timeout_hours becomes
cancelled / not_picked_up the next time the owner queries the orders. No sleeps: ready_at is moved
directly in the test DB."""
from datetime import timedelta, timezone

import pytest
from sqlalchemy import text

from models.order_models import CancelReason, Order_db, OrderStatus
from utils.datetime_utils import utc_now

UTC_MINUS_3 = timezone(timedelta(hours=-3))


@pytest.fixture
def ready_order(insert_order):
    """A ready order of a business, picked up... never: ready_at = now - `ago`."""
    def _ready_order(business_id: int, item_id: int, ago: timedelta) -> Order_db:
        return insert_order(business_id, item_id, status=OrderStatus.ready, ready_at=utc_now() - ago)

    return _ready_order


def list_orders(client, user, business_id: int, **params):
    response = client.get(f"/businesses/{business_id}/orders", params=params, headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()


def stored(db_session, order_id: int) -> Order_db:
    db_session.expire_all()
    return db_session.get(Order_db, order_id)


@pytest.fixture
def shop_ready(shop, ready_order):
    # Shortcut: a ready order of the shop (24 h timeout by default)
    return lambda ago: ready_order(shop.business["id"], shop.items[0]["id"], ago)


# ---------------------------------------------------------------- the basic rule

def test_ready_25_hours_ago_with_24_hour_timeout_is_cancelled(client, shop, shop_ready, db_session):
    order = shop_ready(timedelta(hours=25))
    ready_at_before = order.ready_at

    active = list_orders(client, shop.owner, shop.business["id"], view="active")
    history = list_orders(client, shop.owner, shop.business["id"], view="history")

    assert active["items"] == []
    assert [o["id"] for o in history["items"]] == [order.id]
    assert history["items"][0]["cancel_reason"] == "not_picked_up"
    after = stored(db_session, order.id)
    assert (after.status, after.cancel_reason) == (OrderStatus.cancelled, CancelReason.not_picked_up)
    assert after.ready_at == ready_at_before  # ready_at is kept (when it was ready)


@pytest.mark.parametrize(
    "ago, expected",
    [
        (timedelta(hours=23), OrderStatus.ready),
        (timedelta(hours=23, minutes=59), OrderStatus.ready),
        (timedelta(hours=24, minutes=1), OrderStatus.cancelled),
        (timedelta(hours=25), OrderStatus.cancelled),
    ],
    ids=["23h", "23h59m", "24h01m", "25h"],
)
def test_edges_of_the_24_hour_timeout(client, shop, shop_ready, db_session, ago, expected):
    order = shop_ready(ago)

    list_orders(client, shop.owner, shop.business["id"])

    assert stored(db_session, order.id).status == expected


@pytest.mark.parametrize("trigger", ["list", "detail", "status_change"])
def test_every_owner_query_triggers_the_expiration(client, shop, shop_ready, db_session, trigger):
    order = shop_ready(timedelta(hours=25))
    base = f"/businesses/{shop.business['id']}/orders"

    if trigger == "list":
        client.get(base, headers=shop.owner.headers)
    elif trigger == "detail":
        assert client.get(f"{base}/{order.id}", headers=shop.owner.headers).json()["status"] == "cancelled"
    else:
        client.patch(f"{base}/{order.id}/status", json={"status": "delivered"}, headers=shop.owner.headers)

    assert stored(db_session, order.id).status == OrderStatus.cancelled


# ---------------------------------------------------------------- per-branch timeout

def test_each_branch_uses_its_own_timeout(client, shop, create_business, assign_menu, ready_order, db_session):
    fast = create_business(shop.owner, name="Sucursal Rapida")
    assign_menu(shop.owner, fast["id"], shop.menu["id"])
    client.patch(f"/businesses/{fast['id']}", json={"pickup_timeout_hours": 2}, headers=shop.owner.headers)
    item_id = shop.items[0]["id"]
    in_fast = ready_order(fast["id"], item_id, timedelta(hours=3))
    in_shop = ready_order(shop.business["id"], item_id, timedelta(hours=3))  # 24 h timeout

    list_orders(client, shop.owner, fast["id"])
    list_orders(client, shop.owner, shop.business["id"])

    assert stored(db_session, in_fast.id).status == OrderStatus.cancelled
    assert stored(db_session, in_shop.id).status == OrderStatus.ready


def test_lowering_the_timeout_applies_on_the_next_query(client, shop, shop_ready, db_session):
    # The CURRENT timeout is what counts, not the one in force when the order became ready
    order = shop_ready(timedelta(hours=5))
    list_orders(client, shop.owner, shop.business["id"])
    assert stored(db_session, order.id).status == OrderStatus.ready

    client.patch(f"/businesses/{shop.business['id']}", json={"pickup_timeout_hours": 2}, headers=shop.owner.headers)
    list_orders(client, shop.owner, shop.business["id"])

    assert stored(db_session, order.id).status == OrderStatus.cancelled


# ---------------------------------------------------------------- what never expires

@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.confirmed, OrderStatus.preparing, OrderStatus.delivered])
def test_an_order_that_is_not_ready_never_expires(client, shop, insert_order, db_session, status):
    # Even with very old dates: only READY orders are waiting to be picked up
    long_ago = utc_now() - timedelta(days=10)
    order = insert_order(shop.business["id"], shop.items[0]["id"], status=status, created_at=long_ago, ready_at=long_ago)

    list_orders(client, shop.owner, shop.business["id"])

    after = stored(db_session, order.id)
    assert (after.status, after.cancel_reason) == (status, None)


def test_changing_the_status_of_an_order_that_just_expired_returns_409(client, shop, shop_ready, db_session):
    # The owner sees it as "ready" on screen, but it expired: delivering it now is rejected
    order = shop_ready(timedelta(hours=25))

    response = client.patch(
        f"/businesses/{shop.business['id']}/orders/{order.id}/status", json={"status": "delivered"}, headers=shop.owner.headers
    )

    assert response.status_code == 409
    assert "cancelled" in response.json()["detail"]
    assert stored(db_session, order.id).cancel_reason == CancelReason.not_picked_up


def test_expiration_does_not_touch_other_branches_or_owners(client, shop, user_b, create_business, create_menu, create_item, assign_menu, ready_order, db_session):
    other_branch = create_business(shop.owner, name="Otra Sucursal")
    assign_menu(shop.owner, other_branch["id"], shop.menu["id"])
    business_of_b = create_business(user_b, name="Negocio de B")
    item_of_b = create_item(user_b, create_menu(user_b)["id"])
    overdue = timedelta(hours=30)
    in_shop = ready_order(shop.business["id"], shop.items[0]["id"], overdue)
    in_other_branch = ready_order(other_branch["id"], shop.items[0]["id"], overdue)
    in_b = ready_order(business_of_b["id"], item_of_b["id"], overdue)

    list_orders(client, shop.owner, shop.business["id"])  # only this branch is evaluated

    assert stored(db_session, in_shop.id).status == OrderStatus.cancelled
    assert stored(db_session, in_other_branch.id).status == OrderStatus.ready
    assert stored(db_session, in_b.id).status == OrderStatus.ready


def test_archived_business_is_not_processed(client, shop, shop_ready, db_session):
    order = shop_ready(timedelta(hours=30))
    client.delete(f"/businesses/{shop.business['id']}", headers=shop.owner.headers)

    response = client.get(f"/businesses/{shop.business['id']}/orders", headers=shop.owner.headers)

    assert response.status_code == 404
    assert stored(db_session, order.id).status == OrderStatus.ready  # kept exactly as it was


# ---------------------------------------------------------------- time zones

def _write_raw_ready_at(db_session, order_id: int, naive_utc_text: str):
    # Bypasses UTCDateTime: writes the text exactly as an old row or a manual script would
    db_session.execute(text("UPDATE orders SET ready_at = :value WHERE id = :id"), {"value": naive_utc_text, "id": order_id})
    db_session.commit()


@pytest.mark.parametrize("hours_ago, expected", [(25, OrderStatus.cancelled), (23, OrderStatus.ready)])
def test_naive_ready_at_in_the_db_is_read_as_utc(client, shop, shop_ready, db_session, hours_ago, expected):
    order = shop_ready(timedelta(hours=1))
    naive = (utc_now() - timedelta(hours=hours_ago)).replace(tzinfo=None)
    _write_raw_ready_at(db_session, order.id, naive.strftime("%Y-%m-%d %H:%M:%S.%f"))

    list_orders(client, shop.owner, shop.business["id"])

    assert stored(db_session, order.id).status == expected


@pytest.mark.parametrize("hours_ago, expected", [(25, OrderStatus.cancelled), (23, OrderStatus.ready)])
def test_aware_ready_at_in_utc_minus_3_is_converted_correctly(client, shop, insert_order, db_session, hours_ago, expected):
    # 23 h ago written in Argentina time. If the zone were dropped instead of converted, the order
    # would look 26 h old and be cancelled by mistake (the bug UTCDateTime exists to prevent).
    ready_at = (utc_now() - timedelta(hours=hours_ago)).astimezone(UTC_MINUS_3)
    order = insert_order(shop.business["id"], shop.items[0]["id"], status=OrderStatus.ready, ready_at=ready_at)

    list_orders(client, shop.owner, shop.business["id"])

    assert stored(db_session, order.id).status == expected


def test_ready_order_without_ready_at_never_expires_and_does_not_fail(client, shop, insert_order, db_session):
    # The API can never produce this state (moving to ready always sets ready_at in the same UPDATE),
    # but a manual edit or a data migration could. Fixed behavior: it is skipped, never expired,
    # and listing or viewing it does not crash.
    order = insert_order(shop.business["id"], shop.items[0]["id"], status=OrderStatus.ready, created_at=utc_now() - timedelta(days=10))
    assert order.ready_at is None

    listing = client.get(f"/businesses/{shop.business['id']}/orders", headers=shop.owner.headers)
    detail = client.get(f"/businesses/{shop.business['id']}/orders/{order.id}", headers=shop.owner.headers)

    assert listing.status_code == 200 and detail.status_code == 200
    assert detail.json()["ready_at"] is None
    assert stored(db_session, order.id).status == OrderStatus.ready
