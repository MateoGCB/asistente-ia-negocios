from decimal import Decimal

import pytest

from models.menu_models import Menu_db, MenuCategory, MenuItem_db

ITEM_KEYS = {"id", "name", "description", "price", "category", "available"}


@pytest.fixture
def menu_of_a(user_a, create_menu, create_item):
    menu = create_menu(user_a, name="Menú de A")
    item = create_item(user_a, menu["id"], name="Milanesa", price="9000.00")
    return {"menu": menu, "item": item}


# ---------------------------------------------------------------- menus

def test_create_menu_returns_201_and_owner_comes_from_the_token(client, user_a, db_session):
    response = client.post("/menus/", json={"name": "Carta de Verano", "owner_id": 999}, headers=user_a.headers)

    assert response.status_code == 201
    assert set(response.json()) == {"id", "name"}  # owner_id is never returned
    assert db_session.get(Menu_db, response.json()["id"]).owner_id == user_a.id


# ---------------------------------------------------------------- items: create and validation

@pytest.mark.parametrize("category", [c.value for c in MenuCategory])
def test_create_item_with_each_category(client, user_a, create_menu, category):
    menu = create_menu(user_a)
    body = {"name": "Plato", "description": "Ficticio", "price": "1500.00", "category": category}

    response = client.post(f"/menus/{menu['id']}/items", json=body, headers=user_a.headers)

    assert response.status_code == 201
    data = response.json()
    assert set(data) == ITEM_KEYS
    assert data["category"] == category
    assert data["available"] is True  # new items are available by default


def test_unknown_category_returns_422(client, user_a, create_menu):
    menu = create_menu(user_a)
    body = {"name": "Plato", "description": "Ficticio", "price": "1500.00", "category": "pizzas"}

    assert client.post(f"/menus/{menu['id']}/items", json=body, headers=user_a.headers).status_code == 422


@pytest.mark.parametrize("price", ["0", "0.00", "-1", "-1500.50"])
def test_price_zero_or_negative_returns_422_and_saves_nothing(client, user_a, create_menu, db_session, price):
    menu = create_menu(user_a)
    body = {"name": "Plato", "description": "Ficticio", "price": price, "category": "postre"}

    response = client.post(f"/menus/{menu['id']}/items", json=body, headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(MenuItem_db).count() == 0


@pytest.mark.parametrize("price", ["0", "-5"])
def test_patch_price_zero_or_negative_returns_422(client, user_a, menu_of_a, price):
    url = f"/menus/{menu_of_a['menu']['id']}/items/{menu_of_a['item']['id']}"

    assert client.patch(url, json={"price": price}, headers=user_a.headers).status_code == 422


@pytest.mark.parametrize("sent, returned", [("3500.5", "3500.50"), ("8500", "8500.00"), (1200, "1200.00")])
def test_price_is_returned_as_an_exact_decimal_string(client, user_a, create_menu, sent, returned):
    # Money never travels as float: the JSON carries a string with exactly 2 decimals
    menu = create_menu(user_a)
    body = {"name": "Plato", "description": "Ficticio", "price": sent, "category": "entrada"}

    data = client.post(f"/menus/{menu['id']}/items", json=body, headers=user_a.headers).json()

    assert data["price"] == returned
    assert Decimal(data["price"]) == Decimal(str(sent))


def test_list_items_shows_unavailable_ones_to_the_owner(client, user_a, menu_of_a):
    menu_id, item_id = menu_of_a["menu"]["id"], menu_of_a["item"]["id"]
    client.patch(f"/menus/{menu_id}/items/{item_id}", json={"available": False}, headers=user_a.headers)

    items = client.get(f"/menus/{menu_id}/items", headers=user_a.headers).json()

    assert [(i["id"], i["available"]) for i in items] == [(item_id, False)]


# ---------------------------------------------------------------- isolation between owners

@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", "/items", {"name": "Intruso", "description": "x", "price": "1.00", "category": "postre"}),
        ("get", "/items", None),
        ("patch", "/items/{item_id}", {"name": "Hackeado"}),
        ("delete", "/items/{item_id}", None),
    ],
)
def test_b_gets_404_on_the_menu_of_a(client, user_a, user_b, menu_of_a, method, path, body):
    menu_id, item_id = menu_of_a["menu"]["id"], menu_of_a["item"]["id"]
    url = f"/menus/{menu_id}" + path.format(item_id=item_id)

    response = client.request(method, url, json=body, headers=user_b.headers)

    assert response.status_code == 404
    # A's menu is untouched: same single item, same name
    assert client.get(f"/menus/{menu_id}/items", headers=user_a.headers).json() == [menu_of_a["item"]]


