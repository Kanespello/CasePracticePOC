from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for, abort
from flask_session import Session
import os
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from openai import OpenAI
import time
from textwrap import wrap
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import re
import json

from flask_cors import CORS

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")
client = OpenAI(api_key=openai_api_key)

app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = 1800
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
YOUR_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
Session(app)

@app.route('/verify_google_token', methods=['POST', 'GET'])
def verify_google_token():
    token = request.form.get('credential')
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), YOUR_CLIENT_ID)
        session['user_id'] = idinfo['sub']
        user_email = idinfo['email']
        user_name = idinfo.get('name')  
        print(user_email)
        print(user_name)
        print(idinfo['sub'])
        return redirect(url_for('index'))
    except ValueError:
        abort(401)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/')
def index():
    if 'user_id' in session:
        if 'thread_id' not in session:
            thread = client.beta.threads.create()
            session['thread_id'] = thread.id
            session.modified = True 
            if 'transcript' not in session:
                session['transcript'] = []
        return render_template('dashboard.html')
    return render_template('login.html', GOOGLE_CLIENT_ID=YOUR_CLIENT_ID)
    # return send_from_directory('.', 'login.html')

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
    if transcript_text and len(transcript_text)>1000:
        prompt = '''Analyze the given case interview transcript. The feedback should be structured to comprehensively cover applicable aspects, only addressing those observed within the transcript. For each parameter, provide feedback in a single line followed by subparameter feedback, if applicable. Rate each subparameter out of 10 and provide a brief description.

Use these tokens for showing starting and ending.
<r>rating value</r>
<mp>major param heading</mp>
<mpd>major param desc</mpd>
<sp><sub param heading/sp>
<spd>sub param desc</spd>

Communication: Evaluate the candidate's clarity in conveying ideas, organization and coherence of responses, conciseness in expressing ideas, appropriateness of language and grammar, and evidence of active listening. Only include categories and subcategories that are applicable based on the transcript. Highlight areas for improvement where communication may lack effectiveness or clarity.

Analytical Thinking: Assess the understanding of core issues, skill in interpreting data, ability to generate relevant hypotheses, and prioritization of key factors. Each feedback point should be given only if these aspects are demonstrated in the transcript. Identify gaps in analytical reasoning or areas that could benefit from deeper analysis.

Problem-Solving: Examine the structured approach to problems, creativity of solutions, practicality of solution assessments, adaptability to new information, and considerations for implementation. Feedback should skip any element not evidenced in the discussion. Point out instances where problem-solving strategies could be enhanced or where alternative approaches may yield better outcomes.

Collaboration: Gauge the ability to engage and build rapport, and flexibility in receiving feedback. Include comments on these only if interaction dynamics are clearly presented. Mention any missed opportunities for collaboration or areas where communication could be improved to foster better teamwork.

Business Acumen: Focus on industry knowledge and strategic thinking, providing feedback if these areas are discussed or demonstrated. Suggest areas where further industry insight or strategic considerations could strengthen the candidate's approach.

Presentation Skills: Review confidence and persuasion in presenting solutions. Feedback should be limited to these aspects if they are relevant to the performance observed. Offer constructive criticism on how presentation skills could be improved, such as through better structuring, more persuasive arguments, or enhanced confidence.

Include additional categories such as Math & Calculations or Teamwork & Etiquette if applicable, structured similarly with descriptions and ratings for main parameters and subparameters.

This structured feedback mechanism aims for clarity and conciseness, ensuring readability and directness in evaluation. Only provide feedback on aspects that are clearly demonstrated or applicable as per the transcript, avoiding assumptions or hallucinations about missing information. Additionally, ensure feedback is balanced, recognizing strengths while also pointing out areas for improvement, fostering a constructive and realistic evaluation. Do not provide additional comments just give feedback on the respective parameters'''
        # detailed_prompt = f"{prompt}\n\n{transcript_text}"

        response = client.chat.completions.create(
          model="gpt-4-turbo-preview",
          messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcript_text}
          ],
          temperature=0.8,
          max_tokens=1024,
          top_p=0.9,
          frequency_penalty=0.5,
          presence_penalty=0.4
        )

        analysis = response.choices[0].message.content.strip()
        session['analysis'] = parse_evaluation_data(analysis)
        return jsonify({'analysis': session['analysis']})
    return jsonify({'analysis': "There is no transcript or very small transcript for analysis"})

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
        time.sleep(2)


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

def wrap_text(text, width, canvas):
    lines = wrap(text, width) 
    return lines

def parse_evaluation_data(input_data):
    # Adjust regex to correctly handle main parameter blocks until another <mp> or end of input
    main_param_pattern = re.compile(r'<mp>(.*?)</mp>\s*<mpd>(.*?)</mpd>((?:.(?!<mp>))*.)', re.DOTALL)
    
    # Updated sub_param_pattern to handle <r> tag before or after <spd>
    sub_param_pattern = re.compile(
        r'<sp>(.*?)</sp>\s*(?:<spd>(.*?)</spd>\s*)?<r>(.*?)</r>\s*(?:<spd>(.*?)</spd>)?', re.DOTALL)

    main_params_list = []

    # Process each main parameter block
    for mp_match in main_param_pattern.finditer(input_data):
        mp_name = mp_match.group(1).strip()
        mp_description = mp_match.group(2).strip()
        mp_content = mp_match.group(3)

        sub_params_list = []
        scores = []

        # Process each sub-parameter within the current main parameter block
        for sp_match in sub_param_pattern.finditer(mp_content):
            sp_name = sp_match.group(1).strip()
            sp_description = sp_match.group(2) or sp_match.group(4)  # Handle either position of <spd>
            sp_description = sp_description.strip() if sp_description else "No description provided"
            sp_score_raw = sp_match.group(3).strip()
            sp_score = int(sp_score_raw) if sp_score_raw.isdigit() else None

            sub_params_list.append({
                "analysisParam": sp_name,
                "analysisParamDesc": sp_description,
                "analysisParamScore": sp_score
            })
            if sp_score is not None:
                scores.append(sp_score)

        # Calculate the average score for the main parameter, handling cases with no scores
        average_score = sum(scores) // len(scores) if scores else 0

        main_params_list.append({
            "analysisDetailTuple": {
                "analysisParam": mp_name,
                "analysisParamDesc": mp_description,
                "analysisParamScore": average_score
            },
            "subParamsAnalysisDetailTuple": sub_params_list
        })

    # Convert the structured data into JSON
    output_json = json.dumps({"analysisParams": main_params_list}, indent=4)
    return output_json

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8011)


# https://console.cloud.google.com/apis/dashboard?project=valued-odyssey-419504&supportedpurview=project
