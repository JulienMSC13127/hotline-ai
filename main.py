import os
import json
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Connect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok"}

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
    print("WebSocket connected")
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
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
