import os
import json
import asyncio
import websockets
import flask
from flask import Flask, request

app = Flask(__name__)

# Default configuration
volume = -60
muted = False
dimmed = False
amplifier_ip = os.getenv('AMPLIFIER_IP', '192.168.1.91')
websocket_url = f"ws://{amplifier_ip}/ws"

async def send_websocket_message(message, reply=False):
    print("Sending this message:")
    print(message)
    async with websockets.connect(websocket_url) as websocket:
        await websocket.send(message)
        print('Message sent')

        # if reply:
        #     try:
        #         rep = await websocket.recv()
        #         print(f"Received reply: {rep}")
        #     except websockets.exceptions.ConnectionClosedError as e:
        #         print(f"Connection closed error: {e}")
        #     except asyncio.TimeoutError:
        #         print("Timeout error: No reply received")

def build_message(message_byte, path, command):
    command_bytes = command.encode()
    path_bytes = path.encode()
    part1 = bytearray(b'\x00\x00\x00')
    part2 = bytearray(b'\x03\x00\x00\x00\x12')
    message = bytearray()
    message = part1 + message_byte + part2 + path_bytes + command_bytes

    return message

def get_config():
    print('Getting config from the amplifier...')
    bytes = bytearray(b'\x00\x00\x00\x12\x01\x00\x00\x00\x07/config')
    asyncio.run(send_websocket_message(bytes, True))

@app.route('/volume/<action>', methods=['GET'])
def volume_action(action):
    global volume

    print('Checking action...')

    if action == 'plus':
        volume += 1
        set_volume()
    elif action == 'minus':
        volume -= 1
        set_volume()
    elif action == 'mute':
        set_mute(True)
    elif action == 'unmute':
        set_mute(False)
    elif action == 'togglemute':
        set_mute(not muted)
    elif action == 'dim':
        set_dimmed(True)
    elif action == 'undim':
        set_dimmed(False)
    elif action == 'toggledim':
        set_dimmed(not dimmed)
    else:
        return "Invalid action", 400

    print('Action ' + action + ' OK')
    return f"Volume action {action} executed. Current volume: {volume}", 200

@app.route('/volume/set/<value>', methods=['GET'])
def volume_set(value):
    global volume
    target = float(value)

    if not isinstance(target, float):
        return "Please provide a decimal value"

    # Amplifier limits
    if(target > 20):
        target = 20
    if(target < -120):
        target = -120

    if target == volume:
        return "Volume is already equal to target." # The amp times out when setting a value which is already set

    volume = target

    set_volume()

    print('Volume ' + str(volume) + ' OK')
    return f"Volume set to {volume}.", 200

def format_volume(volume):
    integer_part = int(volume)
    fractional_part_length = 18 - len(str(integer_part))
    formatted_volume = f"{volume:.{fractional_part_length}f}"
    return formatted_volume

def set_volume():
    global volume
    message_byte = bytearray(b'\x35') # '5'
    formatted_volume = format_volume(volume)
    volume_message = build_message(message_byte, '/optimizer/volume/', f'{{"volume":{formatted_volume}}}')
    asyncio.run(send_websocket_message(volume_message))

def set_mute(value):
    global muted
    print(f"Target {value}, current {muted}")
    message_byte = bytearray()
    message_value = str(value).lower()
    if value != muted:
        if(value):
            message_byte = bytearray(b'\x24') # '$'
        else:
            message_byte = bytearray(b'\x25') # '%'

        muted = value

        message = build_message(message_byte, '/optimizer/volume/', f'{{"mute":{message_value}}}')
        asyncio.run(send_websocket_message(message))
    
def set_dimmed(value):
    global dimmed
    message_byte = bytearray()
    message_value = str(value).lower()
    if value != dimmed:
        if(value):
            message_byte = bytearray(b'\x23') # '#'
        else:
            message_byte = bytearray(b'\x24') # '$'

        dimmed = value

        message = build_message(message_byte, '/optimizer/volume/', f'{{"dim":{message_value}}}')
        asyncio.run(send_websocket_message(message))

# TODO
@app.route('/source/<source>', methods=['GET'])
def change_source(source):
    valid_sources = ['hdmi1', 'hdmi2', 'hdmi3', 'hdmi4']

    if source not in valid_sources:
        return "Invalid source", 400

    message = json.dumps({"source": source})
    asyncio.run(send_websocket_message(message))

    return f"Source changed to {source}", 200

@app.route('/', methods=['GET'])
def index():
    global volume
    global amplifier_ip
    return f"<pre>Trinnov Remote running\n---\nVolume: {volume} dB\nIP: {amplifier_ip}</pre>", 200

if __name__ == '__main__':
    # get_config()
    app.run(host='0.0.0.0', port=5555)
