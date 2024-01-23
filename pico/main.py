"""
MicroPython Version of Pico AQ Sensor
MicroPython defaults to main.py
"""
from typing import assert_never
import json
import struct
import time
import network
import ubinascii
import urequests
from machine import Pin, UART
from enum import Enum


def network_status_str(value: int) -> str:
    match value:
        case network.STAT_IDLE:
            return "Idle"
        case network.STAT_CONNECTING:
            return "Connecting"
        case network.STAT_WRONG_PASSWORD:
            return "Failed due to incorrect password"
        case network.STAT_NO_AP_FOUND:
            return "Failed due to no access point"
        case network.STAT_CONNECT_FAIL:
            return "Failed (generic)"
    return "Unknown"


class Error(Enum):
    CONFIG_WIFI = 1
    CONFIG_ENDPOINT = 2
    WIFI_FAILURE = 3


# Corresponds to server log types
class LogType:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Corresponds to server log codes
class LogCode(Enum):
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
    def __init__(self, wifi_ssid: str, wifi_pass: str, data_url: str, log_url: str, client_key: str):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


class AQData:
    def __init__(self, pm10: str, pm25: str, pm100: str):
        self.pm10 = pm10
        self.pm25 = pm25
        self.pm100 = pm100


def create_uart() -> UART | None:
    try:
        uart = UART(id=0)
        uart.init(baudrate=9600, bits=8, parity=None,
                  stop=1, tx=Pin(0), rx=Pin(1))
        return uart
    except Exception as e:
        log(LogType.ERROR,
            LogCode.SENSOR_UART_FAIL,
            f'{type(e).__name__}: {e}')


class Sensor:
    def __init__(self):
        self.buffer = bytearray(32)
        self.uart = create_uart()
        self.pm25 = None

        self.delay_between_attempts = 1
        self.max_attempts = 50

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

        for _ in range(0, self.max_attempts):
            time.sleep(self.delay_between_attempts)
            try:
                if self.uart == None:
                    continue
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

        log(LogType.ERROR, LogCode.SENSOR_PM25_READ_FAIL,
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

    def send_log_entry_to_server(self, log) -> bool:
        if config != None:
            return self.send_data(config.log_url, log)
        return False

    def send_sensor_data_to_server(self, sensor_data: AQData) -> bool:
        json_data = {"pm25": sensor_data.pm25,
                     "pm10": sensor_data.pm10,
                     "pm100": sensor_data.pm100
                     }
        if config != None:
            return self.send_data(config.data_url, json_data)
        return False

    def send_data(self, url, data):
        attempts = 1
        while attempts <= self.max_attempts:
            try:
                response = urequests.post(url, json=data, headers=self.headers)
                if int(response.status_code) != 200:
                    # TODO: Blink failure
                    log(LogType.ERROR, LogCode.DATA_POST_FAILED,
                        "Error: Received unexpected response from server." + str(
                            response.status_code) + response.text)
                    response.close()
                else:
                    # TODO: Blink success
                    print("Success: Data sent to server.",
                          str(response.status_code))
                    response.close()
                    return True
            except RuntimeError as re:
                log(LogType.ERROR, LogCode.DATA_POST_FAILED,
                    "Error: Timeout in sending data to server. Exception: " + str(re))
                attempts += 1
            except Exception as e:
                log(LogType.ERROR, LogCode.DATA_POST_FAILED,
                    "Error: Exception in sending data to server. Exception: " + str(e))
                print("Exception occurred in sending data to server:",
                      type(e), str(e))
                attempts += 1

            attempts += 1
            time.sleep(self.delay_between_attempts)

        print("Max retry of sending reached")
        log(LogType.ERROR, LogCode.DATA_POST_FAILED_MAX_RETRY,
            "Error: Max Retry Reached in Sending Data")
        return False

    def is_connected(self):
        return wlan.status() == network.STAT_GOT_IP


def connect_to_wifi(is_initial=True):
    attempts = 1
    delay = 1
    max_attempts = 25

    if config == None:
        report_error(Error.CONFIG_WIFI, "Config is None")
        return

    print("Attempting to Connect to SSID:", config.wifi_ssid)

    mac_address = ubinascii.hexlify(network.WLAN(
        network.STA_IF).config('mac'), ':').decode()
    wlan.disconnect()
    wlan.connect(config.wifi_ssid, config.wifi_pass)

    while attempts <= max_attempts:
        if wlan.status() == 3:
            break
        print("\tRetrying connection, Attempt:", str(attempts), "WLAN Status:",
              network_status_str(wlan.status()))  # TODO: check if this prints right
        attempts += 1
        time.sleep(delay)

    if wlan.status() == 3:
        ip = wlan.ifconfig()[0]
        if is_initial:
            log(LogType.INFO, LogCode.WIFI_CONNECT_SUCCESS,
                "Successfully Connected to the wifi. Mac: " + str(mac_address) + " IP: " +
                str(ip) + " | Attempt: " + str(attempts))
        return True

    else:
        if is_initial:
            report_error(Error.WIFI_FAILURE,
                         "Unable to make initial connection to WiFi")
        elif attempts == max_attempts:
            log(LogType.ERROR, LogCode.WIFI_CONNECT_FAILED,
                "Unable to connect to wifi after max attempts " + str(attempts))
        else:
            log(LogType.ERROR, LogCode.WIFI_CONNECT_FAILED,
                "Unable to connect to wifi wlan_status: " + str(wlan.status()) + " " +
                network_status_str(wlan.status()))
        return False


def log(log_type, code, string):
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


def flash_led_error(error_type: Error):
    n_blinks = 0
    match error_type:
        case Error.CONFIG_WIFI:
            n_blinks = 1
        case Error.CONFIG_ENDPOINT:
            n_blinks = 2
        case Error.WIFI_FAILURE:
            n_blinks = 3
        case _:
            assert_never(error_type)

    for _ in range(n_blinks):
        led.on()
        time.sleep(1)
        led.off()
        time.sleep(1)
    # Circuit python has 5-second delay between errors, must not use 5 as value
    time.sleep(3)


# TODO: This seems to overlap with error blinking
def flash_led_active():
    for _ in range(2):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)


