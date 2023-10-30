"""
MicroPython Version of Pico AQ Sensor
MicroPython defaults to main.py
"""

import time
import network
import urequests
import ubinascii
import sys
import struct
from machine import Pin, UART
import json


class NetworkStatus:
    idle = 0
    connecting = 1
    wrong_password = -3
    no_ap = -2
    connect_fail = -1
    connect_success = 3

    string_status = {
        idle : "Idle",
        connecting : "Connecting",
        wrong_password : "Wrong Password",
        no_ap : "Access Point Does Not Exist",
        connect_fail : "Connect to Access Point Failed",
        connect_success : "Connection Success"
    }

    @staticmethod
    def return_string_status(code):
        return NetworkStatus.string_status[code]


class Error:
    CONFIG_WIFI = 1
    CONFIG_ENDPOINT = 2
    WIFI_FAILURE = 3


class ServerLogType:
    INFO = "INFO"
    ERROR = "ERROR"


class ServerLogCode:
    WIFI_CONNECT_SUCCESS = 30
    WIFI_CONNECT_FAILED = 4
    WIFI_SOCKET_POOL_HUMAN_ERROR = 5
    WIFI_SOCKET_POOL_CREATION_ERROR = 6
    WIFI_REQUESTS_POTENTIAL_HUMAN_ERROR = 7
    WIFI_REQUESTS_CREATION_ERROR_UNDEFINED_POOL = 8
    WIFI_REQUESTS_CREATION_ERROR = 9
    SENSOR_UART_FAIL = 10
    SENSOR_PM25_CREATE_FAIL_NO_UART = 11
    SENSOR_PM25_CREATE_FAIL = 12
    SENSOR_PM25_UNDEFINED = 13
    SENSOR_PM25_READ_FAIL = 14
    DATA_POST_FAILED = 16
    DATA_POST_FAILED_MAX_RETRY = 18
    DEVICE_POWER_ON = 31
    WIFI_INITIAL_LOST = 44
    GENERAL_EXCEPTION = -9


class Config:
    def __init__(self, wifi_ssid: string, wifi_pass: string, data_url: string, log_url: string, client_key: string):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


class AQData:
    def __init__(self, pm10, pm25, pm100):
        self.pm10 = pm10
        self.pm25 = pm25
        self.pm100 = pm100


class Sensor:
    def __init__(self):
        self.buffer = bytearray(32)
        self.uart = None
        self.pm25 = None

        self.delay_between_attempts = 1
        self.max_attempts = 50

        self.init_uart()

    def init_uart(self):
        try:
            self.uart = UART(0, tx=Pin(0), rx=Pin(1))
            self.uart.init(baudrate=9600, bits=8, parity=None, stop=1)
        except Exception as e:
            log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_UART_FAIL, type(e).__name__ + ": " + str(e))


    def read(self):
        # Use a dictionary to hold our data
        reading = {
            "pm10 standard": None,
            "pm25 standard": None,
            "pm100 standard": None,
            "pm10 env": None,
            "pm25 env": None,
            "pm100 env": None,
            "particles 03um": None,
            "particles 05um": None,
            "particles 10um": None,
            "particles 25um": None,
            "particles 50um": None,
            "particles 100um": None,
        }

        for i in range(0, self.max_attempts):
            time.sleep(self.delay_between_attempts)
            try:
                byte = self.uart.read(1)
                # If we did not get a byte or it doesn't match the header, continue to read
                if not byte or byte[0] != 0x42:
                    continue

                # Save the byte and read the remaining
                self.buffer[0] = byte[0]
                remaining_bytes = self.uart.read(31)

                # If we don't have any remaining bytes, or our length is not 31 (not a full message), continue
                if not remaining_bytes or len(remaining_bytes) != 31:
                    continue

                # If we get this far, we have a full message, unpack
                self.buffer[1:] = remaining_bytes
                frame_len = struct.unpack(">H", self.buffer[2:4])[0]

                # Check for invalid frame length
                if frame_len != 28:
                    continue

                '''
                    The > is big endian
                    H is for unsigned short
                    https://docs.python.org/3.0/library/struct.html
                    '''

                provided_checksum = struct.unpack(">H", self.buffer[30:32])[0]
                computed_checksum = sum(self.buffer[0:30])

                # If checksum does not match, continue
                if computed_checksum != provided_checksum:
                    continue

                # If we get this far, we have a valid frame length and checksum, unpack data and return
                (
                    reading["pm10 standard"],
                    reading["pm25 standard"],
                    reading["pm100 standard"],
                    reading["pm10 env"],
                    reading["pm25 env"],
                    reading["pm100 env"],
                    reading["particles 03um"],
                    reading["particles 05um"],
                    reading["particles 10um"],
                    reading["particles 25um"],
                    reading["particles 50um"],
                    reading["particles 100um"],
                ) = struct.unpack(">HHHHHHHHHHHH", self.buffer[4:28])

                return AQData(reading["pm10 env"], reading["pm25 env"], reading["pm100 env"])

            except Exception as e:
                print("Exception reading sensor: " + str(e) + ": retrying...")
                time.sleep(self.delay_between_attempts)

        log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_PM25_READ_FAIL,
                   "PM25 Read Failure: Reached Max Retry Count: " + str(self.max_attempts))


