from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import json
import websocket
import threading
import requests
import time

app = Flask(__name__)

# Configurations
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-realtime-preview-2024-12-17"

# WebSocket OpenAI API details
url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
headers = [
    f"Authorization: Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta: realtime=v1"
]

# Function to keep the WebSocket connection alive
def keep_alive(ws):
    while ws.sock and ws.sock.connected:
        time.sleep(30)
        ws.send(json.dumps({"type": "ping"}))

# Function to transcribe Twilio audio using OpenAI Whisper
def transcribe_audio(audio_url):
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

# Function to convert AI text response to speech
def generate_audio(text):
    """Convert text response to audio MP3 using OpenAI TTS"""
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
        with open("static/response.mp3", "wb") as f:
            f.write(response.content)
        return "static/response.mp3"
    return None

# WebSocket connection to OpenAI
def send_to_openai(text):
    ws = websocket.WebSocketApp(url, header=headers)
    
    def on_open(ws):
        print("WebSocket connected to OpenAI Realtime API.")
        ws.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["text"],
                "instructions": text
            }
        }))
    
    def on_message(ws, message):
        data = json.loads(message)
        ai_text = data.get("choices", [{}])[0].get("content", "Je n'ai pas compris.")
        print(f"AI Response: {ai_text}")
        generate_audio(ai_text)
    
    ws.on_open = on_open
    ws.on_message = on_message

    # Start the connection
    ws.run_forever()

# Twilio route to handle incoming calls
@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    response = VoiceResponse()
    response.say("Bonjour, bienvenue sur la hotline IA. Posez votre question après le bip.", voice="alice", language="fr-FR")

    response.record(
        action="/process-recording",
        max_length="30",
        play_beep=True
    )
    return str(response)

# Process the recording from Twilio and send to OpenAI
@app.route("/process-recording", methods=["POST"])
def process_recording():
    recording_url = request.form.get("RecordingUrl")
    print(f"Enregistrement reçu : {recording_url}")

    response = VoiceResponse()
    response.say("Votre message est en cours de traitement, veuillez patienter.", voice="alice", language="fr-FR")

    # Process the audio transcription and AI response asynchronously
    threading.Thread(target=handle_ai_request, args=(recording_url,)).start()

    return str(response)

def handle_ai_request(recording_url):
    transcript = transcribe_audio(recording_url)
    print(f"Transcription: {transcript}")
    
    send_to_openai(transcript)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
