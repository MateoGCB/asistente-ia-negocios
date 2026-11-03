"""User B must not see, change or archive user A's businesses.
A foreign business answers 404 (not 403): B cannot even learn that it exists."""
import pytest


@pytest.fixture
def business_of_a(user_a, create_business):
    return create_business(user_a, name="Negocio de A")


def test_list_of_b_does_not_include_businesses_of_a(client, user_b, business_of_a):
    assert client.get("/businesses/", headers=user_b.headers).json() == []


@pytest.mark.parametrize(
    "method, body",
    [("get", None), ("patch", {"name": "Robado"}), ("delete", None)],
)
def test_b_gets_404_on_a_business_of_a(client, user_a, user_b, business_of_a, method, body):
    url = f"/businesses/{business_of_a['id']}"

    response = client.request(method, url, json=body, headers=user_b.headers)

    assert response.status_code == 404
    # Same answer as a business that does not exist at all: nothing is revealed
    unknown = client.request(method, "/businesses/9999", json=body, headers=user_b.headers)
    assert response.json() == unknown.json()
    # And A's business is untouched (not renamed, not archived)
    assert client.get(url, headers=user_a.headers).json() == business_of_a
