import json
import os

from flask import Flask, request, jsonify, render_template, session, make_response, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from dotenv import load_dotenv

import psycopg2
import jwt
from datetime import datetime, timedelta, timezone

from functools import wraps

secret_key = os.getenv("secret_key")

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key

load_dotenv()  # Loads environment variables
user = os.getenv("user")
password = os.getenv("password")
dbname = os.getenv("dbname")
host = os.getenv("host")
port = os.getenv("port")

# Connects to my supabase database


def get_db_connection():
    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )


def validate_token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')

        if not token:
            session.pop('logged_in', None)
            return render_template('login.html')

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            session.pop('logged_in', None)
            response = make_response(redirect(url_for('login')))
            response.set_cookie('token', '', expires=0)
            return response
        except jwt.InvalidTokenError:
            session.pop('logged_in', None)
            return redirect(url_for('login'))

        return func(*args, **kwargs)

    return decorated


# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "20 per hour"],
    storage_uri="memory://"
)


@app.route('/', methods=['GET'])
@validate_token
@limiter.exempt
def home():
        return render_template('home.html')

@app.route('/auth', methods=['GET'])
@validate_token
def auth():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"message": "Missing username or password"}), 400

        if username == 'abdul' and password == '12345':
            session['logged_in'] = True
            token = jwt.encode(
                {'user': username, 'exp': datetime.now(
                    timezone.utc) + timedelta(seconds=120)},
                app.config['SECRET_KEY'],
                algorithm="HS256"
            )
            response = make_response(jsonify({"message": "Login successful"}))
            response.set_cookie(
                'token',
                token,
                httponly=True,
                secure=True,
                samesite='Strict'
            )
            return response

    return jsonify({"message": "Invalid credentials"}), 401


@app.route('/products', methods=['POST'])  # Creates a product
def create_product():
    response = request.get_json()  # Gets the product from the request
    if not response:
        # Returns an error if no product is provided
        return jsonify({"message": "No product provided"}), 400

    # Reads the file and puts it in data
    # with open('static/data/newproducts.json', "r", encoding="utf-8") as f:
    #     data = json.load(f)
    # data["products"].append(response)  # Appends gotten product to the data
    # with open('static/data/newproducts.json', "w", encoding="utf-8") as f:
    #     json.dump(data, f)

    # Connects to the database and inserts the product
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS products(id SERIAL PRIMARY KEY, name VARCHAR(255), price FLOAT)""")
        cur.execute("""INSERT INTO products (name, price) VALUES (%s, %s);""",
                    (response['name'], response['price']))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while creating the product", "error": str(e)}), 500

    return jsonify({"message": "Product created successfully", "product_name": response['name']}), 201


@app.route('/products', methods=['GET'])  # Fetches all products
def get_products():
    # Connects to the database and fetches all products
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "CREATE INDEX idx_products ON products(name, price); SELECT name, price FROM products")
        products = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the products", "error": str(e)}), 500

    return jsonify({"message": "Products fetched successfully", "products": products}), 200


@app.route('/products/<int:id>', methods=['GET'])  # Fetches a product by id
def get_product(id):
    # Connects to the database and fetches the product by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name, price FROM products WHERE id = %s", (id,))
        product = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the product", "error": str(e)}), 500
    return jsonify({"message": "Product fetched successfully", "product": product}), 200


@app.route('/products/<int:id>', methods=['DELETE'])  # Deletes a product by id
def delete_product(id):
    # Connects to the database and deletes the product by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while deleting the product", "error": str(e)}), 500
    return jsonify({"message": "Product deleted successfully"}), 200


@app.route('/products/<int:id>', methods=['PUT'])  # Updates a product by id
def update_product(id):
    response = request.get_json()  # Gets the product from the request
    if not response:
        # Returns an error if no product is provided
        return jsonify({"message": "No product provided"}), 400

    # Connects to the database and updates the product by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE products SET name = %s, price = %s WHERE id = %s",
                    (response['name'], response['price'], id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while updating the product", "error": str(e)}), 500
    return jsonify({"message": "Product updated successfully"}), 200


@app.route('/orders', methods=['POST'])  # Creates an order
def create_order():
    response = request.get_json()
    if not response:
        return jsonify({"message": "No order provided"}), 400

    # Connects to the database and inserts the order
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS orders(order_id SERIAL PRIMARY KEY, product_id INT, quantity INT, FOREIGN KEY (product_id) REFERENCES products(id))""")
        cur.execute("""INSERT INTO orders (product_id, quantity) VALUES (%s, %s);""",
                    (response['product_id'], response['quantity']))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while creating the order", "error": str(e)}), 500

    return jsonify({"message": "Order created successfully"}), 201


@app.route('/orders', methods=['GET'])  # Fetches all orders
def get_orders():
    # Connects to the database and fetches all orders
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, p.name, p.price, o.quantity FROM products p JOIN orders o ON p.id = o.product_id;")
        orders = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the orders", "error": str(e)}), 500

    return jsonify({"message": "Orders fetched successfully", "orders": orders}), 200


@app.route('/orders/<int:id>', methods=['GET'])  # Fetches an order by id
def get_order(id):
    # Connects to the database and fetches the order by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, p.name, p.price, o.quantity FROM products p JOIN orders o ON p.id = o.product_id WHERE o.order_id = %s;", (id,))
        order = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the order", "error": str(e)}), 500
    return jsonify({"message": "Order fetched successfully", "order": order}), 200


@app.route('/orders/<int:id>', methods=['DELETE'])  # Deletes an order by id
def delete_order(id):
    # Connects to the database and deletes the order by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE order_id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while deleting the order", "error": str(e)}), 500
    return jsonify({"message": "Order deleted successfully"}), 200


@app.route('/orders/<int:id>', methods=['PUT'])  # Updates an order by id
def update_order(id):
    response = request.get_json()  # Gets the order from the request
    if not response:
        # Returns an error if no order is provided
        return jsonify({"message": "No order provided"}), 400

    # Connects to the database and updates the order by id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET product_id = %s, quantity = %s WHERE order_id = %s",
                    (response['product_id'], response['quantity'], id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while updating the order", "error": str(e)}), 500

    return jsonify({"message": "Order updated successfully"}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
