from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import json
import websocket

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Connexion à OpenAI via WebSocket
url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
headers = [
    f"Authorization: Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta: realtime=v1"
]

def on_open(ws):
    print("Connected to OpenAI Realtime API")
    event = {
        "type": "response.create",
        "response": {
            "modalities": ["text"],
            "instructions": "Please assist the user."
        }
    }
    ws.send(json.dumps(event))

def on_message(ws, message):
    data = json.loads(message)
    print("Received event:", json.dumps(data, indent=2))

ws = websocket.WebSocketApp(
    url,
    header=headers,
    on_open=on_open,
    on_message=on_message
)

@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    """Twilio webhook to handle incoming calls"""
    response = VoiceResponse()
    response.say("Bienvenue sur la hotline IA. Posez votre question après le bip.", voice="alice", language="fr-FR")

    # Enregistrer la voix de l'utilisateur
    response.record(
        action="/process-recording",
        max_length="30",
        play_beep=True
    )

    return str(response)

@app.route("/process-recording", methods=["POST"])
def process_recording():
    """Traitement de l'enregistrement vocal"""
    recording_url = request.form.get('RecordingUrl')
    print(f"Recording URL received: {recording_url}")

    # Répondre à l'appelant
    response = VoiceResponse()
    response.say("Merci pour votre message. Nous allons vous répondre sous peu.", voice="alice", language="fr-FR")

    return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