def report_error(error_type: Error, label: str):
    print("Error type:", error_type, label)
    for _ in range(5):
        flash_led_error(error_type)


def flush_log():
    print("Attempting to Flush Log List")
    success = []
    for log in log_list:
        print("\tAttempting to send log entry:", log)
        result = services.send_log_entry_to_server(log)
        if result == False:
            print("\tUnable to send log entry:", log)
        else:
            print("\tSent log entry", log)
            success.append(log)

    # Remove the entries that were successful
    for log in success:
        log_list.remove(log)


def load_config() -> Config | None:
    try:
        with open("config.json") as fd:
            config_data = json.load(fd)
            config = Config(config_data["wifi_ssid"],
                            config_data["wifi_pass"],
                            config_data["data_url"],
                            config_data["log_url"],
                            config_data["client_key"])
            if config.wifi_ssid is None or config.wifi_pass is None:
                report_error(Error.CONFIG_WIFI,
                             "WiFi config missing from toml configuration.")
                return None
            elif config.data_url is None or config.log_url is None or config.client_key is None:
                report_error(Error.CONFIG_ENDPOINT,
                             "Endpoint config missing from toml configuration.")
                return None

            return config
    except:
        return None


'''
Variables for Main Execution
'''
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Log list will hold a queue of logs to send to the server
log_list = []  # TODO: type

# Number of seconds between readings to report data
delay = 60

# Pin to use
led = Pin("LED", Pin.OUT)  # TODO: string for pin id?
led.on()

'''
Main Execution
'''
log(LogType.INFO, LogCode.DEVICE_POWER_ON, "Pico Powered On")
config = load_config()
while config is None:
    report_error(Error.CONFIG_WIFI, "None config returned")
    config = load_config()

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
                  network_status_str(wlan.status()))
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
            log(LogType.INFO, LogCode.WIFI_INITIAL_LOST,
                "Initial WiFi Lost - Reconnecting")
            services = Services(config)
    except Exception as e:
        log(LogType.ERROR, LogCode.GENERAL_EXCEPTION, f'{type(e)}: {e}')
