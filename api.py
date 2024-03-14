from flask import Flask, request, jsonify, send_file, render_template, session
from flask_session import Session
import os
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from openai import OpenAI
import time
from textwrap import wrap

def wrap_text(text, width, canvas):
    lines = wrap(text, width) 
    return lines

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)
assistant_id = 'asst_7RrpQGctGtbuCQosef4Vw8rs'

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = 1800
Session(app)

@app.route('/')
def index():
    if 'thread_id' not in session:
        thread = client.beta.threads.create()
        session['thread_id'] = thread.id
        session.modified = True 
        if 'transcript' not in session:
            session['transcript'] = []
    return render_template('dashboard.html')

@app.route('/end_interview', methods=['POST'])
def end_interview():
    return jsonify({'status': 'interview ended'})

@app.route('/download_transcript', methods=['GET'])
def download_transcript():
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y_position = height - 30
    p.drawString(72, y_position, "Interview Transcript")
    y_position -= 30
    max_width = 75  # Adjust based on your page layout and margins

    for entry in session.get('transcript', []):
        role = entry.get('role')
        text = entry.get('text')
        lines = wrap_text(f"{role}: {text}", max_width, p)
        
        for line in lines:
            y_position -= 20
            if y_position < 40:  # Check to ensure there is enough space for the line; adjust threshold as needed
                p.showPage()
                y_position = height - 30  # Reset y_position for the new page
            p.drawString(72, y_position, line)

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, mimetype='application/pdf', download_name='transcript.pdf')

@app.route('/analyze_results', methods=['GET'])
def analyze_results():
    transcript_text = "\n".join([f"{item['role']}: {item['text']}" for item in session.get('transcript', [])])
    if transcript_text:
        prompt = "Provide a detailed analysis of the following interview transcript in max 200 words, highlighting key strengths and areas for improvement."
        detailed_prompt = f"{prompt}\n\n{transcript_text}"

        response = client.completions.create(
          model="gpt-3.5-turbo-instruct",
          prompt=detailed_prompt,
          temperature=1,
          max_tokens=256,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0
        )

        analysis = response.choices[0].text.strip()
        session['analysis'] = analysis
        return jsonify({'analysis': analysis})
    return jsonify({'analysis': "There is no transcript for analysis"})

@app.route('/download_analysis', methods=['GET'])
def download_analysis():
    analysis = session.get('analysis', '')
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y_position = height - 30
    max_width = 75  # Adjust based on your page layout and margins
    
    p.drawString(72, y_position, "Interview Analysis")
    y_position -= 30

    # Assuming each 'paragraph' in analysis is separated by '\n'
    paragraphs = analysis.split('\n')
    for para in paragraphs:
        lines = wrap_text(para, max_width, p)
        for line in lines:
            y_position -= 20  # Increase this value to increase space between lines
            if y_position < 40:  # Ensure there is enough space for the line; adjust threshold as needed
                p.showPage()
                y_position = height - 30  # Reset y_position for the new page
            p.drawString(72, y_position, line)

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, mimetype='application/pdf', download_name='analysis.pdf')


@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    processed_text = data['message']

    session['transcript'].append({'role':'interviewee','text':processed_text})
    
    thread_id = session.get('thread_id')
    if thread_id is None:
        return jsonify({'message': "Session Error"})

    run_id = run_assistant(client, processed_text, thread_id)
    run_status = wait_for_run_completion(client, thread_id, run_id)
    if run_status.status == "completed":
        print("Assistant response received:")

        response = return_last_msg(client, thread_id)

        session['transcript'].append({'role':'interviewer','text':response})

        session.modified = True

        return jsonify({'message': response})
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

def wait_for_run_completion(client, thread_id, run_id):
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        if run_status.status in ["completed", "failed"]:
            return run_status
        time.sleep(1)


def return_last_msg(client, thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    print(f"Number of messages: {len(messages.data)}")
    for message in messages.data:
        role = message.role
        print(role)
        if role !='user':
            for content in message.content :
                if content.type == "text":
                    return content.text.value

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8011)
