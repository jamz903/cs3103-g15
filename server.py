from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import io
from pydub import AudioSegment
import pyaudio
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_speaker = None  # Track the current speaker

    async def connect(self, websocket: WebSocket):
        print("Server has connected to a student WebSocket")
        await websocket.accept()
        self.active_connections.append(websocket)

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


async def receive_audio(websocket: WebSocket):
    data = await websocket.receive()
    
    if "bytes" in data:
        # Process binary audio data
        audio_bytes = data["bytes"]
        print(f"Received audio_bytes of length {len(audio_bytes)}")
        return audio_bytes
    elif "text" in data:
        # Skip JSON messages
        json_message = data["text"]
        print(f"Received JSON message: {json_message}")
        return None
    else:
        print("Unknown data format received.")
        return None


async def save_audio_to_file(audio_data, filename="output.wav"):
    try:
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm", codec="opus")
        audio_segment.export(filename, format="wav")  # Save as WAV
        print(f"Audio file saved as {filename}")
    except Exception as e:
        print(f"Error decoding or saving audio: {e}")


manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    print(f"In WebSocket for client {client_id}")
    await manager.connect(websocket)
    
    action = await receive_action(websocket)
    
    # Set up PyAudio for real-time playback
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, output=True)

    try:
        if action == "start":
            await send_start(websocket)
            while True:
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
