from flask import Flask, request, jsonify, render_template, redirect, url_for
import json

app = Flask(__name__)

@app.route('/', methods=['GET'])
@app.route('/<name>', methods=['GET'])
def home(name=None):
    return render_template('index.html', person=name)

@app.route('/api/products', methods=['GET'])
def get_products():
    with open('static/data/fakeproducts.json', "r", encoding="utf-8") as f:
        products = json.load(f)
    print(products)
    #return redirect('https://fakestoreapi.com/products')
    return jsonify(products)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)