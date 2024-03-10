from flask import Flask, request, jsonify, render_template
import time


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    processed_text = data['message']
    print(processed_text)
    time.sleep(2)
    return jsonify({'message': processed_text})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8011)

