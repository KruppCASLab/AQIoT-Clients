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
import logging
from requests.auth import HTTPBasicAuth


# set up logging configs for logging to log file messages
logging.basicConfig(
    filename='aqiot_service.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


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
    def __init__(self, base_url, user_token, auth_token, interval):
        self.base_url = base_url
        self.user_token = user_token
        self.auth_token = auth_token
        self.interval = interval


def get_pm_data():
    # Setup PM sensor
    # Note: This was added within the  function to solve issue where stale readings occur
    uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
    pm25 = PM25_UART(uart, None)

    print("Read PM data")
    logging.info("Reading PM data")
    reading_count = 0

    while True:
        time.sleep(1)

        try:
            aqdata = pm25.read()
        except RuntimeError:
            reading_count += 1
            print("Unable to read from PM sensor, retrying...")
            logging.warning("not reading sensor data")
            if reading_count > 100:
                post_log(LogType.WARNING, LogCode.SENSOR_PM25_READ_FAIL, "Excessive PM read failure, > 100")
                logging.error("Excessive PM25 Sensor fail")
                # break #possibly needed here 
            continue
        return aqdata


def dump_sensor_data(aqdata):
    now = datetime.datetime.now()
    # print stmt can be adjusted here and removed here for new formated one 
    print("%s\tPM 1.0: %d\tPM2.5: %d\tPM10: %d" % (
    now.strftime('%Y-%m-%d %H:%M:%S'), aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"]))
    info_msg = f"{now.strftime('%Y-%m-%d %H:%M:%S')}, PM 1.0: {aqdata['pm10 env']}, PM 2.5 {aqdata['pm25 env']}, PM 10: {aqdata['pm100 env']}"
    print(info_msg)
    logging.info(info_msg)


def build_url():
    # return config.base_url + str(config.client_id) + "/"
    return config.base_url + "/"


def post_log(log_type: LogType, code: LogCode, message: str):
    url = build_url() + "loggings"
    url = config.base_url
    json_data = {
        "type": log_type,
        "code": code,
        "message": message
    }
    logging.info("sending json data")
    send_request(json_data, url)


def post_data(aqdata):
    url = build_url() + "readings"
    json_data = {
        "pm25": aqdata["pm25 env"],
        "pm10": aqdata["pm10 env"],
        "pm100": aqdata["pm100 env"]
    }
    logging.info("sensor data is being posted to web service")
    send_request(json_data, url)


def send_request(json_data, url):
    try:
        headers = {
            "Content-Type": "application/json",
            # "x-api-key": config.client_key
        }

        r = requests.post(url, json=json_data, headers=headers, auth=HTTPBasicAuth(config.user_token, config.auth_token))
        if int(r.status_code) != 200:
            info_msg = f"Response from server: {r.status_code}, {r.text}"
            print("Response from server: ", r.status_code, r.text)
            logging.info(info_msg)     
        else:
            print("Response from server: ", r.status_code, r.text)
    except Exception as e:
        print("Unable to send data to server")
        logging.debug("Unable to send data to server")
        print(e)


# def update_config():
#     # Check for new config
#     response = requests.get("https://krupp.dev/aqiot/config.json")
#     source_config = response.json()
#     source_base_url = source_config["base_url"]
#     source_interval = source_config["interval"]

#     # Update config parameters and write new config
#     if source_base_url != config.base_url or source_interval != config.interval:
#         print("Updating Config")
#         logging.info("Config being updated here")
#         config.base_url = source_base_url
#         config.interval = source_interval
#         with open("config.json", "w") as fd:
#             json.dump(vars(config), fd, indent=4)


# Main Operation
with open("config.json") as fd:
    config_data = json.load(fd)
    config = Config(
                    config_data["base_url"],
                    config_data["user_token"],
                    config_data["auth_token"],
                    config_data["interval"]
                    )

if config is None:
    print("Unable to load config")
    logging.error("Config not loading properly")
    sys.exit(1)

print(config.__dict__)

# Normal Operation
print("Starting AQIoT Service")
logging.info("Starting AQIoT Service")
elapsed_sec = 0
# TODO: Logging Service Not Implemented yet
# post_log(LogType.INFO, LogCode.DEVICE_POWER_ON, "Starting Up")
while True:
    # update_config()
    aqdata = get_pm_data()
    dump_sensor_data(aqdata)
    post_data(aqdata)
    time.sleep(int(config.interval))
