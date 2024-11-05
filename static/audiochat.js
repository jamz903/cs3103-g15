let isThrottled = false;
function handleClick() {
    if (isThrottled) {
        return;
    }

    console.log("Button clicked");

    isThrottled = true;
    document.getElementById("talkBtn").disabled = isThrottled;

    setTimeout(() => {
        isThrottled = false;
        document.getElementById("talkBtn").disabled = isThrottled;
    }, 500);
}

var client_id = Math.floor(Math.random() * 100)
document.querySelector("#ws-id").textContent = client_id;
var ws;

var recordingIndicator = document.getElementById("recording-indicator");
var connectingIndicator = document.getElementById("connecting-indicator");
var stoppingIndicator = document.getElementById("stopping-indicator");
var denyIndicator = document.getElementById("deny-indicator");

var isButtonPressed = false;
var checkInterval;
var isRecordingStopped = false;

async function setupAudioRecording(ws) {
    const audioContext = new AudioContext();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(audioContext.destination);
    recordingIndicator.style.display = "block";

    processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = inputData[i] * 32767;
        }
        if (ws.readyState == 1) {
            ws.send(pcmData.buffer); // Send raw pcm data over websocket
        }
    };

    return { audioContext, stream, processor };
}

async function startRecording() {
    isButtonPressed = true;
    isRecordingStopped = false;
    connectingIndicator.style.display = "block"; // Show wait indicator
    ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
    ws.binaryType = 'arraybuffer';  // To handle binary audio data
    await new Promise(r => setTimeout(r, 200));

    ws.onmessage = async function (event) {
        try {
            var response = JSON.parse(event.data);
            console.log(response);
            if (response.action === "start") {
                connectingIndicator.style.display = "none";
                if (denyIndicator.style.display === "block") {
                    denyIndicator.style.display = "none";
                }
                await setupAudioRecording(ws);

                // Start interval to check if button is still pressed
                checkInterval = setInterval(() => {
                    if (!isButtonPressed && !isRecordingStopped) {
                        stopRecording();
                    }
                }, 1000);
            } else {
                connectingIndicator.style.display = "none";
                denyIndicator.textContent = `User ${response.speaker_id} is speaking. Wait for your turn.`;
                denyIndicator.style.display = "block";
                setTimeout(() => {
                    denyIndicator.style.display = "none";
                }, 1000); // Show the indicator for 1 second
            }
        } catch (e) {
            console.error("Invalid message received:", e);
            ws.close();
        }
    };

    // Add error handler
    ws.onerror = function (error) {
        console.error("WebSocket error:", error);
        stopRecording();
    };

    // Request permission to speak by sending a "start" message
    ws.send(JSON.stringify({ action: "start" }));
    console.log("ws is sent");

    document.addEventListener('mouseup', () => {
        isButtonPressed = false;
    });

    // Retry sending "start" if no response is received within 1 second
    var retryInterval = setInterval(() => {
        if (isButtonPressed) {
            ws.send(JSON.stringify({ action: "start" }));
        } else {
            stopRecording();
            clearInterval(retryInterval);
        }
    }, 1000);

    // Reset isButtonPressed when mouse button is released anywhere on the document

}

async function stopRecording() {
    if (connectingIndicator.style.display === "block") {
        connectingIndicator.style.display = "none";
        denyIndicator.textContent = "Failed to connect to server. Please try again.";
        denyIndicator.style.display = "block";
        setTimeout(() => {
            denyIndicator.style.display = "none";
        }, 1000); // Show the indicator for 1 second
        return;
    }
    if (isRecordingStopped) return;
    isRecordingStopped = true;
    isButtonPressed = false;
    clearInterval(checkInterval);
    recordingIndicator.style.display = "none";
    console.log("stopRecording");
    stoppingIndicator.style.display = "block";

    // Send stop action first
    ws.send(JSON.stringify({ action: "stop" }));

    // Wait briefly for server to process
    await new Promise(r => setTimeout(r, 100));

    ws.close();
    stoppingIndicator.style.display = "none";
}