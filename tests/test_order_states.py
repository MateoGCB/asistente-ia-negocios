"""PATCH /businesses/{id}/orders/{order_id}/status: the order state machine."""
import itertools
import threading
from datetime import timedelta

import pytest

from models.order_models import CancelReason, Order_db, OrderStatus
from utils.datetime_utils import utc_now

# Written by hand ON PURPOSE (not imported from ALLOWED_TRANSITIONS): if the code's table had a
# mistake, a test built from that same table would repeat the mistake and still pass.
VALID_TRANSITIONS = {
    ("pending", "confirmed"), ("pending", "cancelled"),
    ("confirmed", "preparing"), ("confirmed", "cancelled"),
    ("preparing", "ready"), ("preparing", "cancelled"),
    ("ready", "delivered"), ("ready", "cancelled"),
}
ALL_STATUSES = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
INVALID_TRANSITIONS = sorted(set(itertools.product(ALL_STATUSES, repeat=2)) - VALID_TRANSITIONS)


def test_there_are_exactly_28_invalid_transitions():
    # 6 x 6 = 36 pairs (including "same status"), minus the 8 valid ones
    assert len(INVALID_TRANSITIONS) == 28


@pytest.fixture
def new_order(shop, insert_order):
    def _new_order(status: str = "pending") -> Order_db:
        fields = {"status": OrderStatus(status)}
        if status == "ready":
            fields["ready_at"] = utc_now()  # recent, so it does not expire
        if status == "cancelled":
            fields["cancel_reason"] = CancelReason.owner
        return insert_order(shop.business["id"], shop.items[0]["id"], **fields)

    return _new_order


def change_status(client, shop, order_id: int, status: str):
    url = f"/businesses/{shop.business['id']}/orders/{order_id}/status"
    return client.patch(url, json={"status": status}, headers=shop.owner.headers)


def status_in_db(db_session, order_id: int) -> Order_db:
    db_session.expire_all()
    return db_session.get(Order_db, order_id)


# ---------------------------------------------------------------- valid paths

def test_happy_path_from_pending_to_delivered(client, shop, place_order, db_session):
    # Starts with a REAL order created through the public endpoint
    place_order(shop.business["slug"], [(shop.items[0]["id"], 1)])
    order_id = db_session.query(Order_db).one().id

    for status in ["confirmed", "preparing", "ready", "delivered"]:
        response = change_status(client, shop, order_id, status)
        assert response.status_code == 200, f"-> {status}: {response.text}"
        assert response.json()["status"] == status

    assert status_in_db(db_session, order_id).status == OrderStatus.delivered


def test_ready_at_is_saved_when_the_order_becomes_ready(client, shop, new_order, db_session):
    order = new_order("preparing")
    assert order.ready_at is None
    before = utc_now()

    response = change_status(client, shop, order.id, "ready")

    stored = status_in_db(db_session, order.id).ready_at
    assert before - timedelta(seconds=1) <= stored <= utc_now() + timedelta(seconds=1)
    assert response.json()["ready_at"] is not None


@pytest.mark.parametrize("from_status", ["pending", "confirmed", "preparing", "ready"])
def test_owner_can_cancel_from_any_active_status(client, shop, new_order, db_session, from_status):
    order = new_order(from_status)

    response = change_status(client, shop, order.id, "cancelled")

    assert response.status_code == 200
    assert response.json()["cancel_reason"] == "owner"
    stored = status_in_db(db_session, order.id)
    assert (stored.status, stored.cancel_reason) == (OrderStatus.cancelled, CancelReason.owner)


# ---------------------------------------------------------------- invalid transitions

@pytest.mark.parametrize("from_status, to_status", INVALID_TRANSITIONS)
def test_invalid_transition_returns_409_and_keeps_the_status(client, shop, new_order, db_session, from_status, to_status):
    # Includes skipping steps, going back, leaving a final status and "same status"
    order = new_order(from_status)

    response = change_status(client, shop, order.id, to_status)

    assert response.status_code == 409
    assert status_in_db(db_session, order.id).status == OrderStatus(from_status)


@pytest.mark.parametrize("body", [{"status": "perdido"}, {"status": None}, {}, {"status": "PENDING"}])
def test_invalid_status_in_the_body_returns_422(client, shop, new_order, db_session, body):
    order = new_order("pending")

    response = client.patch(f"/businesses/{shop.business['id']}/orders/{order.id}/status", json=body, headers=shop.owner.headers)

    assert response.status_code == 422
    assert status_in_db(db_session, order.id).status == OrderStatus.pending


# ---------------------------------------------------------------- race between two changes

def _reachable(start: str, steps: list[str]) -> bool:
    status = start
    for step in steps:
        if (status, step) not in VALID_TRANSITIONS:
            return False
        status = step
    return True


@pytest.mark.slow
@pytest.mark.parametrize(
    "start, first, second",
    [
        ("pending", "confirmed", "cancelled"),    # cancelled is valid after confirmed: 2 x 200 is possible
        ("pending", "confirmed", "confirmed"),    # same change twice: only one may win
        ("preparing", "ready", "cancelled"),
        ("ready", "delivered", "cancelled"),      # both final: only one may win
    ],
)
def test_two_simultaneous_changes_end_in_a_valid_state(client, shop, new_order, db_session, start, first, second):
    for round_number in range(5):
        order = new_order(start)
        barrier = threading.Barrier(2)
        results = {}

        def send(target, key):
            barrier.wait()  # both threads fire at the same moment
            results[key] = change_status(client, shop, order.id, target).status_code

        threads = [threading.Thread(target=send, args=(first, "first")), threading.Thread(target=send, args=(second, "second"))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        final = status_in_db(db_session, order.id).status.value
        winners = [target for target, key in ((first, "first"), (second, "second")) if results[key] == 200]
        assert set(results.values()) <= {200, 409}, f"round {round_number}: {results}"
        assert winners, f"round {round_number}: nobody won {results}"

        if len(winners) == 1:
            # One applied, the other was rejected: the final status is the winner's
            assert final == winners[0], f"round {round_number}: {results}, final {final}"
        else:
            # Both 200 is only correct if they ran one after the other in a valid order
            valid_orders = [seq for seq in ([first, second], [second, first]) if _reachable(start, seq) and seq[-1] == final]
            assert valid_orders, f"round {round_number}: both 200 but {start}->{first}/{second} ended in {final}"
