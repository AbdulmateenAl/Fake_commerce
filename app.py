from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route('/', methods=['GET'])
@app.route('/<name>', methods=['GET'])
def home(name=None):
    return render_template('index.html', person=name)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)