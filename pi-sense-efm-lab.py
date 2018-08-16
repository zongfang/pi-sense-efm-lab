#!/usr/bin/env python3
"""
Use the Raspberry Pi Sense Hat as part of an Cisco Kinetic EFM Lab to
- Act as a sensor and send environmental data via MQTT
- Display received data from MQTT via the RGB LED matrix
- Act as a control and send joystick actions via MQTT
"""
import argparse
import logging
import signal
import sys
import time
import json
import configparser
import paho.mqtt.client as mqtt
from sense_hat import SenseHat

# Keep track of whether to exit the program or not
EXIT_FLAG = False

# Whether we are connected to the MQTT broker or not
MQTT_CONNECTED = False

# The MQTT client
client = False

# Set up the Sense Hat
sense = SenseHat()

# The config
config = False


def signal_handler(signum, frame):
    """ Handle OS signals """
    log = logging.getLogger('pi-sense-efm-lab')
    global EXIT_FLAG
    if signum == signal.SIGTERM or signum == signal.SIGINT:
        log.warning('Received quit signal')
        EXIT_FLAG = True


def on_mqtt_connect(client, userdata, flags, rc):
    """ Handle MQTT broker connect events """
    global MQTT_CONNECTED
    log = logging.getLogger('pi-sense-efm-lab')
    if rc == 0:
        # Successful connection
        log.info('Connected to MQTT broker')
        MQTT_CONNECTED = True

        # Subscribe to the display topic with subtopic ID
        display_topic = '{0}/{1}'.format(config['display']['topic'], config['mqtt']['id'])
        client.subscribe(display_topic)
    else:
        # An error of some kind
        log.error('MQTT broker connection error: {0}'.format(mqtt.connack_string(rc)))
        MQTT_CONNECTED = False


def on_mqtt_disconnect(client, userdata, rc):
    """ Handle MQTT broker disconnect events """
    global MQTT_CONNECTED
    log = logging.getLogger('pi-sense-efm-lab')
    MQTT_CONNECTED = False
    if rc != 0:
        # Not a disconnect the client asked for
        log.warning('Disconnected from MQTT broker: {0}'.format(mqtt.connack_string(rc)))


def on_mqtt_message(client, userdata, message):
    """ Handle incoming MQTT messages """
    log = logging.getLogger('pi-sense-efm-lab')
    log.debug('Received MQTT message on topic {0}: {1}'.format(message.topic, message.payload))
    display_topic = '{0}/{1}'.format(config['display']['topic'], config['mqtt']['id'])

    if message.topic == display_topic:
        try:
            data = json.loads(message.payload.decode('utf8'))
        except json.JSONDecodeError:
            log.warning('Unable to decode MQTT message on topic {0}: {1}'.format(message.topic, message.payload))
        else:
            if 'action' in data:
                if data['action'] == config['display']['clear']:
                    sense.clear()
                elif data['action'] == config['display']['draw']:
                    if 'x' in data and 'y' in data and len(data['color']) == 3:
                        sense.set_pixel(data['x'], data['y'], data['color'])
                elif data['action'] == config['display']['text']:
                    if 'text' in data and 'color' in data and len(data['color']) == 3:
                        sense.show_message(data['text'], text_colour=data['color'])
                    else:
                        log.warning('Display text missing required parameters: {0}'.format(message.payload))
                else:
                    log.info('Unknown display action specified: {0}'.format(data['action']))
            else:
                log.warning('Display message missing action specifier: {0}'.format(message.payload))


def send_sensor_data():
    """ Read the environmental sensors and send the data via MQTT """
    if MQTT_CONNECTED:
        topic = '{0}/{1}'.format(config['sensor']['topic'], config['mqtt']['id'])
        message = {
            'id': config['mqtt']['id'],
            'timestamp': time.time(),
            'humidity': sense.get_humidity(),
            'temp_c': sense.get_temperature(),
            'press_hpa': sense.get_pressure() / 100
        }
        client.publish(topic, json.dumps(message))


def send_joystick_data(event):
    """ Read the joystick buffer and send the data via MQTT """
    if MQTT_CONNECTED:
        topic = '{0}/{1}'.format(config['control']['topic'], config['mqtt']['id'])
        message = {
            'id': config['mqtt']['id'],
            'timestamp': event.timestamp,
            'direction': event.direction,
            'action': event.action
        }
        client.publish(topic, json.dumps(message))


def main():
    """
    The main program to run when invoked as a script
    """
    global config, client

    # Set up command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log_file', default='pi-sense-efm-lab.log', help='The log file to save the script output (default: %(default)s)')
    parser.add_argument('--conf_file', default='pi-sense-efm-lab.ini', help='The config file to use (default: %(default)s)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode, displaying all output to the console')
    args = parser.parse_args()

    # Set up logging
    log = logging.getLogger('pi-sense-efm-lab')
    log_format = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S %Z')
    if args.debug:
        # Log everything to the console when in debug mode
        log.setLevel(logging.DEBUG)
        console = logging.StreamHandler()
        console.setFormatter(log_format)
        log.addHandler(console)
    else:
        # Log everything to our config file when not in debug mode
        log.setLevel(logging.INFO)
        file_log = logging.FileHandler(args.log_file)
        file_log.setFormatter(log_format)
        log.addHandler(file_log)

    # Register SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log.info('Starting up')

    # Clear the display
    sense.clear()

    # Load the main config file
    config = configparser.ConfigParser()
    config.read(args.conf_file)
    log.info('This is MQTT client {0}'.format(config['mqtt']['id']))

    # Connect to the MQTT broker and register handlers
    log.info('Using MQTT broker at {0}'.format(config['mqtt']['broker']))
    client = mqtt.Client(config['mqtt']['id'])
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.on_message = on_mqtt_message
    client.connect_async(config['mqtt']['broker'])
    client.loop_start()

    # Register joystick clicks
    sense.stick.direction_any = send_joystick_data

    last_run = time.time()
    while not EXIT_FLAG:
        now = time.time()
        if (now - last_run) >= float(config['sensor']['publish_freq']):
            send_sensor_data()
            last_run = time.time()
        else:
            time.sleep(0.1)

    # Shut down the MQTT connection
    log.info('Disconnecting from MQTT broker')
    client.loop_stop()
    client.disconnect()

    # Clear the display
    sense.clear()

    log.info('Shutting down')


if __name__ == '__main__':
    main()
