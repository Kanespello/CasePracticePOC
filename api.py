from flask import Flask, request, jsonify, render_template, session
from flask_session import Session 
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route('/')
def index():
    if 'thread_id' not in session:
        thread = client.beta.threads.create()
        session['thread_id'] = thread.id
    return render_template('dashboard.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    processed_text = data['message']
    print(processed_text)

    thread_id = session.get('thread_id')
    if thread_id is None:
        return jsonify({'message': "Session Error"})

    run_id = run_assistant(client, processed_text, thread_id)
    run_status = wait_for_run_completion(client, thread_id, run_id)
    if run_status.status == "completed":
        print("Assistant response received:")
        return jsonify({'message': return_last_msg(client, thread_id)})
    else:
        return jsonify({'message': "Error"})

def run_assistant(client, user_input, thread_id):
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input,
    )
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    return run.id


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8011)
