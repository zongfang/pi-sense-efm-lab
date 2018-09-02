## Synopsis

Use the Raspberry Pi Sense Hat as part of a Cisco Kinetic EFM Lab to
- Act as a sensor and send environmental data via MQTT
- Act as a control and send joystick actions via MQTT
- Display received data from MQTT via the RGB LED matrix

## Hardware
This has only been tested on Raspbian running on a Raspberry Pi 3 Model B+ and the official Sense HAT.

## Installation

### Install Prerequisites
```
sudo apt update
sudo apt install sense-hat python3-pip
sudo pip3 install paho-mqtt
sudo reboot
```

### Download and Install
This assumes a local sudo user called `picon` exists and the project will be installed in `~/pi-sense-efm-lab`. It also assumes the `pi-sense-boot` project is being used. Adjust the .service file accordingly to change paths and startup dependencies.

1. Clone or download the project via Github
2. Install the service
```
cd ~/pi-sense-efm-lab
sudo mv pi-sense-efm-lab.service /lib/systemd/system/
sudo systemctl enable pi-sense-efm-lab
```

## MQTT Message Reference

### Sensor
These JSON messages are published to the `sensor` topic every 3 seconds, unless set differently in the .ini file.
```
{
    "id": "pi-sense",
    "timestamp": time.time(),
    "humidity": sense.get_humidity(),
    "temp_c": sense.get_temperature(),
    "press_hpa": sense.get_pressure() / 100
}
```

### Control
These JSON messages are published to the `control` topic as joystick events are created, unless set differently in the .ini file.
```
{
    "id": "pi-sense",
    "timestamp": event.timestamp,
    "direction": event.direction,
    "action": event.action
}
```

### Display
These JSON messages are received and processed via MQTT on the subscribed `display/pi-sense` topic, unless set differently in the .ini file.

#### Clear the display
```
{
    "action": "clear"
}
```

#### Display some text
```
{
    "action": "text",
    "text": "This is the message to show",
    "color": [red_value, green_value, blue_value]
}
```

#### Set a pixel
```
{
    "action": "draw",
    "x": x_value,
    "y": y_value,
    "color": [red_value, green_value, blue_value]
}
```

## License

This project is licensed under the MIT License.