#!/usr/bin/python3

import sys 
import os
from dotenv import load_dotenv

load_dotenv()

# debug code in case docker doesn't find the modules
#for path in sys.path:
#    print(path)


try:
    socozone=int(os.environ.get("SONOS_ZONE"))
except:
    socozone="Woonkamer Sonos"

try:
    multiplier=int(os.environ.get("VOLUME_MULTIPLIER"))
except:
    multiplier=1

try:
    mqttprefix=os.environ.get("MQTT_PREFIX")
except:
    mqttprefix="zigbee2mqtt/sonosremote"

try:
    mqtthost=os.environ.get("MQTT_HOST")
except:
    mqtthost="localhost"

try:
    mqttport=os.environ.get("MQTT_PORT")
except:
    mqttport=1883

try:
    mqttuser=os.environ.get("MQTT_USER")
except:
    mqttuser=None
    
try:
    mqttpass=os.environ.get("MQTT_PASS")
except:
    mqttpass=None

    
import paho.mqtt.client as mqtt
import soco
import traceback
import json



# class, to keep some "globals" contained

class Z2S:

    def __init__(self):
        self.discover()
        self.lastUporDown = None
        
    def discover(self):
        discovered = soco.discover()
        if discovered is not None:
            self.zones = {x.player_name: x for x in discovered}
            print("ZONES: "+str(self.zones))
        else:
            self.zones = {}
            print("No zones discovered")

        
        return self.zones

    def pause(self, speaker):
        self.state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        #print(state)

        if self.state == "PLAYING":
            print("Pause " + speaker)
            self.zones[speaker].pause()
        
        else:
            print("Play " + speaker)
            try:                
                self.zones[speaker].play()
            except Exception as e:
                print(f"Unable to play tune on {speaker}. Try playing something from the Sonos controller first. Error: {e}")
                pass

    def skipforward(self, speaker):
        print("skip forward "+speaker)

        self.zones[speaker].next()

    def volup(self, speaker):
        self.state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if self.state == "PLAYING":
            print("volume up " + speaker)
            nv = min(self.zones[speaker].volume + multiplier, 100)
            self.zones[speaker].volume = nv

    def voldown(self, speaker):
        self.state = self.zones[speaker].get_current_transport_info()['current_transport_state']
        if self.state == "PLAYING":
            print("volume down " + speaker)
            nv = max(self.zones[speaker].volume-multiplier,0)
            self.zones[speaker].volume = nv

        

############## mqtt callbacks ########################

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reasonCode, properties=None):
    print("MQTT Connected with result code "+str(reasonCode))
    if reasonCode == 4:
        print("MQTT connection refused - bad username or password")
    elif reasonCode == 5:
        print("MQTT connection refused - not authorized")
        
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    
    print("trying to subscribe to "+mqttprefix)
    client.subscribe(mqttprefix)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):

    decoded_message=str(msg.payload.decode("utf-8"))
    payload=json.loads(decoded_message)
    action = payload.get('action')
    volume = payload.get('brightness')
    # print(decoded_message)
    # print(action)
    # print(volume)

    if action == "brightness_move_up":
        z2s.lastUporDown = "up"
    elif action == "brightness_move_down":
        z2s.lastUporDown = "down"   
    elif action == "brightness_stop":
        z2s.lastUporDown = None

    # move this to the object
    if not socozone in z2s.zones:
        print("No such speaker "+socozone+" running discover")
        z2s.discover()

        if not socozone in z2s.zones:
            print ("Not found after rescan")
            return

    if action == "play_pause" or action == "toggle":
        # both gen1 and gen2 have play_pause
        z2s.pause(socozone)
    elif action == "skip_forward" or action == "track_next":
        # gen1 - skip_forward, gen2 - track_next
        z2s.skipforward(socozone)
    elif action == "rotate_right" or action == "volume_up" or action == "brightness_move_up" or (action == None and z2s.lastUporDown == "up"):
        # gen1 - rotate, gen2 - volume...
        z2s.volup(socozone)
    elif action == "rotate_left"  or action == "volume_down" or action == "brightness_move_down" or (action == None and z2s.lastUporDown == "down"):
        # gen1 - rotate, gen2 - volume...
        z2s.voldown(socozone)
        
################################

z2s = Z2S()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.user_data_set(z2s)
if mqttuser:
    print ("Using mqtt user name "+mqttuser+" / password '"+mqttpass+"'")
    client.username_pw_set(mqttuser, mqttpass)
client.on_connect = on_connect
client.on_message = on_message

print ("Connecting to "+mqtthost+":"+str(mqttport))
client.connect(mqtthost, int(mqttport), 60)

print ("zigbee2soco starting processing of events")

# mqtt loop
client.loop_forever()
