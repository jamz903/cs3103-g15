from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Audio Chat</title>
    </head>
    <body>
        <h1>WebSocket Audio Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <button id="talkBtn" onmousedown="startRecording()" onmouseup="stopRecording()">Push to Talk</button>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Math.floor(Math.random() * 100)
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.binaryType = 'arraybuffer';  // To handle binary audio data
            
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };

            var mediaRecorder;
            var audioChunks = [];
            var stream;

            function startRecording() {
                // Request permission to speak by sending a "start" message
                ws.send(JSON.stringify({ action: "start" }));

                // Check if permission was granted (server responds with "start" or "deny")
                ws.onmessage = function(event) {
                    var response = JSON.parse(event.data);
                    if (response.action === "start") {
                        navigator.mediaDevices.getUserMedia({ audio: true })
                            .then(function(mediaStream) {
                                stream = mediaStream;  // Save the stream so it can be stopped later
                                mediaRecorder = new MediaRecorder(mediaStream);
                                mediaRecorder.start();

                                mediaRecorder.ondataavailable = function(event) {
                                    if (event.data.size > 0) {
                                        // Send audio data chunk as binary over WebSocket
                                        ws.send(event.data);
                                    }
                                };
                            })
                            .catch(function(error) {
                                console.error('Error accessing microphone:', error);
                            });
                    } else if (response.action === "deny") {
                        alert("Someone else is speaking. Wait for your turn.");
                    }
                };
            }

            function stopRecording() {
                if (mediaRecorder && mediaRecorder.state !== "inactive") {
                    mediaRecorder.stop();  // Stop the MediaRecorder
                }

                if (stream) {
                    stream.getTracks().forEach(track => track.stop());  // Stop the audio stream
                }

                ws.send(JSON.stringify({ action: "stop" }));
            }
        </script>
    </body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_speaker = None  # Track the current speaker

    async def connect(self, websocket: WebSocket):
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


manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "start":
                # Check if the current user can start speaking
                if await manager.start_speaking(websocket):
                    await websocket.send_json({"action": "start"})  # Allow speaking
                else:
                    await websocket.send_json({"action": "deny"})  # Deny speaking

            elif action == "stop":
                # Stop speaking and clear the current speaker
                await manager.stop_speaking(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} disconnected")
