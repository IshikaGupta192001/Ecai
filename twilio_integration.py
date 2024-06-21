import os
from flask import Flask, request, redirect, session, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.cloud import dialogflow_v2 as dialogflow
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Automatically generate a secure secret key

# Path to your OAuth 2.0 client secrets file
CLIENT_SECRETS_FILE = 'google_creds.json'
DIALOGFLOW_PROJECT_ID = 'appointmentbookingagent-fwua'
DIALOGFLOW_LANGUAGE_CODE = 'en'

# Configure the OAuth 2.0 client
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=['https://www.googleapis.com/auth/cloud-platform'],
    redirect_uri='http://localhost'
)

@app.route('/')
def index():
    return 'Welcome to the Dialogflow Twilio Integration!'

@app.route('/authorize')
def authorize():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('voice'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def detect_intent_texts(project_id, session_id, text, language_code):
    credentials = Credentials(**session['credentials'])
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    return response.query_result

@app.route('/voice', methods=['POST'])
def voice():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    response = VoiceResponse()
    call_sid = request.values.get('CallSid')
    session_id = call_sid

    gather = Gather(input='speech', action='/process_speech', method='POST')
    gather.say("Hi, how can I assist you today?")
    response.append(gather)

    return str(response)

@app.route('/process_speech', methods=['POST'])
def process_speech():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    response = VoiceResponse()
    call_sid = request.values.get('CallSid')
    session_id = call_sid

    user_input = request.values.get('SpeechResult', '')
    dialogflow_result = detect_intent_texts(DIALOGFLOW_PROJECT_ID, session_id, user_input, DIALOGFLOW_LANGUAGE_CODE)

    fulfillment_text = dialogflow_result.fulfillment_text
    intent_name = dialogflow_result.intent.display_name

    if intent_name in ['Booking Appointment Intent', 'Provide Date Intent', 'Provide Time Intent', 'Decline Confirmation Intent']:
        gather = Gather(input='speech', action='/process_speech', method='POST')
        gather.say(fulfillment_text)
        response.append(gather)
    else:
        response.say(fulfillment_text)

    return str(response)

if __name__ == '__main__':
    app.run(debug=True)
