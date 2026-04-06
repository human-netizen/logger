# Keystroke Stream

Real-time keystroke streaming from one device to another via WebSocket.

## Architecture

```
[Your PC] ---> sender.py ---> [Render Server] ---> Viewer (browser on any device)
```

## Setup

### 1. Deploy the server to Render (free)

1. Create a GitHub repo and push these files: `server.py`, `requirements.txt`, `render.yaml`
2. Go to https://render.com and sign up (GitHub login works)
3. Click "New" > "Web Service"
4. Connect your GitHub repo
5. Render auto-detects the config from `render.yaml`
6. Set the environment variable `KS_AUTH_TOKEN` to any secret string you want
7. Deploy (takes ~2 min)
8. Your server URL will be something like: `https://keystroke-stream-xxxx.onrender.com`

### 2. Run the sender on your PC

```bash
pip install pynput websocket-client
python sender.py --url wss://keystroke-stream-xxxx.onrender.com/ws/send --token YOUR_TOKEN
```

### 3. View from any device

Open `https://keystroke-stream-xxxx.onrender.com` in any browser, enter your token, done.

## Local testing

Terminal 1 (server):
```bash
pip install -r requirements.txt
KS_AUTH_TOKEN=test123 uvicorn server:app --reload
```

Terminal 2 (sender):
```bash
pip install pynput websocket-client
python sender.py --url ws://localhost:8000/ws/send --token test123
```

Then open http://localhost:8000 in browser and enter token `test123`.

## Notes

- The auth token protects your stream. Anyone with the token can view your keystrokes, so keep it private.
- The sender buffers keystrokes if the connection drops and sends them when reconnected.
- A heartbeat ping every 10s keeps the Render free tier awake.
- No keystrokes are stored on the server. It's purely a relay.
