from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import io
from pydub import AudioSegment
import pyaudio

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
    data = await websocket.receive_json()
    action = data.get("action")
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
    # Connect student
    await manager.connect(websocket)
    
    action = await receive_action(websocket)
    # pd = AudioSegment.from_file("output.wav")
    
    # encoding	pcm_s16le
    # format	s16
    # number_of_channel	1 ch (mono)
    # sample_rate	48,000 Hz
    # file_size	478,124 bytes
    # duration	5 s
    p = pyaudio.PyAudio()
    chunk = 1024
    # print(pd.frame_rate)
    # print(pd.sample_width)
    # print(pd.channels)
    stream = p.open(format =
                        p.get_format_from_width(2),
                        channels = 1,
                        rate = 48000,
                        output = True)


    if action == "start":
        await send_start(websocket)
        # audio_buffer = io.BytesIO()  # Use BytesIO to collect audio data in memory
        while True:
            audio_bytes = await receive_audio(websocket)
            if audio_bytes:
                # audio_buffer.write(audio_bytes)  # Write each chunk to buffer
                # AudioSegment
                stream.write(audio_bytes)
            else:
                break
        
        
    elif action == "stop":
        print("received stop")
