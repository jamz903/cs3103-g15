from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import pyaudio
import websockets
import asyncio


app = FastAPI()

# Initialize PyAudio for real-time audio playback
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_speaker = None  # Track the current speaker
        self.prof_websocket = None  # Track the professor's WebSocket connection

    async def connect(self, websocket: WebSocket):
        print("Server has connected to a student WebSocket")
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket == self.current_speaker:
            self.current_speaker = None  # Clear the speaker if they disconnect

    async def connect_prof(self, websocket: WebSocket):
        print("Server has connected to the professor WebSocket")
        await websocket.accept()
        self.prof_websocket = websocket  # Assign the WebSocket connection for the professor

    async def disconnect_prof(self):
        print("Professor WebSocket disconnected")
        self.prof_websocket = None

    async def start_speaking(self, websocket: WebSocket):
        if self.current_speaker is None:
            self.current_speaker = websocket
            return True
        return False

    async def stop_speaking(self, websocket: WebSocket):
        if websocket == self.current_speaker:
            self.current_speaker = None

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


async def receive_action(websocket: WebSocket):
    data = await websocket.receive_json()
    action = data.get("action")
    return action


async def send_start(websocket: WebSocket):
    await websocket.send_json({"action": "start"})


async def send_deny(websocket: WebSocket):
    await websocket.send_json({"action": "deny"})
        
async def receive_audio(websocket: WebSocket):

    data = await websocket.receive()
    print(f"audio_bytes is {data}")
    
    if "bytes" in data :
        audio_bytes = data["bytes"]
        print(f"audio_bytes is {audio_bytes}")
        return audio_bytes
    else:
        print(f"audio_bytes is not bytes")
        return None

async def forward_audio(websocket: WebSocket, audio_bytes):
    if manager.prof_websocket:
        await manager.prof_websocket.send_bytes(audio_bytes)
    # Send the audio bytes to the professor's WebSocke
    if audio_bytes:
        stream.write(audio_bytes)



manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.get("/prof")
async def get_prof():
    return FileResponse("prof.html")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # connecting prof
    if client_id == "prof":
        await manager.connect_prof(websocket)
        try:
            while True:
                # Keep the connection open for the professor
                print("Professor WebSocket connected")
                await websocket.receive_bytes()
                 
        except WebSocketDisconnect:
            await manager.disconnect_prof()
            print("Professor WebSocket disconnected")
        return
    else:
        ## connecting student
        await manager.connect(websocket)
        
        
        action = await receive_action(websocket)
        
        if action == "start":
            await send_start(websocket) 
            while True:
                audio_bytes = await receive_audio(websocket)
                print("received bytes, forwarding to prof")
                if audio_bytes:
                    await forward_audio(websocket, audio_bytes)
                else:
                    print("audio_bytes is None")
                    break
                
            
        elif action == "stop":
            # send_deny()
            print("received stop")
        
# @app.websocket("/ws/prof")
# async def websocket_prof_endpoint(websocket: WebSocket):
#     await manager.connect_prof(websocket)
#     try:
#         while True:
#             # Keep the connection open for the professor
#             await websocket.receive_text()  
#     except WebSocketDisconnect:
#         await manager.disconnect_prof()
#         print("Professor WebSocket disconnected")
