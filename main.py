import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Start, Stream
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SYSTEM_MESSAGE = "Vous êtes un assistant AI sympathique qui répond en français."

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f'wss://{request.headers["host"]}/media')
    response.append(connect)
    response.say("Bienvenue sur la hotline AI. Comment puis-je vous aider?", language="fr-FR")
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async with websockets.connect(
        'wss://api.openai.com/v1/audio/speech',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    ) as openai_ws:
        stream_sid = None
        
        async def receive_from_twilio():
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media':
                        await openai_ws.send(json.dumps({
                            "audio": data['media']['payload'],
                            "model": "whisper-1"
                        }))
            except WebSocketDisconnect:
                print("Client déconnecté")

        async def send_to_twilio():
            try:
                async for message in openai_ws:
                    response = json.loads(message)
                    if response.get('audio'):
                        await websocket.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": response['audio']
                            }
                        })
            except Exception as e:
                print(f"Erreur: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())
