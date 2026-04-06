"""
Keystroke Sender (cross-platform)
Linux: uses evdev (requires sudo)
Windows: uses pynput

Usage:
    pip install websocket-client evdev   (Linux)
    pip install websocket-client pynput  (Windows)

    sudo python3 sender.py --url wss://your-app.onrender.com/ws/send --token your-token   (Linux)
    python sender.py --url wss://your-app.onrender.com/ws/send --token your-token          (Windows)

    --list   Show available input devices (Linux only)
    --device /dev/input/eventX   Specify keyboard device (Linux only)
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


# ── WebSocket sender (shared) ──────────────────────────────────────────────

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

    def start_connection(self):
        conn_thread = threading.Thread(target=self.connect, daemon=True)
        conn_thread.start()


# ── Linux backend (evdev) ──────────────────────────────────────────────────

def run_linux(sender: KeystrokeSender, device_path: str = None):
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


# ── Windows backend (pynput) ──────────────────────────────────────────────

def run_windows(sender: KeystrokeSender):
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


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Keystroke Sender (cross-platform)")
    parser.add_argument("--url", help="WebSocket server URL")
    parser.add_argument("--token", help="Auth token")
    parser.add_argument("--device", help="Input device path, Linux only (e.g., /dev/input/event3)")
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
        print("Supported: Linux, Windows")
        sys.exit(1)


if __name__ == "__main__":
    main()
