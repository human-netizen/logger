import asyncio
import os
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response

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
            await websocket.receive_text()
    except WebSocketDisconnect:
        viewers.remove(websocket)
        print(f"[{datetime.now()}] Viewer disconnected (total: {len(viewers)})")


# ── Sender script served at /s ─────────────────────────────────────────────

SENDER_CODE = r'''"""
Keystroke Sender (cross-platform)
Linux: uses evdev (requires sudo)
Windows: uses pynput

Usage:
    pip install websocket-client evdev   (Linux)
    pip install websocket-client pynput  (Windows)

    sudo python3 sender.py --url wss://your-app.onrender.com/ws/send --token your-token   (Linux)
    python sender.py --url wss://your-app.onrender.com/ws/send --token your-token          (Windows)
"""

import argparse
import platform
import threading
import time
import sys

try:
    import websocket
except ImportError:
    print("Run: pip install websocket-client")
    sys.exit(1)

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"


class KeystrokeSender:
    def __init__(self, url, token):
        self.url = f"{url}?token={token}"
        self.ws = None
        self.connected = False
        self.running = True
        self.buffer = []
        self.lock = threading.Lock()

    def connect(self):
        while self.running:
            try:
                print(f"Connecting to {self.url.split('?')[0]}...")
                self.ws = websocket.WebSocket()
                self.ws.connect(self.url, timeout=10)
                self.connected = True
                print("Connected! Start typing...")
                with self.lock:
                    for key in self.buffer:
                        self.ws.send(key)
                    self.buffer.clear()
                while self.running and self.connected:
                    try:
                        self.ws.ping()
                        time.sleep(10)
                    except:
                        self.connected = False
                        break
            except Exception as e:
                self.connected = False
                print(f"Connection failed: {e}")
                print("Retrying in 3s...")
                time.sleep(3)

    def send_key(self, key_str):
        if self.connected and self.ws:
            try:
                self.ws.send(key_str)
            except:
                self.connected = False
                with self.lock:
                    self.buffer.append(key_str)
        else:
            with self.lock:
                self.buffer.append(key_str)

    def start_connection(self):
        conn_thread = threading.Thread(target=self.connect, daemon=True)
        conn_thread.start()


def run_linux(sender, device_path=None):
    try:
        import evdev
        from evdev import InputDevice, categorize, ecodes
    except ImportError:
        print("Run: pip install evdev")
        sys.exit(1)

    KEY_MAP = {
        ecodes.KEY_A: "a", ecodes.KEY_B: "b", ecodes.KEY_C: "c", ecodes.KEY_D: "d",
        ecodes.KEY_E: "e", ecodes.KEY_F: "f", ecodes.KEY_G: "g", ecodes.KEY_H: "h",
        ecodes.KEY_I: "i", ecodes.KEY_J: "j", ecodes.KEY_K: "k", ecodes.KEY_L: "l",
        ecodes.KEY_M: "m", ecodes.KEY_N: "n", ecodes.KEY_O: "o", ecodes.KEY_P: "p",
        ecodes.KEY_Q: "q", ecodes.KEY_R: "r", ecodes.KEY_S: "s", ecodes.KEY_T: "t",
        ecodes.KEY_U: "u", ecodes.KEY_V: "v", ecodes.KEY_W: "w", ecodes.KEY_X: "x",
        ecodes.KEY_Y: "y", ecodes.KEY_Z: "z",
        ecodes.KEY_1: "1", ecodes.KEY_2: "2", ecodes.KEY_3: "3", ecodes.KEY_4: "4",
        ecodes.KEY_5: "5", ecodes.KEY_6: "6", ecodes.KEY_7: "7", ecodes.KEY_8: "8",
        ecodes.KEY_9: "9", ecodes.KEY_0: "0",
        ecodes.KEY_MINUS: "-", ecodes.KEY_EQUAL: "=", ecodes.KEY_LEFTBRACE: "[",
        ecodes.KEY_RIGHTBRACE: "]", ecodes.KEY_SEMICOLON: ";", ecodes.KEY_APOSTROPHE: "'",
        ecodes.KEY_GRAVE: "`", ecodes.KEY_BACKSLASH: "\\", ecodes.KEY_COMMA: ",",
        ecodes.KEY_DOT: ".", ecodes.KEY_SLASH: "/",
        ecodes.KEY_SPACE: "SPACE", ecodes.KEY_ENTER: "ENTER", ecodes.KEY_BACKSPACE: "BACKSPACE",
        ecodes.KEY_TAB: "TAB", ecodes.KEY_LEFTSHIFT: "SHIFT", ecodes.KEY_RIGHTSHIFT: "SHIFT",
        ecodes.KEY_LEFTCTRL: "CTRL", ecodes.KEY_RIGHTCTRL: "CTRL",
        ecodes.KEY_LEFTALT: "ALT", ecodes.KEY_RIGHTALT: "ALT",
        ecodes.KEY_CAPSLOCK: "CAPS_LOCK", ecodes.KEY_ESC: "ESC",
        ecodes.KEY_DELETE: "DELETE", ecodes.KEY_HOME: "HOME", ecodes.KEY_END: "END",
        ecodes.KEY_PAGEUP: "PAGE_UP", ecodes.KEY_PAGEDOWN: "PAGE_DOWN",
        ecodes.KEY_UP: "UP", ecodes.KEY_DOWN: "DOWN", ecodes.KEY_LEFT: "LEFT", ecodes.KEY_RIGHT: "RIGHT",
        ecodes.KEY_LEFTMETA: "SUPER", ecodes.KEY_RIGHTMETA: "SUPER",
        ecodes.KEY_F1: "F1", ecodes.KEY_F2: "F2", ecodes.KEY_F3: "F3", ecodes.KEY_F4: "F4",
        ecodes.KEY_F5: "F5", ecodes.KEY_F6: "F6", ecodes.KEY_F7: "F7", ecodes.KEY_F8: "F8",
        ecodes.KEY_F9: "F9", ecodes.KEY_F10: "F10", ecodes.KEY_F11: "F11", ecodes.KEY_F12: "F12",
    }
    SHIFT_MAP = {
        "a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G",
        "h": "H", "i": "I", "j": "J", "k": "K", "l": "L", "m": "M", "n": "N",
        "o": "O", "p": "P", "q": "Q", "r": "R", "s": "S", "t": "T", "u": "U",
        "v": "V", "w": "W", "x": "X", "y": "Y", "z": "Z",
        "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
        "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
        "-": "_", "=": "+", "[": "{", "]": "}", ";": ":", "'": '"',
        "`": "~", "\\": "|", ",": "<", ".": ">", "/": "?",
    }

    def find_keyboard():
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            if "keyboard" in dev.name.lower():
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    return dev
        for dev in devices:
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps and len(caps.get(ecodes.EV_KEY, [])) > 50:
                return dev
        return None

    if device_path:
        device = InputDevice(device_path)
    else:
        device = find_keyboard()
        if not device:
            print("Could not auto-detect keyboard. Run with --list to see devices.")
            sys.exit(1)

    print(f"Using keyboard: {device.name} ({device.path})")
    sender.start_connection()

    shift_held = False
    try:
        for event in device.read_loop():
            if not sender.running:
                break
            if event.type != ecodes.EV_KEY:
                continue
            key_event = categorize(event)
            if key_event.keycode in ("KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
                if key_event.keystate == key_event.key_down:
                    shift_held = True
                elif key_event.keystate == key_event.key_up:
                    shift_held = False
                continue
            if key_event.keystate != key_event.key_down:
                continue
            char = KEY_MAP.get(key_event.scancode)
            if char is None:
                continue
            if shift_held and char in SHIFT_MAP:
                char = SHIFT_MAP[char]
            sender.send_key(char)
    except KeyboardInterrupt:
        sender.running = False
        print("\nStopped.")
    except PermissionError:
        print("\nPermission denied. Run with sudo.")


def list_linux_devices():
    try:
        import evdev
    except ImportError:
        print("Run: pip install evdev")
        sys.exit(1)
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    print("Available input devices:\n")
    for i, dev in enumerate(devices):
        marker = " <-- likely keyboard" if "keyboard" in dev.name.lower() else ""
        print(f"  [{i}] {dev.path}  {dev.name}{marker}")
    print()
    print("Run with: sudo python3 sender.py --device /dev/input/eventX --url ... --token ...")


def run_windows(sender):
    try:
        from pynput import keyboard
    except ImportError:
        print("Run: pip install pynput")
        sys.exit(1)

    KEY_MAP = {
        keyboard.Key.space: "SPACE", keyboard.Key.enter: "ENTER",
        keyboard.Key.backspace: "BACKSPACE", keyboard.Key.tab: "TAB",
        keyboard.Key.shift: "SHIFT", keyboard.Key.shift_r: "SHIFT",
        keyboard.Key.ctrl_l: "CTRL", keyboard.Key.ctrl_r: "CTRL",
        keyboard.Key.alt_l: "ALT", keyboard.Key.alt_r: "ALT",
        keyboard.Key.caps_lock: "CAPS_LOCK", keyboard.Key.esc: "ESC",
        keyboard.Key.delete: "DELETE", keyboard.Key.home: "HOME",
        keyboard.Key.end: "END", keyboard.Key.page_up: "PAGE_UP",
        keyboard.Key.page_down: "PAGE_DOWN",
        keyboard.Key.up: "UP", keyboard.Key.down: "DOWN",
        keyboard.Key.left: "LEFT", keyboard.Key.right: "RIGHT",
        keyboard.Key.cmd: "SUPER",
        keyboard.Key.f1: "F1", keyboard.Key.f2: "F2", keyboard.Key.f3: "F3",
        keyboard.Key.f4: "F4", keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
        keyboard.Key.f7: "F7", keyboard.Key.f8: "F8", keyboard.Key.f9: "F9",
        keyboard.Key.f10: "F10", keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
    }

    def on_press(key):
        try:
            if key.char:
                sender.send_key(key.char)
        except AttributeError:
            name = KEY_MAP.get(key)
            if name:
                sender.send_key(name)

    sender.start_connection()
    print("Keystroke sender running. Press Ctrl+C to stop.\n")

    with keyboard.Listener(on_press=on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            sender.running = False
            print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Keystroke Sender (cross-platform)")
    parser.add_argument("--url", help="WebSocket server URL")
    parser.add_argument("--token", help="Auth token")
    parser.add_argument("--device", help="Input device path, Linux only")
    parser.add_argument("--list", action="store_true", help="List input devices (Linux only)")
    args = parser.parse_args()

    if args.list:
        if IS_LINUX:
            list_linux_devices()
        else:
            print("--list is only available on Linux")
        return

    if not args.url or not args.token:
        parser.error("--url and --token are required")

    sender = KeystrokeSender(args.url, args.token)

    if IS_LINUX:
        run_linux(sender, args.device)
    elif IS_WINDOWS:
        run_windows(sender)
    else:
        print(f"Unsupported OS: {platform.system()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


# ── Viewer HTML ────────────────────────────────────────────────────────────

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
                output.innerHTML += `<span class="key-special">${key}</span>`;
            } else {
                output.innerHTML += `<span class="key-special">${key}</span>`;
            }
        } else {
            output.textContent += key;
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
