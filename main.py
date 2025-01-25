import os
import json
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Connexion en cours", language="fr-FR")
    connect = Connect()
    connect.stream(url=f'wss://{request.headers["host"]}/media')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            print(f"Received: {data}")
            
            if data.get('event') == 'media':
                await websocket.send_json({
                    "event": "media",
                    "streamSid": data.get('streamSid'),
                    "media": data.get('media')
                })
    except Exception as e:
        print(f"Error: {e}")