def test_item_is_only_reachable_through_its_own_menu(client, user_a, create_menu, menu_of_a):
    # Same owner, but the item belongs to another menu: the URL pair must match
    other_menu = create_menu(user_a, name="Otro menú")
    url = f"/menus/{other_menu['id']}/items/{menu_of_a['item']['id']}"

    assert client.patch(url, json={"name": "x"}, headers=user_a.headers).status_code == 404
    assert client.delete(url, headers=user_a.headers).status_code == 404


def test_b_cannot_assign_the_menu_of_a_to_its_business(client, user_b, menu_of_a, create_business):
    business_of_b = create_business(user_b)

    response = client.patch(f"/businesses/{business_of_b['id']}", json={"menu_id": menu_of_a["menu"]["id"]}, headers=user_b.headers)

    assert response.status_code == 404
    assert client.get(f"/businesses/{business_of_b['id']}", headers=user_b.headers).json()["menu_id"] is None


def test_owner_can_assign_one_menu_to_two_branches(client, user_a, menu_of_a, create_business, assign_menu):
    menu_id = menu_of_a["menu"]["id"]
    first, second = create_business(user_a, name="Sucursal 1"), create_business(user_a, name="Sucursal 2")

    assert assign_menu(user_a, first["id"], menu_id)["menu_id"] == menu_id
    assert assign_menu(user_a, second["id"], menu_id)["menu_id"] == menu_id


# ---------------------------------------------------------------- delete items

