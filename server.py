from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pyaudio
import json
import asyncio

app = FastAPI()
app.mount('/static', StaticFiles(directory='static', html=True), name='static')
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_speaker = None
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str, username: str):
        print("Server has connected to a student WebSocket")
        await websocket.accept()
        websocket.client_id = client_id
        websocket.username = username
        self.active_connections.append(websocket)

        if self.current_speaker:
            await websocket.send_json({
                "action": "deny",
                "speaker_id": self.current_speaker.client_id,
                "speaker_username": self.current_speaker.username
            })

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def set_speaker(self, websocket: WebSocket):
        async with self.lock:
            self.current_speaker = websocket
            await self.broadcast({"action": "speaker", "speaker_id": websocket.client_id})

    async def stop_speaking(self, websocket: WebSocket):
        async with self.lock:
            if websocket == self.current_speaker:
                self.current_speaker = None
                await self.broadcast({"action": "speaker", "speaker_id": None})

    async def broadcast(self, message: str | dict):
        for connection in self.active_connections:
            try:
                if isinstance(message, dict):
                    await connection.send_json(message)
                else:
                    await connection.send_text(message)
            except WebSocketDisconnect:
                continue


async def receive_action(websocket: WebSocket):
    try:
        while True:
            recv = await websocket.receive()
            if "text" in recv:
                data = json.loads(recv["text"])
                print(f"Received action: {data['action']}")
                return data["action"]
    except WebSocketDisconnect:
        print("WebSocket disconnected while receiving action")
        return None


async def send_start(websocket: WebSocket):
    await websocket.send_json({"action": "start"})


manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # access stored cookie for username
    username = websocket.cookies.get("audiochat-username")
    print(f"In WebSocket for client {client_id}, Username: {username}")
    await manager.connect(websocket, client_id, username)
    stream = None

    try:
        action = await receive_action(websocket)
        
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, output=True, frames_per_buffer=1024)
        
        if action == "start":
            if manager.current_speaker is None:
                await manager.set_speaker(websocket)
                await send_start(websocket)
                print(f"Recording started for client {client_id}")

                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, output=True, frames_per_buffer=1024)
            
                while True:
                    print(f"Speaking: {client_id}, {username}")
                    try:
                        message = await websocket.receive()
                        
                        if "bytes" in message and websocket == manager.current_speaker:
                            async with manager.lock:
                                stream.write(message["bytes"])
                        elif "text" in message:
                            data = json.loads(message["text"])
                            print(f"Received text message: {data}")
                            if data.get("action") == "stop":
                                break
                    except RuntimeError as e:
                        if str(e) == 'Cannot call "receive" once a disconnect message has been received.':
                            print("Client disconnected before receiving data")
                            break
                        raise e
            else:
                await websocket.send_json({"action": "deny", "speaker_id": manager.current_speaker.client_id, "speaker_username": manager.current_speaker.username})

        await manager.stop_speaking(websocket)

    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected unexpectedly")
    
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
            p.terminate()
        await manager.stop_speaking(websocket)
        await manager.disconnect(websocket)
        print("Connection closed and resources released")
