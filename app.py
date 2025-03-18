import json
import os

from flask import Flask, request, jsonify, render_template, redirect, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
import psycopg2

app = Flask(__name__)

load_dotenv() # Loads environment variables
user = os.getenv("user")
password = os.getenv("password")
dbname = os.getenv("dbname")
host = os.getenv("host")
port = os.getenv("port")

# Connects to my supabase database
conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

@app.route('/', methods=['GET'])
@app.route('/<name>', methods=['GET'])
def home(name=None):
    return render_template('index.html', person=name)


@app.route('/products', methods=['POST']) # Creates a product
def create_product():
    response = request.get_json() # Gets the product from the request
    if not response:
        return jsonify({"message": "No product provided"}), 400 # Returns an error if no product is provided

    # Reads the file and puts it in data
    with open('static/data/newproducts.json', "r", encoding="utf-8") as f:
        data = json.load(f)
    data["products"].append(response) # Appends gotten product to the 
    with open('static/data/newproducts.json', "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Connects to the database and inserts the product
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS products(id SERIAL PRIMARY KEY, name VARCHAR(255), price FLOAT)")
        cur.execute("INSERT INTO products (name, price) VALUES (%s, %s)", (response['name'], response['price']))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while creating the product", "error": str(e)}), 500
    
    return jsonify({"message": "Product created successfully", "product_name": response['name']}), 201

@app.route('/products', methods=['GET']) # Fetches all products
def get_products():
    # Connects to the database and fetches all products
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products")
        products = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the products", "error": str(e)}), 500

    return jsonify({"message": "Products fetched successfully", "products": products}), 200

@app.route('/products/<int:id>', methods=['GET']) # Fetches a product by id
def get_product(id):
    # Connects to the database and fetches the product by id
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id = %s", (id,))
        product = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while fetching the product", "error": str(e)}), 500
    return jsonify({"message": "Product fetched successfully", "product": product}), 200

@app.route('/products/<int:id>', methods=['DELETE']) # Deletes a product by id
def delete_product(id):
    # Connects to the database and deletes the product by id
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"message": "An error occurred while deleting the product", "error": str(e)}), 500
    return jsonify({"message": "Product deleted successfully"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)