from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import json
import websocket
import requests

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-realtime-preview-2024-12-17"

# WebSocket URL OpenAI Realtime
url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
headers = [
    f"Authorization: Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta: realtime=v1"
]

def on_open(ws):
    print("Connected to OpenAI Realtime API")

def on_message(ws, message):
    data = json.loads(message)
    print("AI Response:", json.dumps(data, indent=2))
    # Extraire la réponse texte et générer un fichier audio
    ai_text = data.get("choices", [{}])[0].get("content", "Je n'ai pas compris.")
    generate_audio(ai_text)

ws = websocket.WebSocketApp(
    url,
    header=headers,
    on_open=on_open,
    on_message=on_message
)

def generate_audio(text):
    """Convertir la réponse texte en audio MP3"""
    openai_api_url = "https://api.openai.com/v1/audio/speech"
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": "alloy"
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(openai_api_url, headers=headers, json=payload)
    if response.status_code == 200:
        with open("response.mp3", "wb") as f:
            f.write(response.content)
        return "response.mp3"
    return None

@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    """Twilio webhook pour gérer les appels entrants"""
    response = VoiceResponse()
    response.say("Bonjour, bienvenue sur la hotline IA. Dites-moi votre question après le bip.", voice="alice", language="fr-FR")
    response.record(action="/process-recording", max_length="30", play_beep=True)
    return str(response)

@app.route("/process-recording", methods=["POST"])
def process_recording():
    """Twilio envoie l'enregistrement vocal ici, puis il est transmis à l'IA."""
    recording_url = request.form.get("RecordingUrl")
    print(f"Enregistrement reçu : {recording_url}")

    # Envoyer l'audio Twilio à Whisper (transcription)
    transcript = transcribe_audio(recording_url)
    
    # Envoyer le texte transcrit à OpenAI
    ws.send(json.dumps({
        "type": "response.create",
        "response": {
            "modalities": ["text"],
            "instructions": transcript
        }
    }))

    # Lire la réponse audio
    audio_file = "response.mp3"
    if audio_file:
        response = VoiceResponse()
        response.play("https://hotline-ai.onrender.com/static/response.mp3")
        response.pause(length=2)
        response.say("Avez-vous une autre question ?", voice="alice", language="fr-FR")
        response.record(action="/process-recording", max_length="30", play_beep=True)
        return str(response)
    
    return str(VoiceResponse().say("Une erreur est survenue."))

def transcribe_audio(audio_url):
    """Transcrire l'audio de Twilio via OpenAI Whisper"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    audio_data = requests.get(audio_url).content
    files = {
        "file": ("audio.wav", audio_data, "audio/wav")
    }
    response = requests.post("https://api.openai.com/v1/audio/transcriptions",
                             headers=headers, files=files)
    return response.json().get("text", "Je n'ai pas compris.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
