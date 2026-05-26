#!/usr/bin/python3

import os
import json
import logging
import threading
import paho.mqtt.client as mqtt
import soco
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

socozone   = os.getenv("SONOS_ZONE", "Woonkamer Sonos")
multiplier = int(os.getenv("VOLUME_MULTIPLIER", "1"))
mqttprefix = os.getenv("MQTT_PREFIX", "zigbee2mqtt/sonosremote")
mqtthost   = os.getenv("MQTT_HOST", "localhost")
mqttport   = int(os.getenv("MQTT_PORT", "1883"))
mqttuser   = os.getenv("MQTT_USER")
mqttpass   = os.getenv("MQTT_PASS")



# class, to keep some "globals" contained

class Z2S:

    def __init__(self, multiplier):
        self.multiplier = multiplier
        self.lastUporDown = None
        self._click_timer = None
        self._was_playing = False
        self.discover()

    def discover(self):
        discovered = soco.discover()
        if discovered is not None:
            self.zones = {x.player_name: x for x in discovered}
            log.info(f"Zones found: {list(self.zones.keys())}")
        else:
            self.zones = {}
            log.warning("No zones discovered")
        return self.zones

    def on_toggle(self, speaker):
        if self._click_timer is not None:
            # Second click within window — undo pause and skip to next track
            self._click_timer.cancel()
            self._click_timer = None
            self.skipforward(speaker)
            if self._was_playing:
                try:
                    self.zones[speaker].play()
                except Exception:
                    pass
        else:
            # First click — act immediately, open a window for a second click
            state = self.zones[speaker].get_current_transport_info()['current_transport_state']
            self._was_playing = (state == "PLAYING")
            self.pause(speaker)
            self._click_timer = threading.Timer(0.4, self._close_click_window)
            self._click_timer.start()

    def _close_click_window(self):
        self._click_timer = None

    def pause(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if state == "PLAYING":
            log.info(f"Pause {speaker}")
            self.zones[speaker].pause()
        else:
            log.info(f"Play {speaker}")
            try:
                self.zones[speaker].play()
            except Exception as e:
                log.error(f"Unable to play on {speaker}. Try playing something from the Sonos controller first. Error: {e}")

    def skipforward(self, speaker):
        log.info(f"Skip forward {speaker}")
        self.zones[speaker].next()

    def volup(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if state == "PLAYING":
            nv = min(self.zones[speaker].volume + self.multiplier, 100)
            log.info(f"Volume up {speaker} → {nv}")
            self.zones[speaker].volume = nv

    def voldown(self, speaker):
        state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if state == "PLAYING":
            nv = max(self.zones[speaker].volume - self.multiplier, 0)
            log.info(f"Volume down {speaker} → {nv}")
            self.zones[speaker].volume = nv

        

############## mqtt callbacks ########################

def on_connect(client, userdata, flags, reasonCode, properties=None):
    if reasonCode.is_failure:
        log.error(f"MQTT connection failed: {reasonCode}")
    else:
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        log.info(f"MQTT connected ({reasonCode}), subscribing to {mqttprefix}")
        client.subscribe(mqttprefix)

def on_disconnect(client, userdata, flags, reasonCode, properties=None):
    log.warning(f"MQTT disconnected: {reasonCode}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error(f"Invalid message on {msg.topic}: {e}")
        return

    z2s = userdata
    action = payload.get('action')

    if action == "brightness_move_up":
        z2s.lastUporDown = "down"
    elif action == "brightness_move_down":
        z2s.lastUporDown = "up"
    elif action == "brightness_stop":
        z2s.lastUporDown = None

    if socozone not in z2s.zones:
        log.warning(f"Speaker '{socozone}' not found, running discover")
        z2s.discover()
        if socozone not in z2s.zones:
            log.error(f"Speaker '{socozone}' not found after rescan")
            return

    if action in ("play_pause", "toggle"):
        # single click = play/pause, double click = next track
        z2s.on_toggle(socozone)
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

z2s = Z2S(multiplier)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.user_data_set(z2s)
if mqttuser:
    log.info(f"Using MQTT user '{mqttuser}'")
    client.username_pw_set(mqttuser, mqttpass)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

log.info(f"Connecting to {mqtthost}:{mqttport}")
client.connect(mqtthost, mqttport, 60)

log.info("zigbee2soco starting")
client.loop_forever()
