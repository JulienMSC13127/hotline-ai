import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/audio/realtime"

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
    response.say("Déconnexion", language="fr-FR")
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with websockets.connect(
        OPENAI_REALTIME_URL,
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    ) as openai_ws:
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get('event') == 'media':
                    await openai_ws.send(json.dumps({
                        "audio": data['media']['payload'],
                        "model": "whisper-1"
                    }))
                    
                    response = await openai_ws.recv()
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": data.get('streamSid'),
                        "media": {"payload": response}
                    })
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
