#!/usr/bin/python3

import os
import json
import paho.mqtt.client as mqtt
import soco
from dotenv import load_dotenv

load_dotenv()

socozone  = os.getenv("SONOS_ZONE", "Woonkamer Sonos")
multiplier = int(os.getenv("VOLUME_MULTIPLIER", "1"))
mqttprefix = os.getenv("MQTT_PREFIX", "zigbee2mqtt/sonosremote")
mqtthost   = os.getenv("MQTT_HOST", "localhost")
mqttport   = int(os.getenv("MQTT_PORT", "1883"))
mqttuser   = os.getenv("MQTT_USER")
mqttpass   = os.getenv("MQTT_PASS")



# class, to keep some "globals" contained

class Z2S:

    def __init__(self):
        self.discover()
        self.lastUporDown = None
        
    def discover(self):
        discovered = soco.discover()
        if discovered is not None:
            self.zones = {x.player_name: x for x in discovered}
            print(f"ZONES: {self.zones}")
        else:
            self.zones = {}
            print("No zones discovered")

        return self.zones

    def pause(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']

        if state == "PLAYING":
            print(f"Pause {speaker}")
            self.zones[speaker].pause()
        else:
            print(f"Play {speaker}")
            try:
                self.zones[speaker].play()
            except Exception as e:
                print(f"Unable to play tune on {speaker}. Try playing something from the Sonos controller first. Error: {e}")

    def skipforward(self, speaker):
        print(f"skip forward {speaker}")
        self.zones[speaker].next()

    def volup(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if state == "PLAYING":
            print(f"volume up {speaker}")
            self.zones[speaker].volume = min(self.zones[speaker].volume + multiplier, 100)

    def voldown(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if state == "PLAYING":
            print(f"volume down {speaker}")
            self.zones[speaker].volume = max(self.zones[speaker].volume - multiplier, 0)

        

############## mqtt callbacks ########################

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reasonCode, properties=None):
    print(f"MQTT Connected with result code {reasonCode}")
    if reasonCode == 4:
        print("MQTT connection refused - bad username or password")
    elif reasonCode == 5:
        print("MQTT connection refused - not authorized")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    print(f"trying to subscribe to {mqttprefix}")
    client.subscribe(mqttprefix)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))
    action = payload.get('action')

    if action == "brightness_move_up":
        z2s.lastUporDown = "down"
    elif action == "brightness_move_down":
        z2s.lastUporDown = "up"
    elif action == "brightness_stop":
        z2s.lastUporDown = None

    # move this to the object
    if socozone not in z2s.zones:
        print(f"No such speaker {socozone}, running discover")
        z2s.discover()

        if socozone not in z2s.zones:
            print("Not found after rescan")
            return

    if action in ("play_pause", "toggle"):
        # both gen1 and gen2 have play_pause
        z2s.pause(socozone)
    elif action in ("skip_forward", "track_next"):
        # gen1 - skip_forward, gen2 - track_next
        z2s.skipforward(socozone)
    elif action in ("rotate_right", "volume_up", "brightness_move_down") or (action is None and z2s.lastUporDown == "up"):
        # gen1 - rotate, gen2 - volume...
        z2s.volup(socozone)
    elif action in ("rotate_left", "volume_down", "brightness_move_up") or (action is None and z2s.lastUporDown == "down"):
        # gen1 - rotate, gen2 - volume...
        z2s.voldown(socozone)
        
################################

z2s = Z2S()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.user_data_set(z2s)
if mqttuser:
    print(f"Using mqtt user name {mqttuser} / password '{mqttpass}'")
    client.username_pw_set(mqttuser, mqttpass)
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to {mqtthost}:{mqttport}")
client.connect(mqtthost, mqttport, 60)

print("zigbee2soco starting processing of events")

# mqtt loop
client.loop_forever()
