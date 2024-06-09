import os
import json
import asyncio
import websockets
import flask
from flask import Flask, request

app = Flask(__name__)

# Default configuration
volume = -60
amplifier_ip = os.getenv('AMPLIFIER_IP', '192.168.1.91')
websocket_url = f"ws://{amplifier_ip}/ws"

async def send_websocket_message(message):
    async with websockets.connect(websocket_url) as websocket:
        await websocket.send(message)

@app.route('/volume/<action>', methods=['GET'])
def volume_action(action):
    global volume

    if action == 'plus':
        volume += 1
        print("Volume plus")
    elif action == 'minus':
        volume -= 1
        print("Volume minus")
    elif action == 'mute':
        message = json.dumps({"mute": True})
        asyncio.run(send_websocket_message(message))
    elif action == 'dim':
        message = b'\x00\x00\x00\x23\x03\x00\x00\x00\x12/optimizer/volume/{"dim":true}'
        asyncio.run(send_websocket_message(message))
    elif action == 'undim':
        message = b'\x00\x00\x00\x24\x03\x00\x00\x00\x12/optimizer/volume/{"dim":false}'
        asyncio.run(send_websocket_message(message))
    else:
        return "Invalid action", 400

    volume_message = f'\x00\x00\x00\x35\x03\x00\x00\x00\x12/optimizer/volume/{{"volume":{volume:.15f}}}'.encode()
    print(volume_message)
    asyncio.run(send_websocket_message(volume_message))
    print("Volume...")
    return f"Volume action {action} executed. Current volume: {volume}", 200

# TODO
@app.route('/source/<source>', methods=['GET'])
def change_source(source):
    valid_sources = ['hdmi1', 'hdmi2', 'hdmi3', 'hdmi4']

    if source not in valid_sources:
        return "Invalid source", 400

    message = json.dumps({"source": source})
    asyncio.run(send_websocket_message(message))

    return f"Source changed to {source}", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
