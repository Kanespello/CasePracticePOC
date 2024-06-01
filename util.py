import requests
from dotenv import load_dotenv
import os

load_dotenv()

def save_assistant_thread(session_id, assistant_id, thread_id):
    url = 'http://localhost:9033/session/api/v1/saveAssistantThread'
    headers = {'Content-Type': 'application/json'}
    data = {
        "sessionId": session_id,
        "threadId": thread_id,
        "assistantId": assistant_id
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    return None

def get_session_details(session_id):
    url = f'http://localhost:9033/session/api/v1/getSessionDetails?sessionId={session_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json()!=None and 'data' in response.json() :
        return response.json()['data']
    return None
   

def get_assistant_thread(session_id):
    url = f'http://localhost:9033/session/api/v1/getAssistantThread?sessionId={session_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data!=None and 'data' in data and data['data']!=None:
        	return data['data']['threadId'], data['data']['assistantId']
    return None, None
    

def get_transcript(session_id):
    url = f'http://localhost:9033/session/api/v1/getTranscript?sessionId={session_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)    
    if response.status_code == 200 and response.json()!=None and 'data' in response.json() and response.json()['data']!=None and 'conversationTuples' in response.json()['data'] and response.json()['data']['conversationTuples']!=None:
        return response.json()['data']['conversationTuples']
    return None


def save_conversation(session_id, interviewer_text, interviewee_text):
    url = "http://localhost:9033/session/api/v1/saveConversation"

    payload = {
        "sessionId": session_id,
        "conversationTuple": {
            "intervieweeText":interviewee_text,
            "interviewerText":interviewer_text
        }
    }

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print("Conversation saved successfully:", response.json())
    else:
        print("Failed to save conversation:", response.json())


def save_analysis(session_id, analysis, summary, caseTitle):
    url = "http://localhost:9033/session/api/v1/saveAnalysis"

    payload = {
        "sessionId": session_id,
        "analysisParams": analysis,
        "summary":summary,
        "caseTitle":caseTitle
    }

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print("analysis saved successfully:", response.json())
    else:
        print("Failed to save analysis:", response.json())


def register(name, email):
    url = "http://localhost:9033/registration/api/v1/register"

    payload = {
        "name": name,
        "email": email
    }

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        
        if response.json()!=None and 'data' in response.json() and 'userId' in response.json()['data']:
            return response.json()['data']['userId']

    else:
        print("Failed to register:", response.json())


def get_assistant(session_details):

	if session_details!=None and 'sessionDetails' in session_details and 'role' in session_details['sessionDetails'] and session_details['sessionDetails']['role']!=None:
		if session_details['sessionDetails']['role'] == 'consultant':
			return os.getenv('CONSULTANT_ASSISTANT_ID')
		elif session_details['sessionDetails']['role'] == 'product':
			return os.getenv('PRODUCT_ASSISTANT_ID')




