import time
import board
import json
import busio
import serial
import requests
import datetime
import sys
from adafruit_pm25.uart import PM25_UART


class Config:
    def __init__(self, wifi_ssid, wifi_pass, data_url, log_url, client_key):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


with open("config.json") as fd:
    config_data = json.load(fd)
    config = Config(config_data["wifi_ssid"],
                    config_data["wifi_pass"],
                    config_data["data_url"],
                    config_data["log_url"],
                    config_data["client_key"])

if config is None:
    print("Unable to load config")
    sys.exit(1)

print(config.__dict__)

config_interval = 60

print("Starting AQIoT Service")


def get_pm_data():
    # Setup PM sensor
    # Note: This was added within the  function to solve issue where stale readings occur
    uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
    pm25 = PM25_UART(uart, None)

    print("Read PM data")

    reading_count = 0

    while True:
        time.sleep(1)

        try:
            aqdata = pm25.read()
        except RuntimeError:
            print("Unable to read from PM sensor, retrying...")
            continue
        return aqdata


def dump_sensor_data(aqdata):
    now = datetime.datetime.now()
    print("%s\tPM 1.0: %d\tPM2.5: %d\tPM10: %d" % (
    now.strftime('%Y-%m-%d %H:%M:%S'), aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"]))


def post_data(aqdata):
    print("Sending Data")
    try:
        json_data = {
            "pm25": aqdata["pm25 env"],
            "pm10": aqdata["pm10 env"],
            "pm100": aqdata["pm100 env"]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.client_key
        }

        r = requests.post(config.data_url, json=json_data, headers=headers)
        if int(r.status_code) != 200:
            print("Response from server: ", r.status_code, r.text)
        else:
            print("Response from server: ", r.status_code, r.text)
    except Exception as e:
        print("Unable to send data to server, will attempt on next reading")
        print(e)
    print("Done Sending Data")


# Normal Operation
elapsed_sec = 0
while True:
    aqdata = get_pm_data()
    dump_sensor_data(aqdata)
    post_data(aqdata)
    time.sleep(config_interval)
