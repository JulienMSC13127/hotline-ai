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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
    openai_ws = await websockets.connect(
        'wss://api.openai.com/v1/realtime/speech',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    )

    try:
        async def forward_to_openai():
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                if data.get('event') == 'media':
                    await openai_ws.send(json.dumps({
                        "type": "audio",
                        "data": data['media']['payload']
                    }))

        async def forward_to_twilio():
            while True:
                response = await openai_ws.recv()
                response_data = json.loads(response)
                if response_data.get('type') == 'audio':
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": response_data.get('streamSid'),
                        "media": {"payload": response_data['data']}
                    })

        await asyncio.gather(forward_to_openai(), forward_to_twilio())
    except Exception as e:
        print(f"Error: {e}")
        await openai_ws.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
