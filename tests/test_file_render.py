import os
import json


def login_file_render(self):
    response = self.client.get("/")
    assert response.status_code == 200

    try:
        with open("templates/login.html", "r") as file:
            index_content = file.read().rstrip('\n')

        assert response.data.decode().rstrip('\n') == index_content

    except Exception as e:
        assert False, 'login file content not matching with the response'


def new_order_file_render(self):
    response = self.client.get("/new-order")
    assert response.status_code == 200

    menu = list(response.data.decode())
    assert menu is not None
    assert isinstance(menu, list)
    assert len(menu) > 0


def my_order_render_file(self):
    # Set up the session with user_id
    with self.client.session_transaction() as sess:
        sess["user_id"] = "64a6386b376bbe6dc7785e46"

    # Send GET request to the /my-orders route
    response = self.client.get("/my-orders")

    # Verify the response
    assert response.status_code == 200

    # Check if the expected template name is present in the response HTML
    assert b'title>My Orders</title>' in response.data

    # Check if the orders list is present in the response data
    orders = list(response.data.decode())
    assert orders is not None
    assert isinstance(orders, list)
    assert len(orders) > 0


def single_order_render_file(self):
    # Send GET request to the /order/<order_id> route
    response = self.client.get("/single-order/64a6386b376bbe6dc7785e46")

    # Verify the response
    assert response.status_code == 200

    # Check if the expected template name is present in the response HTML
    assert b'title>Order Details</title>' in response.data

    # Check if the order details are present in the response data
    order = list(response.data.decode())
    assert order is not None
    assert isinstance(order, list)
    assert len(order) > 0
