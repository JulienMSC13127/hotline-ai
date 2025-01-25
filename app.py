from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import json
import websocket

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Connexion au WebSocket OpenAI
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
    print("Received response from AI:", json.dumps(data, indent=2))

ws = websocket.WebSocketApp(
    url,
    header=headers,
    on_open=on_open,
    on_message=on_message
)

@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    """Twilio webhook pour gérer les appels entrants"""
    response = VoiceResponse()
    
    # Faire parler l'IA directement
    response.say("Bonjour, comment puis-je vous aider ?", voice="alice", language="fr-FR")

    # Ajouter une option pour continuer la conversation
    response.gather(
        input="speech",
        action="/process-speech",
        speechTimeout="auto"
    )
    
    return str(response)

@app.route("/process-speech", methods=["POST"])
def process_speech():
    """Traitement de la parole enregistrée par Twilio"""
    user_input = request.form.get('SpeechResult')
    print(f"Utilisateur a dit : {user_input}")

    # Simulation de l'envoi au modèle OpenAI
    response = VoiceResponse()
    response.say(f"Vous avez dit : {user_input}. Laissez-moi réfléchir...", voice="alice", language="fr-FR")

    # Simuler une réponse AI
    ai_response = "Je pense que la meilleure solution est d'essayer encore une fois."

    response.say(ai_response, voice="alice", language="fr-FR")

    response.pause(length=2)
    response.say("Avez-vous une autre question ?", voice="alice", language="fr-FR")

    # Relancer une nouvelle écoute de l'utilisateur
    response.gather(input="speech", action="/process-speech", speechTimeout="auto")

    return str(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
