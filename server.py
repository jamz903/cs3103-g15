from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import io
from pydub import AudioSegment
import pyaudio
import json
from time import sleep

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_speaker = None  # Track the current speaker

    async def connect(self, websocket: WebSocket):
        print("Server has connected to a student WebSocket")
        await websocket.accept()
        
        
        if self.current_speaker is None:
            self.current_speaker = websocket
            return True
            # await websocket.send_text("You are the current speaker")
            # self.active_connections.append(websocket)
        else:
            sleep(1) # Might be needed to wait for the client to receive the message as takes a while for socket to form
            print("Another student is currently speaking")
            await websocket.send_json({"action": "deny"})
            websocket.close()
            return False

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket == self.current_speaker:
            self.current_speaker = None  # Clear the speaker if they disconnect

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
    recv = await websocket.receive()
    
    ## Handles leftover in the socket and cleans up the remaining info in the socket
    while "text" not in recv:
        print("Trying again")
        recv = await websocket.receive()
    print(recv)
    # data = await websocket.receive()
    # data = await websocket.receive()
    if "text" in recv:
        data = json.loads(recv["text"])
        print(data)
        
        action = data["action"]
        print(f"Received action: {action}")
        return action


async def send_start(websocket: WebSocket):
    await websocket.send_json({"action": "start"})


async def send_deny(websocket: WebSocket):
    await websocket.send_json({"action": "deny"})


manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    print(f"In WebSocket for client {client_id}")
    check = await manager.connect(websocket)
    print("check if connected", check)
    if not check:
        print("Connection denied")
        return
    
    
    action = await receive_action(websocket)
    
    # Set up PyAudio for real-time playback
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, output=True)

    try:
        if action == "start":
            await send_start(websocket)
            while True:
                print(f"Currently speaking: {client_id}")
                audio_bytes = await websocket.receive_bytes()
                if audio_bytes:
                    stream.write(audio_bytes)  # Play the received audio in real-time
                else:
                    break
        elif action == "stop":
            print("Received stop action")

    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected unexpectedly")
    
    finally:
        # Cleanup resources
        stream.stop_stream()
        stream.close()
        p.terminate()
        await manager.stop_speaking(websocket)
        manager.disconnect(websocket)
        print("Connection closed and resources released")
