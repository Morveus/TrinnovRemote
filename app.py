import os
import json
import asyncio
import websockets
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
import paho.mqtt.publish as publish
from flask import Flask, request

app = Flask(__name__)

# Default configuration
volume = -60
muted = False
dimmed = False
source_id = 1

amplifier_ip = os.getenv('TRINNOV_AMPLIFIER_IP', '192.168.1.91')
listen_port = os.getenv('TRINNOV_REMOTE_PORT', '5555')
websocket_url = f"ws://{amplifier_ip}/ws"

mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
mqtt_name = os.getenv('MQTT_DEVICE_NAME', 'TrinnovAmplitude')
mqtt_identifier = os.getenv('MQTT_DEVICE_IDENTIFIER', 'trinnov_amp_1')
mqtt_topic = os.getenv('MQTT_TOPIC', 'trinnovremote/'+mqtt_identifier)

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(f"{mqtt_topic}/#")

def on_message(client, userdata, msg):
    # Handle the message here based on topic
    if("/set" in msg.topic):
        print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

    if msg.topic == f"{mqtt_topic}/volume/set":
        volume_set(msg.payload.decode())
    elif msg.topic == f"{mqtt_topic}/mute/set":
        set_mute(msg.payload.decode().lower() == 'on')
    elif msg.topic == f"{mqtt_topic}/dimmed/set":
        set_dimmed(msg.payload.decode().lower() == 'on')
    elif msg.topic == f"{mqtt_topic}/source/set":
        set_source(msg.payload.decode())

def setup_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_forever()

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

def build_message(message_byte, end_byte, path, command):
    command_bytes = command.encode()
    path_bytes = path.encode()
    part1 = bytearray(b'\x00\x00\x00')
    part2 = bytearray(b'\x03\x00\x00\x00')
    message = bytearray()
    message = part1 + message_byte + part2 + end_byte + path_bytes + command_bytes

    return message

def get_config():
    print('Getting config from the amplifier...')
    bytes = bytearray(b'\x00\x00\x00\x12\x01\x00\x00\x00\x07/config')
    asyncio.run(send_websocket_message(bytes, True))

@app.route('/volume/<action>', methods=['GET'])
def volume_action(action):
    global volume

    print('Checking action...')

    if action == 'plus' or 'up':
        volume += 1
        set_volume()
    elif action == 'minus' or 'down':
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
    volume_message = build_message(message_byte, b'\x12', '/optimizer/volume/', f'{{"volume":{formatted_volume}}}')
    asyncio.run(send_websocket_message(volume_message))
    set_mqtt_values()

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

        message = build_message(message_byte, b'\x12', '/optimizer/volume/', f'{{"mute":{message_value}}}')
        asyncio.run(send_websocket_message(message))
        set_mqtt_values()
    
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

        message = build_message(message_byte, b'\x12', '/optimizer/volume/', f'{{"dim":{message_value}}}')
        asyncio.run(send_websocket_message(message))
        set_mqtt_values()

def set_source(id):
    global source_id
    id = int(id)
    if(id == source_id):
        return "Source already set"
    
    source_id = id

    # Don't ask me why, I don't know yet (this byte changes after source 10)
    if(id < 10):
        message_byte = bytearray(b'\x22') # "double quotes"
    else:
        message_byte = bytearray(b'\x23') # "pound sign"
    
    message = build_message(message_byte, b'\x15', '/metapresets/current/', f'{{"id":{id}}}')
    asyncio.run(send_websocket_message(message))

    set_mqtt_values()

def publish_discovery_config():
    device_config = {
        "identifiers": [mqtt_identifier],
        "manufacturer": "Trinnov",
        "model": "Optimizer",
        "name": mqtt_name,
        "sw_version": "1.0"
    }

    volume_config = {
        "name": f"Volume",
        "state_topic": f"{mqtt_topic}/volume/state",
        "command_topic": f"{mqtt_topic}/volume/set",
        "unique_id": f"{mqtt_identifier}_volume",
        "device": device_config,
        "min": -120,
        "max": 20, 
        "step": 1
    }

    mute_config = {
        "name": f"Mute",
        "state_topic": f"{mqtt_topic}/mute/state",
        "command_topic": f"{mqtt_topic}/mute/set",
        "unique_id": f"{mqtt_identifier}_mute",
        "device_class": "switch",
        "device": device_config
    }

    dimmed_config = {
        "name": f"Dimmed",
        "state_topic": f"{mqtt_topic}/dimmed/state",
        "command_topic": f"{mqtt_topic}/dimmed/set",
        "unique_id": f"{mqtt_identifier}_dimmed",
        "device_class": "switch",
        "device": device_config
    }

    source_config = {
        "name": f"Source",
        "state_topic": f"{mqtt_topic}/source/state",
        "command_topic": f"{mqtt_topic}/source/set",
        "unique_id": f"{mqtt_identifier}_source",
        "device": device_config,
        "min": 0,
        "max": 30, 
        "step": 1
    }

    msgs = [
        {
            "topic": f"homeassistant/number/{mqtt_identifier}/volume/config",
            "payload": json.dumps(volume_config),
            "retain": True
        },
        {
            "topic": f"homeassistant/switch/{mqtt_identifier}/mute/config",
            "payload": json.dumps(mute_config),
            "retain": True
        },
        {
            "topic": f"homeassistant/switch/{mqtt_identifier}/dimmed/config",
            "payload": json.dumps(dimmed_config),
            "retain": True
        },
        {
            "topic": f"homeassistant/number/{mqtt_identifier}/source/config",
            "payload": json.dumps(source_config),
            "retain": True
        },
    ]

    # Publish the messages
    publish.multiple(msgs, hostname=mqtt_broker, port=mqtt_port, protocol=MQTTProtocolVersion.MQTTv5)

def set_mqtt_values():
    print("Publishing to MQTT topic " + mqtt_topic)

    message_volume = volume
    message_muted = "ON" if muted else "OFF"
    message_dimmed = "ON" if dimmed else "OFF"
    message_source = source_id

    msgs = [
        {'topic': f"{mqtt_topic}/volume/state", 'payload': str(message_volume)},
        {'topic': f"{mqtt_topic}/mute/state", 'payload': message_muted},
        {'topic': f"{mqtt_topic}/dimmed/state", 'payload': message_dimmed},
        {'topic': f"{mqtt_topic}/source/state", 'payload': str(message_source)}
    ]
    publish.multiple(msgs, hostname=mqtt_broker, port=mqtt_port, protocol=MQTTProtocolVersion.MQTTv5)

@app.route('/source/<source>', methods=['GET'])
def change_source(source):
    set_source(source)

    return f"Source changed to {source}", 200

@app.route('/', methods=['GET'])
def index():
    global volume
    global amplifier_ip
    return f"<pre>Trinnov Remote running\n---\nVolume: {volume} dB\nIP: {amplifier_ip}</pre>", 200

if __name__ == '__main__':
    # get_config()
    publish_discovery_config()
    set_mqtt_values()
    
    # Start the MQTT client in a separate thread
    mqtt_thread = threading.Thread(target=setup_mqtt_client)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    app.run(host='0.0.0.0', port=listen_port)
