from flask import Flask, render_template, request, redirect, json, session, jsonify
from flask_cors import CORS
import bcrypt
import jwt
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from bson import ObjectId
from functools import wraps
import openai
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = "your_secret_key"
    CORS(app)
    socketio = SocketIO(app)

    # -----------------MongoDB connection-----------------
    client = MongoClient(os.getenv("DATABASE_URL"))
    db = client["restaurant"]
    menu_collection = db["menu"]
    orders_collection = db["orders"]
    users_collection = db["users"]
    cart_collection = db["cart"]
    feedback_collection = db["feedback"]
    # -----------------MongoDB connection end-----------------

    # -----------------OpenAI API configuration-----------------
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # -----------------OpenAI API end-----------------

    # -----------------SocketIO connection-----------------

    @socketio.on('connect', namespace='/order')
    def order_connect():
        socketio.emit(
            'Greet', {'data': 'Hello from the server'}, namespace='/order')
        print('Client connected')

    @socketio.on('disconnect', namespace='/order')
    def order_disconnect():
        print('Client disconnected')

    # -----------------SocketIO connection end-----------------

    # -----------------middleware-----------------

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print(session.get("role"))
            if session.get("role") != "admin":
                return "Access denied"
            return f(*args, **kwargs)
        return decorated_function

    # -----------------middleware end-----------------

    # -----------------Admin routes-----------------

    @app.route("/menu")
    @admin_required
    def show_menu():
        menu = list(menu_collection.find())
        return render_template("menu.html", menu=menu)

    @app.route("/add-menu", methods=["POST"])
    @admin_required
    def add_menu():
        dish_name = request.form.get("dish_name")
        price = request.form.get("price")
        availability = request.form.get("availability")
        img = request.form.get("img")

        dish = {
            "dish_name": dish_name,
            "price": price,
            "availability": availability,
            "img": img,
        }

        menu_collection.insert_one(dish)

        return redirect("/menu")

    @app.route("/remove-dish/<dish_id>", methods=["POST"])
    @admin_required
    def remove_dish(dish_id):
        menu_collection.delete_one({"_id": ObjectId(dish_id)})
        return redirect("/menu")

    @app.route("/update-dish", methods=["POST"])
    @admin_required
    def update_dish():
        dish_id = request.form.get("dish_id")
        dish_name = request.form.get("dish_name")
        price = request.form.get("price")
        availability = request.form.get("availability")
        img = request.form.get("img")

        menu_collection.update_one(
            {"_id": ObjectId(dish_id)},
            {"$set": {
                "dish_name": dish_name,
                "price": price,
                "availability": availability,
                "img": img
            }}
        )

        return redirect("/menu")

    @app.route("/show-orders")
    @admin_required
    def show_orders():
        orders = list(orders_collection.find())
        return render_template("show_orders.html", orders=orders)

    @app.route("/update-status/<order_id>", methods=["POST"])
    @admin_required
    def update_status(order_id):
        status = request.form["status"]

        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": status}}
        )

        socketio.emit('order_status_updated', {
            'orderId': order_id,
            'status': status
        }, namespace='/order')

        return redirect("/show-orders")

    @app.route("/delete-order/<order_id>", methods=["POST"])
    @admin_required
    def delete_order(order_id):
        orders_collection.delete_one({"_id": ObjectId(order_id)})
        return redirect("/show-orders")

    # -----------------Admin routes end-----------------

    # -----------------Normal user routes-----------------
    first_quest = True

    @app.route("/register", methods=["POST"])
    def register():
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = "user"

        # Check if the user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return json.dumps({"status": 'error', 'message': "User already exists!"})

        # Hash the password
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt())

        # Create a new user document
        user = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role,
        }

        users_collection.insert_one(user)

        return json.jsonify({"status": "success", "message": "User registered successfully!"}), 200

    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            # Check if the user exists
            print(email, password)
            user = users_collection.find_one({"email": email})
            print(user)
            if user:
                # Verify the password
                if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
                    # Authentication successful
                    # payload = {"email": email, "user_id": user.get("_id")}

                    # token = jwt.encode(payload, app.secret_key, algorithm="HS256")

                    # Store the token in the session
                    # session["token"] = token
                    session["username"] = user.get("name")
                    session["user_id"] = str(user.get("_id"))
                    session["email"] = email
                    session["role"] = user.get("role")
                    return json.dumps({"status": 'success', 'message': "Login Successful"})
                else:
                    # Invalid credentials
                    return json.dumps({"status": 'error', 'message': "Invalid credentials!"})
            else:
                return json.dumps({"status": 'error', 'message': "User does not exist!"})
        # GET request, show the login form
        return render_template("login.html")

    @app.route("/new-order", methods=["POST", "GET"])
    def new_order():
        if request.method == "POST":
            # Process the form submission and add the order
            customer_name = session.get("username")
            order_user_id = session.get("user_id")

            if customer_name is None or order_user_id is None:
                return json.dumps({"status": "error", "message": "You are not logged in"})

            dishes = request.form.get("dishes")
            dishes = json.loads(dishes)

            dish_ids = []
            dish_names = []
            dish_imgs = []

            for dish in dishes:
                dish_ids.append(ObjectId(dish["_id"]))
                dish_names.append(dish["dish_name"])
                dish_imgs.append(dish["img"])

            total_price = sum(
                [int(dish["price"])
                 for dish in menu_collection.find({"_id": {"$in": dish_ids}})]
            )

            order = {
                "customer_name": customer_name,
                "user_id": ObjectId(order_user_id),
                "dish_ids": dish_ids,
                "dish_names": dish_names,
                "total_price": total_price,
                "dish_imgs": dish_imgs,
                "status": "received",
            }
            orders_collection.insert_one(order)

            return redirect("/my-orders")
        else:
            menu = list(menu_collection.find())
            return render_template("new_order.html", menu=menu)

    @app.route("/my-orders")
    def my_orders():
        global first_quest
        first_quest = True
        user_id = session.get("user_id")
        orders = list(orders_collection.find({"user_id": ObjectId(user_id)}))
        return render_template("myorders.html", orders=orders), 200

    @app.route("/single-order/<order_id>", methods=["GET"])
    def single_order(order_id):
        singleOrd = orders_collection.find_one({"_id": ObjectId(order_id)})
        return render_template("single_order.html", singleOrd=singleOrd)

    @app.route("/add-feedback", methods=["POST"])
    def add_feed():
        data = request.json
        order_id = data["order_id"]
        user_feedback = data["user_feedback"]
        rating = data["rating"]
        dishIds = data["dishIds"]

        user_id = session.get("user_id")

        # check if user has already added a feedback to the order
        is_present = feedback_collection.find_one({
            'user_id': ObjectId(user_id),
            'order_id': ObjectId(order_id)
        })

        if is_present is not None:
            return json.dumps({"status": "error", "message": "You have already submited feedback."})

        newFeedBk = {
            'user_id': ObjectId(user_id),
            'order_id': ObjectId(order_id),
            'user_feedback': user_feedback,
            'rating': rating,
            'dish_ids': dishIds
        }

        if user_id is None:
            return json.dumps({"status": "error", "message": "You are not logged In"})

        feedback_collection.insert_one(newFeedBk)
        return json.dumps({"status": "success", "message": "Feedback Added"})

    # ----------------chatbot----------------

    def generate_prompt(query):
        capitalized_query = query[0].upper() + query[1:].lower()
        very_first_q = f"""
            Take a role of a food app 'chatboat' and generate a small response to the user's query: {capitalized_query},
            try to be as creative as possible. You may give real-life examples or response.
            The response should be at max 2 line not more than that, less would work. If user asks for a dish, you may give a description of the dish. If user asks for a restaurant, you may give a description of the restaurant. if user asks a question other than food, restaurants or other food related topics then you may give a general response.
        """
        other_q = f""" 
            User: {capitalized_query} \n
            NOTE: maximum 2 lines response \n
            Chatboat:
        """
        return very_first_q if first_quest else other_q

    @app.route("/chatboat", methods=["POST"])
    def generate_response():
        response_topic = request.json.get("responseTopic")
        try:
            response = generate_prompt(response_topic)
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": response}]
            )
            result = completion["choices"][0]["message"]["content"]
            global first_quest
            first_quest = False
            return json.dumps({"response": result, "ok": True})
        except Exception as e:
            print(e)
            first_quest = True
            return json.dumps({"error": str(e), "ok": False})

    return app


app = create_app()
CORS(app)

# ----------------normal user routes end----------------
if __name__ == "__main__":
    app.run(debug=True)