def test_delete_item_without_orders(client, user_a, menu_of_a):
    menu_id, item_id = menu_of_a["menu"]["id"], menu_of_a["item"]["id"]
    url = f"/menus/{menu_id}/items/{item_id}"

    response = client.delete(url, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == {"message": "Item deleted successfully"}
    assert client.delete(url, headers=user_a.headers).status_code == 404
    assert client.patch(url, json={"name": "x"}, headers=user_a.headers).status_code == 404
    assert client.get(f"/menus/{menu_id}/items", headers=user_a.headers).json() == []


def test_delete_item_used_in_an_order_returns_409_and_keeps_it(client, shop, insert_order, db_session):
    item = shop.items[0]
    insert_order(shop.business["id"], item["id"], quantity=2)

    response = client.delete(f"/menus/{shop.menu['id']}/items/{item['id']}", headers=shop.owner.headers)

    assert response.status_code == 409
    # Clear message that also tells the owner what to do instead
    assert "available=false" in response.json()["detail"]
    assert db_session.get(MenuItem_db, item["id"]) is not None


def test_b_gets_404_not_409_deleting_an_item_of_a_that_has_orders(client, shop, user_b, insert_order):
    # 409 would reveal to B that A's item exists AND has orders: ownership is checked first
    item = shop.items[0]
    insert_order(shop.business["id"], item["id"])

    response = client.delete(f"/menus/{shop.menu['id']}/items/{item['id']}", headers=user_b.headers)

    assert response.status_code == 404


# ---------------------------------------------------------------- available on / off

def test_owner_can_turn_available_off_and_on(client, user_a, menu_of_a):
    url = f"/menus/{menu_of_a['menu']['id']}/items/{menu_of_a['item']['id']}"

    off = client.patch(url, json={"available": False}, headers=user_a.headers)
    on = client.patch(url, json={"available": True}, headers=user_a.headers)

    assert off.status_code == 200 and off.json()["available"] is False
    assert on.status_code == 200 and on.json()["available"] is True


def test_b_cannot_change_available_of_an_item_of_a(client, user_a, user_b, menu_of_a, db_session):
    url = f"/menus/{menu_of_a['menu']['id']}/items/{menu_of_a['item']['id']}"

    assert client.patch(url, json={"available": False}, headers=user_b.headers).status_code == 404
    assert db_session.get(MenuItem_db, menu_of_a["item"]["id"]).available is True


# ---------------------------------------------------------------- text validation (menus and items)

def test_create_menu_strips_spaces_and_accepts_edges(client, user_a):
    for sent, saved in [("M", "M"), ("x" * 100, "x" * 100), ("  Carta de Invierno  ", "Carta de Invierno")]:
        response = client.post("/menus/", json={"name": sent}, headers=user_a.headers)
        assert response.status_code == 201, sent
        assert response.json()["name"] == saved


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, None])
def test_create_menu_with_invalid_name_returns_422_and_saves_nothing(client, user_a, db_session, name):
    # None: the name is required, so null is an error (not "use a default")
    response = client.post("/menus/", json={"name": name}, headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(Menu_db).count() == 0


INVALID_ITEM_TEXTS = [
    ("name", ""),
    ("name", "   "),
    ("name", "x" * 101),
    ("description", ""),
    ("description", "   "),
    ("description", "x" * 501),
]

VALID_ITEM_EDGES = [
    ("name", "X", "X"),
    ("name", "x" * 100, "x" * 100),
    ("name", "  Flan casero  ", "Flan casero"),
    ("description", "d", "d"),
    ("description", "x" * 500, "x" * 500),
    ("description", "  Con dulce de leche  ", "Con dulce de leche"),
]


def _item_body(**changes) -> dict:
    return {"name": "Plato", "description": "Ficticio", "price": "1000.00", "category": "postre", **changes}


@pytest.mark.parametrize("field, value", INVALID_ITEM_TEXTS + [("name", None), ("description", None)])
def test_create_item_with_invalid_text_returns_422_and_saves_nothing(client, user_a, create_menu, db_session, field, value):
    menu = create_menu(user_a)

    response = client.post(f"/menus/{menu['id']}/items", json=_item_body(**{field: value}), headers=user_a.headers)

    assert response.status_code == 422
    assert db_session.query(MenuItem_db).count() == 0


@pytest.mark.parametrize("field, value", INVALID_ITEM_TEXTS)
def test_patch_item_with_invalid_text_returns_422_and_keeps_it(client, user_a, menu_of_a, field, value):
    menu_id, item = menu_of_a["menu"]["id"], menu_of_a["item"]

    response = client.patch(f"/menus/{menu_id}/items/{item['id']}", json={field: value}, headers=user_a.headers)

    assert response.status_code == 422
    assert client.get(f"/menus/{menu_id}/items", headers=user_a.headers).json() == [item]


@pytest.mark.parametrize("field, value, saved", VALID_ITEM_EDGES)
def test_create_item_accepts_edges_and_strips_spaces(client, user_a, create_menu, field, value, saved):
    menu = create_menu(user_a)

    response = client.post(f"/menus/{menu['id']}/items", json=_item_body(**{field: value}), headers=user_a.headers)

    assert response.status_code == 201
    assert response.json()[field] == saved


@pytest.mark.parametrize("field, value, saved", VALID_ITEM_EDGES)
def test_patch_item_accepts_edges_and_strips_spaces(client, user_a, menu_of_a, field, value, saved):
    url = f"/menus/{menu_of_a['menu']['id']}/items/{menu_of_a['item']['id']}"

    response = client.patch(url, json={field: value}, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json()[field] == saved


def test_patch_item_with_nulls_is_ignored(client, user_a, menu_of_a):
    url = f"/menus/{menu_of_a['menu']['id']}/items/{menu_of_a['item']['id']}"
    body = {"name": None, "description": None, "price": None, "category": None, "available": None}

    response = client.patch(url, json=body, headers=user_a.headers)

    assert response.status_code == 200
    assert response.json() == menu_of_a["item"]
