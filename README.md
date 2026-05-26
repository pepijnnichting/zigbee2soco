This connects sonos to zigbee2mqtt to control SONOS speakers with the IKEA SYMFONISK controllers - the rotary (gen1) and the new "flat" (gen2).

Tested with Sonos S2 - unknown if it works with S1.

The controller need to be named as the speaker, e.g. mqtt topic _prefix_/_speaker_, then everything works out of the box.
This is case sensitive and _prefix_ need to uniquely identify what messages are from controllers.

Easiest way to keep this running is with docker:
`docker-compose build && docker-compose up -d`

# Configuration:

You can either edit the config into the source, or if using docker-compose, change the environment variables in docker-compose.yml:

- MQTT*PREFIX=zigbee/stereo \_the zigbee mqtt prefix, as described above*
- MQTT*HOST=localhost \_mqtt host*
- MQTT*PORT=1883 \_mqtt port*
- MQTT*USER=minion \_mqtt user*
- MQTT*PASS=banana \_mqtt password*
- VOLUME*MULTIPLIER=2 \_higher number -> quicker reaction when turning the button*

# Implemented:

- pause/restart - single click on button
- skip to next in playlist - double click on button
- volume control - might require the config above (debounce etc). The volume cannot be adjusted unless the speaker is playing something.

# For those using Symfonisk Generation 1 - Rotary Controller (E1744)

You need to configure the device in zigbee2mqtt, see https://www.zigbee2mqtt.io/devices/E1744.html

Use the following config in your zigbee2mqtt `devices.yaml`:

```yaml
"0xYOURADDRESS":
  friendly_name: Woonkamer Sonos
  legacy: false
  debounce: 0.1
  debounce_ignore:
    - action
```

- `legacy: false` — required for correct action names (`toggle`, `brightness_move_up` etc.)
- `debounce: 0.1` — ensures toggle events arrive within 100ms (needed for double-click detection)
- `debounce_ignore: action` — ensures every unique action is published immediately
- No `simulated_brightness` — lets the hardware send events at its natural rate, so faster turning = faster volume change