class Services:
    def __init__(self, config: Config):
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": config.client_key
        }
        self.config = config

        self.delay_between_attempts = 1
        self.max_attempts = 5

    def send_log_entry_to_server(self, log):
        return self.send_data(config.log_url, log)

    def send_sensor_data_to_server(self, sensor_data: AQData):
        json_data = {"pm25": sensor_data.pm25,
                     "pm10": sensor_data.pm10,
                     "pm100": sensor_data.pm100
                     }
        return self.send_data(config.data_url, json_data)

    def send_data(self, url, data):
        attempts = 1
        while attempts <= self.max_attempts:
            try:
                response = urequests.post(url, json=data, headers=self.headers)
                if int(response.status_code) != 200:
                    # TODO: Blink failure
                    log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                               "Error: Received unexpected response from server." + response.status_code + response.text)
                    response.close()
                else:
                    # TODO: Blink success
                    print("Success: Data sent to server.", response.status_code)
                    response.close()
                    return True
            except RuntimeError as re:
                log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                           "Error: Timeout in sending data to server. Exception: " + str(re))
                attempts += 1
            except Exception as e:
                log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                           "Error: Exception in sending data to server. Exception: " + str(e))
                print("Exception occurred in sending data to server:", type(e), str(e))
                attempts += 1

            attempts += 1
            time.sleep(self.delay_between_attempts)

        print("Max retry of sending reached")
        log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED_MAX_RETRY,
                   "Error: Max Retry Reached in Sending Data")
        return False

    def is_connected(self):
        return wlan.status() == 3


def connect_to_wifi(is_initial=True):
    attempts = 1
    delay = 1
    max_attempts = 25

    print("Attempting to Connect to SSID:", config.wifi_ssid)

    mac_address = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()
    wlan.disconnect()
    wlan.connect(config.wifi_ssid, config.wifi_pass)

    while attempts <= max_attempts:
        if wlan.status() == 3:
            break
        print("\tRetrying connection, Attempt:", str(attempts), "WLAN Status:",
              NetworkStatus.return_string_status(wlan.status()))
        attempts += 1
        time.sleep(delay)

    if wlan.status() == 3:
        ip = wlan.ifconfig()[0]
        if is_initial:
            log_create(ServerLogType.INFO, ServerLogCode.WIFI_CONNECT_SUCCESS,
                       "Successfully Connected to the wifi. Mac: " + str(mac_address) + " IP: " +
                       str(ip) + " | Attempt: " + str(attempts))
        return True

    else:
        if is_initial:
            report_exit_error(Error.WIFI_FAILURE, "Unable to make initial connection to WiFi")
        elif attempts == max_attempts:
            log_create(ServerLogType.ERROR, ServerLogCode.WIFI_CONNECT_FAILED,
                       "Unable to connect to wifi after max attempts " + str(attempts))
        else:
            log_create(ServerLogType.ERROR, ServerLogCode.WIFI_CONNECT_FAILED,
                       "Unable to connect to wifi wlan_status: " + str(wlan.status()) + " " +
                       NetworkStatus.return_string_status(wlan.status()))
        return False


