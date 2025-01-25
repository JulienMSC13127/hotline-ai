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
    connect = Connect()
    connect.stream(url=f'wss://{request.headers["host"]}/media')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    openai_ws = await websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    )

    try:
        # Send initial configuration
        await openai_ws.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "Tu es un assistant AI sympathique qui parle français."
            }
        }))

        while True:
            data = await websocket.receive_json()
            print(f"Received from Twilio: {data}")
            
            if data.get('event') == 'media':
                await openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data['media']['payload']
                }))
                
                response = await openai_ws.recv()
                response_data = json.loads(response)
                print(f"Received from OpenAI: {response_data}")
                
                if response_data.get('type') == 'response.audio.delta':
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": data['streamSid'],
                        "media": {
                            "payload": response_data['delta']
                        }
                    })
    except Exception as e:
        print(f"Error: {e}")
        await openai_ws.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
