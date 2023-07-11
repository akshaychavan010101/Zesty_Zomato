import pytest
from app import create_app
from tests.test_file_render import login_file_render, new_order_file_render, my_order_render_file, single_order_render_file
import json
from flask_testing import TestCase


class MyTest(TestCase):
    def create_app(self):
        # Create and configure your Flask app instance
        app = create_app()
        app.config["TESTING"] = True
        return app


# ----------------------user routes test cases----------------------


    def test_get_home(self):
        login_file_render(self)

    def test_register_route(self):
        # Prepare form data
        form_data = {
            "name": "John Doe",
            "email": "johndoe@example.com",
            "password": "password123"
        }

        # Send POST request
        response = self.client.post("/register", data=form_data)

        # Verify the response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"status": "success",
                        "message": "User registered successfully!"} or data == {"status": 'error', 'message': "User already exists!"}

    def test_new_order_post_route(self):
        # Prepare form data
        form_data = {
            "customer_name": "John Doe",
            "user_id": "64a6386b376bbe6dc7785e46",
            "dish_ids": ["64a6386b376bbe6dc7785e46", "64a6386b376bbe6dc7785e46"],
            "dish_names": ["Pizza", "Burger"],
            "total_price": 1000,
            "dish_imgs": ["pizza.jpg", "burger.jpg"],
            "status": "received"
        }

        # Send POST request
        response = self.client.post("/new-order", data=form_data)

        # Verify the response
        assert response.status_code == 200
        data = json.loads(response.data)

    def test_my_orders_get_route(self):
        my_order_render_file(self)

    def test_new_order_get_route(self):
        new_order_file_render(self)

    def test_single_order_get_route(self):
        single_order_render_file(self)

    def test_add_feedback_route(self):

        # Prepare JSON data for the feedback
        feedback_data = {
            "order_id": "5fcd1a9f40ee4319f8f6dbb0",
            "user_feedback": "Great service!",
            "rating": 5,
            "dishIds": ["5fcd1a9f40ee4319f8f6dbb1"]
        }

        # Send POST request to the /add-feedback route
        response = self.client.post("/add-feedback", json=feedback_data)

        # Verify the response
        assert response.status_code == 200

        # if you are dumping the response data to JSON, then use json.loads()
        # if you are using jsonify() in the route, then use response.json

        # Check if the response data contains the expected status and message
        data = json.loads(response.data)
        assert data == {"status": "success",
                        "message": "Feedback Added"} or data == {"status": "error", "message": "You have already submited feedback."} or data == {"status": "error", "message": "You are not logged In"}

    # ----------------------user routes test cases ends----------------------

    # ----------------------admin routes test cases----------------------------

    def test_show_menu_route(self):
        # Simulate a session with "admin" role
        with self.client.session_transaction() as sess:
            sess["role"] = "admin"

        # Send GET request to the /menu route
        response = self.client.get("/menu")

        # Verify the response
        assert response.status_code == 200

        # Check if the response data contains the expected HTML content
        assert b'<title>Zesty Yum - Menu</title>' in response.data

        # Check if the menu list is present in the response data
        menu = list(response.data.decode())
        assert menu is not None
        assert isinstance(menu, list)
        assert len(menu) > 0

    def test_show_menu_route_unauthorized(self):
        # Simulate a session with "user" role
        with self.client.session_transaction() as sess:
            sess["role"] = "user"

        # Send GET request to the /menu route
        response = self.client.get("/menu")

        # Verify the response
        assert response.status_code == 200
        assert response.get_data(as_text=True) == "Access denied"
