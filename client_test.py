import asyncio
import websockets
import json

async def listen():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected to server. Listening for transcriptions...\n")
        try:
            while True:
                message = await websocket.recv()
                try:
                    data = json.loads(message)
                    if data.get("type") == "interim":
                        print(f"[INTERIM {data.get('timestamp')}] [{data.get('stream_id','')}] ({data.get('speaker')}) {data.get('text')}")
                    elif data.get("type") == "transcript":
                        print(f"[{data.get('timestamp')}] [{data.get('stream_id','')}] ({data.get('speaker')}) {data.get('text')}")
                    elif data.get("type") == "summary":
                        print(f"[SUMMARY {data.get('timestamp')}] {data.get('text')}")
                    else:
                        print(message)
                except Exception:
                    print(message)
        except websockets.ConnectionClosed:
            print("Connection closed.")

asyncio.run(listen())
