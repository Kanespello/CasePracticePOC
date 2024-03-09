from flask import Flask, request, jsonify, render_template
import time


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    processed_text = data['message']
    time.sleep(10)
    return jsonify({'message': processed_text})

if __name__ == '__main__':
    app.run(debug=True)

