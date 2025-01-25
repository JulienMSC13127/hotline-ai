import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()

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
    response.say("Bienvenue sur la hotline AI.", language="fr-FR")
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            print(f"Received: {data}")
            
            if data.get('event') == 'media':
                response_data = {
                    "event": "media",
                    "streamSid": data.get('streamSid'),
                    "media": {
                        "payload": data['media']['payload']
                    }
                }
                await websocket.send_json(response_data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
