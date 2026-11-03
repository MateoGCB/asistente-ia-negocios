"""Concurrency with REAL threads against a real SQLite file.

Each thread waits on a Barrier so all requests are fired at the same moment. The protections
under test are atomic statements: UPDATE ... RETURNING for the order counter, and conditional
UPDATEs (WHERE ... AND <state we read>) for archiving. Several rounds, because a race that is
lost only sometimes is still a bug.
"""
import threading

import pytest

from models.business_models import Business_db
from models.order_models import Order_db
from services import order_services
from tests.conftest import TEST_CUSTOMER
from utils.datetime_utils import utc_now

pytestmark = pytest.mark.slow  # every test in this file: skip them with -m "not slow"

ROUNDS = 10
SIMULTANEOUS_ORDERS = 12


def run_simultaneously(calls: list) -> list:
    """Runs every callable in its own thread, all released together. Returns results in order."""
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(index, call):
        barrier.wait()
        results[index] = call()

    threads = [threading.Thread(target=worker, args=(i, call)) for i, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_simultaneous_orders_get_unique_numbers_without_gaps(client, shop, create_business, assign_menu, place_order, db_session):
    item = [(shop.items[0]["id"], 1)]
    for round_number in range(ROUNDS):
        # A fresh branch per round, so every round starts again at number 1
        branch = create_business(shop.owner, name=f"Sucursal Carrera {round_number}")
        assign_menu(shop.owner, branch["id"], shop.menu["id"])

        responses = run_simultaneously([lambda: place_order(branch["slug"], item)] * SIMULTANEOUS_ORDERS)

        statuses = [r.status_code for r in responses]
        assert statuses == [201] * SIMULTANEOUS_ORDERS, f"round {round_number}: {statuses}"
        numbers = sorted(r.json()["number"] for r in responses)
        assert numbers == list(range(1, SIMULTANEOUS_ORDERS + 1)), f"round {round_number}: {numbers}"
        db_session.expire_all()
        assert db_session.get(Business_db, branch["id"]).next_order_number == SIMULTANEOUS_ORDERS + 1
        assert db_session.query(Order_db).filter(Order_db.business_id == branch["id"]).count() == SIMULTANEOUS_ORDERS


def test_two_simultaneous_archives_give_one_200_and_one_404(client, user_a, create_business):
    # The conditional UPDATE (WHERE ... AND deleted_at IS NULL) lets only one of them win
    for round_number in range(ROUNDS):
        business = create_business(user_a, name=f"Carrera {round_number}")
        archive = lambda: client.delete(f"/businesses/{business['id']}", headers=user_a.headers)

        statuses = sorted(r.status_code for r in run_simultaneously([archive, archive]))

        assert statuses == [200, 404], f"round {round_number}: {statuses}"


def test_business_archived_between_lookup_and_numbering_gets_no_order(client, shop, session_factory, db_session, monkeypatch):
    # Deterministic version of the archive/order race: we archive the business (from ANOTHER
    # session, like a simultaneous request would) right AFTER create_order found it by slug and
    # BEFORE it takes a number. The "deleted_at IS NULL" in the counter UPDATE must stop it.
    body = {**TEST_CUSTOMER, "items": [{"menu_item_id": shop.items[0]["id"], "quantity": 1}]}
    unknown = client.post("/public/este-slug-no-existe/orders", json=body)  # reference 404, before patching
    real_lookup = order_services.search_business_by_slug

    def lookup_then_archive(slug, db):
        business = real_lookup(slug, db)
        other_request = session_factory()
        other_request.query(Business_db).filter(Business_db.id == business.id).update({Business_db.deleted_at: utc_now()})
        other_request.commit()
        other_request.close()
        return business  # create_order still holds the (now stale) active business

    monkeypatch.setattr(order_services, "search_business_by_slug", lookup_then_archive)

    response = client.post(f"/public/{shop.business['slug']}/orders", json=body)

    assert unknown.status_code == 404
    assert response.status_code == 404
    assert response.json() == unknown.json()  # indistinguishable from an unknown slug
    db_session.expire_all()
    assert db_session.query(Order_db).count() == 0
    assert db_session.get(Business_db, shop.business["id"]).next_order_number == 1


def test_simultaneous_archive_and_order_never_leave_an_order_in_an_archived_business(client, shop, create_business, assign_menu, db_session):
    # The real race with threads: either the order arrives first (201, saved before the archive),
    # or the archive does (404, nothing saved). Never a half state.
    item_id = shop.items[0]["id"]
    for round_number in range(ROUNDS):
        branch = create_business(shop.owner, name=f"Sucursal Cierre {round_number}")
        assign_menu(shop.owner, branch["id"], shop.menu["id"])
        order = lambda: client.post(f"/public/{branch['slug']}/orders", json={**TEST_CUSTOMER, "items": [{"menu_item_id": item_id, "quantity": 1}]})
        archive = lambda: client.delete(f"/businesses/{branch['id']}", headers=shop.owner.headers)

        order_response, archive_response = run_simultaneously([order, archive])

        assert archive_response.status_code == 200, f"round {round_number}"
        assert order_response.status_code in (201, 404), f"round {round_number}: {order_response.status_code}"
        db_session.expire_all()
        saved = db_session.query(Order_db).filter(Order_db.business_id == branch["id"]).count()
        counter = db_session.get(Business_db, branch["id"]).next_order_number
        if order_response.status_code == 201:
            assert (saved, counter) == (1, 2), f"round {round_number}"
        else:
            assert (saved, counter) == (0, 1), f"round {round_number}"
