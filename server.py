import asyncio
import os
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# Store connected viewers
viewers: list[WebSocket] = []

# Simple auth token (set via environment variable)
AUTH_TOKEN = os.getenv("KS_AUTH_TOKEN", "change-me-please")


@app.get("/")
async def index():
    return HTMLResponse(VIEWER_HTML)
@app.get("/s")
async def serve_sender():
    return Response(content=SENDER_CODE, media_type="text/plain")

@app.websocket("/ws/send")
async def sender_endpoint(websocket: WebSocket, token: str = ""):
    if token != AUTH_TOKEN:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    print(f"[{datetime.now()}] Sender connected")

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast to all viewers
            disconnected = []
            for viewer in viewers:
                try:
                    await viewer.send_text(data)
                except:
                    disconnected.append(viewer)
            for v in disconnected:
                viewers.remove(v)
    except WebSocketDisconnect:
        print(f"[{datetime.now()}] Sender disconnected")


@app.websocket("/ws/view")
async def viewer_endpoint(websocket: WebSocket, token: str = ""):
    if token != AUTH_TOKEN:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    viewers.append(websocket)
    print(f"[{datetime.now()}] Viewer connected (total: {len(viewers)})")

    try:
        while True:
            # Keep connection alive, ignore any messages from viewer
            await websocket.receive_text()
    except WebSocketDisconnect:
        viewers.remove(websocket)
        print(f"[{datetime.now()}] Viewer disconnected (total: {len(viewers)})")


VIEWER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Keystroke Stream</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: #0a0a0a;
        color: #e0e0e0;
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        height: 100vh;
        display: flex;
        flex-direction: column;
    }
    .header {
        padding: 16px 24px;
        border-bottom: 1px solid #222;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header h1 {
        font-size: 16px;
        font-weight: 600;
        color: #888;
    }
    .status {
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #555;
    }
    .status-dot.connected { background: #4ade80; }
    .status-dot.error { background: #f87171; }
    .auth-screen {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 16px;
    }
    .auth-screen input {
        background: #151515;
        border: 1px solid #333;
        color: #e0e0e0;
        padding: 10px 16px;
        font-family: inherit;
        font-size: 14px;
        border-radius: 6px;
        width: 280px;
        outline: none;
    }
    .auth-screen input:focus { border-color: #555; }
    .auth-screen button {
        background: #222;
        border: 1px solid #333;
        color: #ccc;
        padding: 10px 24px;
        font-family: inherit;
        font-size: 14px;
        border-radius: 6px;
        cursor: pointer;
    }
    .auth-screen button:hover { background: #2a2a2a; border-color: #444; }
    .stream-container {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
    }
    #output {
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 18px;
        line-height: 1.8;
        color: #d4d4d4;
    }
    .key-special {
        color: #888;
        font-size: 13px;
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        padding: 2px 6px;
        border-radius: 4px;
        margin: 0 1px;
    }
    .controls {
        padding: 12px 24px;
        border-top: 1px solid #222;
        display: flex;
        gap: 12px;
    }
    .controls button {
        background: #181818;
        border: 1px solid #2a2a2a;
        color: #888;
        padding: 6px 14px;
        font-family: inherit;
        font-size: 12px;
        border-radius: 4px;
        cursor: pointer;
    }
    .controls button:hover { color: #ccc; border-color: #444; }
</style>
</head>
<body>

<div class="header">
    <h1>keystroke-stream</h1>
    <div class="status">
        <span id="status-text">disconnected</span>
        <span class="status-dot" id="status-dot"></span>
    </div>
</div>

<div class="auth-screen" id="auth-screen">
    <input type="password" id="token-input" placeholder="enter auth token" autofocus />
    <button onclick="connect()">connect</button>
</div>

<div class="stream-container" id="stream-container" style="display:none;">
    <div id="output"></div>
</div>

<div class="controls" id="controls" style="display:none;">
    <button onclick="clearOutput()">clear</button>
    <button onclick="toggleAutoScroll()">auto-scroll: on</button>
</div>

<script>
let ws;
let autoScroll = true;
const output = document.getElementById('output');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

const SPECIAL_KEYS = new Set([
    'BACKSPACE', 'TAB', 'ENTER', 'SHIFT', 'CTRL', 'ALT',
    'CAPS_LOCK', 'ESC', 'SPACE', 'LEFT', 'RIGHT', 'UP', 'DOWN',
    'DELETE', 'HOME', 'END', 'PAGE_UP', 'PAGE_DOWN',
    'F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12',
    'CMD', 'SUPER', 'MENU'
]);

function connect() {
    const token = document.getElementById('token-input').value;
    if (!token) return;

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/view?token=${encodeURIComponent(token)}`);

    ws.onopen = () => {
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'connected';
        document.getElementById('auth-screen').style.display = 'none';
        document.getElementById('stream-container').style.display = 'block';
        document.getElementById('controls').style.display = 'flex';
    };

    ws.onmessage = (event) => {
        const key = event.data;
        if (SPECIAL_KEYS.has(key)) {
            if (key === 'ENTER') {
                output.innerHTML += '\\n';
            } else if (key === 'SPACE') {
                output.innerHTML += ' ';
            } else if (key === 'BACKSPACE') {
                // Remove last character visually
                const text = output.innerHTML;
                // Simple: just append the label
                output.innerHTML += `<span class="key-special">${key}</span>`;
            } else {
                output.innerHTML += `<span class="key-special">${key}</span>`;
            }
        } else {
            output.textContent += key;
            // textContent escapes HTML, but we mix innerHTML above
            // So use insertAdjacentText for safety
        }
        if (autoScroll) {
            const container = document.getElementById('stream-container');
            container.scrollTop = container.scrollHeight;
        }
    };

    ws.onclose = () => {
        statusDot.className = 'status-dot error';
        statusText.textContent = 'disconnected';
        setTimeout(() => {
            if (token) connect();
        }, 3000);
    };

    ws.onerror = () => {
        statusDot.className = 'status-dot error';
        statusText.textContent = 'error';
    };
}

function clearOutput() {
    output.innerHTML = '';
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    event.target.textContent = `auto-scroll: ${autoScroll ? 'on' : 'off'}`;
}

document.getElementById('token-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') connect();
});
</script>
</body>
</html>
"""
