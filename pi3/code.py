import time
import board
import json
import busio
import serial
import requests
import datetime
import sys
from adafruit_pm25.uart import PM25_UART
from enum import Enum

class LogType(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogCode(int, Enum):
    WIFI_CONNECT_SUCCESS = 30
    WIFI_CONNECT_FAILED = 4
    SENSOR_PM25_READ_FAIL = 14
    DEVICE_POWER_ON = 31


class Config:
    def __init__(self, wifi_ssid, wifi_pass, data_url, log_url, client_key):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


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
            reading_count += 1
            print("Unable to read from PM sensor, retrying...")
            if reading_count > 100:
                post_log(LogType.WARNING, LogCode.SENSOR_PM25_READ_FAIL, "Excessive PM read failure, > 100")
            continue
        return aqdata


def dump_sensor_data(aqdata):
    now = datetime.datetime.now()
    print("%s\tPM 1.0: %d\tPM2.5: %d\tPM10: %d" % (
    now.strftime('%Y-%m-%d %H:%M:%S'), aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"]))


def post_log(log_type: LogType, code: LogCode, message: str):
    json_data = {
        "type": log_type,
        "code": code,
        "message": message
    }
    send_request(json_data, config.log_url)


def post_data(aqdata):
    json_data = {
        "pm25": aqdata["pm25 env"],
        "pm10": aqdata["pm10 env"],
        "pm100": aqdata["pm100 env"]
    }
    send_request(json_data, config.data_url)


def send_request(json_data, url):
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.client_key
        }

        r = requests.post(url, json=json_data, headers=headers)
        if int(r.status_code) != 200:
            print("Response from server: ", r.status_code, r.text)
        else:
            print("Response from server: ", r.status_code, r.text)
    except Exception as e:
        print("Unable to send data to server")
        print(e)


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


# Normal Operation
print("Starting AQIoT Service")
elapsed_sec = 0
post_log(LogType.INFO, LogCode.DEVICE_POWER_ON, "Starting Up")
while True:
    aqdata = get_pm_data()
    dump_sensor_data(aqdata)
    post_data(aqdata)
    time.sleep(config_interval)
