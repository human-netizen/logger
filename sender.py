"""
Keystroke Sender
Captures keystrokes and streams them to the server via WebSocket.

Usage:
    pip install pynput websocket-client
    python sender.py --url wss://your-app.onrender.com/ws/send --token your-secret-token

For local testing:
    python sender.py --url ws://localhost:8000/ws/send --token change-me-please
"""

import argparse
import threading
import time
import sys
from pynput import keyboard

try:
    import websocket
except ImportError:
    print("Run: pip install websocket-client")
    sys.exit(1)


class KeystrokeSender:
    def __init__(self, url: str, token: str):
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

                # Send buffered keys
                with self.lock:
                    for key in self.buffer:
                        self.ws.send(key)
                    self.buffer.clear()

                # Keep alive with heartbeat
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

    def send_key(self, key_str: str):
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

    def on_press(self, key):
        try:
            # Regular character key
            key_str = key.char
            if key_str:
                self.send_key(key_str)
        except AttributeError:
            # Special key
            key_map = {
                keyboard.Key.space: "SPACE",
                keyboard.Key.enter: "ENTER",
                keyboard.Key.backspace: "BACKSPACE",
                keyboard.Key.tab: "TAB",
                keyboard.Key.shift: "SHIFT",
                keyboard.Key.shift_r: "SHIFT",
                keyboard.Key.ctrl_l: "CTRL",
                keyboard.Key.ctrl_r: "CTRL",
                keyboard.Key.alt_l: "ALT",
                keyboard.Key.alt_r: "ALT",
                keyboard.Key.caps_lock: "CAPS_LOCK",
                keyboard.Key.esc: "ESC",
                keyboard.Key.delete: "DELETE",
                keyboard.Key.home: "HOME",
                keyboard.Key.end: "END",
                keyboard.Key.page_up: "PAGE_UP",
                keyboard.Key.page_down: "PAGE_DOWN",
                keyboard.Key.up: "UP",
                keyboard.Key.down: "DOWN",
                keyboard.Key.left: "LEFT",
                keyboard.Key.right: "RIGHT",
                keyboard.Key.cmd: "SUPER",
                keyboard.Key.f1: "F1",
                keyboard.Key.f2: "F2",
                keyboard.Key.f3: "F3",
                keyboard.Key.f4: "F4",
                keyboard.Key.f5: "F5",
                keyboard.Key.f6: "F6",
                keyboard.Key.f7: "F7",
                keyboard.Key.f8: "F8",
                keyboard.Key.f9: "F9",
                keyboard.Key.f10: "F10",
                keyboard.Key.f11: "F11",
                keyboard.Key.f12: "F12",
            }
            name = key_map.get(key, None)
            if name:
                self.send_key(name)

    def start(self):
        # Start WebSocket connection in background thread
        conn_thread = threading.Thread(target=self.connect, daemon=True)
        conn_thread.start()

        # Start keyboard listener (blocks main thread)
        print("Keystroke sender running. Press Ctrl+C to stop.")
        with keyboard.Listener(on_press=self.on_press) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                self.running = False
                print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Keystroke Sender")
    parser.add_argument("--url", required=True, help="WebSocket server URL (e.g., wss://your-app.onrender.com/ws/send)")
    parser.add_argument("--token", required=True, help="Auth token")
    args = parser.parse_args()

    sender = KeystrokeSender(args.url, args.token)
    sender.start()


if __name__ == "__main__":
    main()
