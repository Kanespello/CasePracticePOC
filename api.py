from flask import Flask, request, jsonify, render_template
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
thread = client.beta.threads.create()
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    processed_text = data['message']
    print(processed_text)
    

    run_id = run_assistant(client, processed_text, thread)
    run_status = wait_for_run_completion(client, thread.id, run_id)
    if run_status.status == "completed":
        print("Assistant response received:")
        return jsonify({'message': return_last_msg(client, thread.id)})
    else:
        return jsonify({'message': "Error"})


assistant_id = 'asst_7RrpQGctGtbuCQosef4Vw8rs'

# Runs the assistant and returns the thread_id and run_id
def run_assistant(client, user_input, thread):
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )
    return run.id


# Waits for the run to be completed and returns the run status.
def wait_for_run_completion(client, thread_id, run_id):
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        if run_status.status in ["completed", "failed"]:
            return run_status
        time.sleep(1)


# Prints the messages from the thread.
def return_last_msg(client, thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    print(f"Number of messages: {len(messages.data)}")
    for message in reversed(messages.data):
        role = message.role
        print(role)
        if role !='user':
            for content in message.content :
                if content.type == "text":
                    return content.text.value



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8011)