def log_create(log_type, code, string):
    global services
    print("Log Created: ", log_type, code, string)
    log = {
        "type": log_type,  # "INFO" | "WARNING" | "ERROR"
        "code": code,
        "message": string
    }

    log_list.append(log)


def print_sensor_data(sensor_data: AQData):
    print("Sensor Reading:", sensor_data.pm25, "pm25")


def flash_led(error_type: int):
    for i in range(error_type):
        led.on()
        time.sleep(1)
        led.off()
        time.sleep(1)
    time.sleep(3)  # Circuit python has 5-second delay between errors, must not use 5 as value


def flash_led_active():
    for i in range(2):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)


def report_exit_error(error_type, label):
    print("Error type:", error_type, label)
    while True:
        flash_led(error_type)


def flush_log():
    print("Attempting to Flush Log List")
    success = []
    for log in log_list:
        print("\tAttempting to send:", log)
        result = services.send_log_entry_to_server(log)
        if result == False:
            print("\tUnable to send log entry:", log)
        else:
            print("\tSent log entry", log)
            success.append(log)

    # Remove the entries that were successful
    for log in success:
        log_list.remove(log)


def load_config():
    try:
        with open("config.json") as fd:
            config_data = json.load(fd)
            config = Config(config_data["wifi_ssid"],
                          config_data["wifi_pass"],
                          config_data["data_url"],
                          config_data["log_url"],
                          config_data["client_key"])
            if config.wifi_ssid is None or config.wifi_pass is None:
                report_exit_error(Error.CONFIG_WIFI, "WiFi config missing from toml configuration.")
            elif config.data_url is None or config.log_url is None or config.client_key is None:
                report_exit_error(Error.CONFIG_ENDPOINT, "Endpoint config missing from toml configuration.")

            return config
    except:
       return None

'''
Variables for Main Execution
'''
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Log list will hold a queue of logs to send to the server
log_list = []

# Config and network will be used globally, so declare here
config = None
services = None

# Number of seconds between readings to report data
delay = 60

# Pin to use
led = Pin("LED", machine.Pin.OUT)
led.on()

'''
Main Execution
'''
log_create(ServerLogType.INFO, ServerLogCode.DEVICE_POWER_ON, "Pico Powered On")
config = load_config()
if config is None:
    report_exit_error(Error.CONFIG_WIFI, "None config returned")

# Initialize wifi, network, and sensor
while True:
    connect_success = connect_to_wifi()
    if connect_success:
        break

services = Services(config)
flush_log()
sensor = Sensor()

# Read sensor and post data to server
while True:
    try:
        flash_led_active()
        connected = connect_to_wifi(False)
        if connected:
            print("Network is connected.", "WLAN Status:",
                  NetworkStatus.return_string_status(wlan.status()))
            data = sensor.read()
            if data is None:
                print("No sensor data was returned")
                continue
            print("Sensor data received:", data.pm25)
            print_sensor_data(data)
            services.send_sensor_data_to_server(data)

            # Make sure any log entries are sent
            flush_log()

            print("Attempting next reading in", delay, "seconds")
            time.sleep(delay)
        else:
            log_create(ServerLogType.INFO, ServerLogCode.WIFI_INITIAL_LOST, "Initial WiFi Lost - Reconnecting")
            services = Services(config)
    except Exception as e:
        log_create(ServerLogType.ERROR, ServerLogCode.GENERAL_EXCEPTION, "An general exception occurred" + str(e) + type(e))

