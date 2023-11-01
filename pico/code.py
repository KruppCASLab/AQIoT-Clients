"""
CircuitPython Version of Pico AQ Sensor
CircuitPython defaults to code.py
"""

import time
import board
import busio
import os
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests
from digitalio import DigitalInOut, Direction, Pull
from adafruit_pm25.uart import PM25_UART
import ipaddress
import digitalio
import sys


# CircuitPython does not support enums at this time, using class to code errors
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


class Sensor:
    def __init__(self):
        self.uart = None
        self.pm25 = None

        self.delay_between_attempts = 1
        self.max_attempts = 50

        self.init_uart()
        self.init_pm25()

    def init_uart(self):
        try:
            self.uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
        except Exception as e:
            log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_UART_FAIL, type(e).__name__ + ": " + str(e))

    def init_pm25(self):
        try:
            self.pm25 = PM25_UART(self.uart, None)  # 2nd parameter is reset pin
        except NameError as e:
            log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_PM25_CREATE_FAIL_NO_UART,
                       type(e).__name__ + ": " + str(e))
        except Exception as e:
            log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_PM25_CREATE_FAIL, type(e).__name__ + ": " + str(e))

    def read(self):
        for i in range(0, self.max_attempts):
            try:
                reading = self.pm25.read()
                aqdata = AQData(reading["pm10 env"], reading["pm25 env"], reading["pm100 env"])
                return aqdata
            except NameError as e:
                log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_PM25_UNDEFINED, type(e).__name__ + ": " + str(e))
                time.sleep(self.delay_between_attempts)
            except Exception as e:
                print("Exception reading sensor: " + str(e) + ": retrying...")
                time.sleep(self.delay_between_attempts)

        log_create(ServerLogType.ERROR, ServerLogCode.SENSOR_PM25_READ_FAIL,
                   "PM25 Read Failure: Reached Max Retry Count: " + str(self.max_attempts))


class AQData:
    def __init__(self, pm10, pm25, pm100):
        self.pm10 = pm10
        self.pm25 = pm25
        self.pm100 = pm100


class Network:
    def __init__(self, config: Config):
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": config.client_key
        }
        self.config = config
        self.socketpool = None
        self.requests = None

        self.delay_between_attempts = 1
        self.max_attempts = 5

        self.init_socket_pool()
        self.init_requests()

    def init_socket_pool(self):
        attempts = 1

        while attempts <= self.max_attempts:
            try:
                self.socketpool = socketpool.SocketPool(wifi.radio)
                break  # Break of the loop if initialization is successful
            except (AttributeError, ValueError, TypeError, RuntimeError, SyntaxError) as e:
                print(type(e).__name__, ":", str(e))
                print("Potential human error")
                log_create(ServerLogType.ERROR, ServerLogCode.WIFI_SOCKET_POOL_HUMAN_ERROR,
                           type(e).__name__ + ": " + str(e))
                break  # Human Error
            except Exception as e:
                print("Caught", type(e).__name__, ":", str(e))
                print("Retrying Pool Creation, Attempt:", str(attempts + 1))
                log_create(ServerLogType.ERROR, ServerLogCode.WIFI_SOCKET_POOL_CREATION_ERROR,
                           type(e).__name__ + ": " + str(e))
                attempts += 1
                time.sleep(self.delay_between_attempts)
        else:
            print("Failed Pool Creation")

    def init_requests(self):
        attempts = 1

        while attempts <= self.max_attempts:
            try:
                self.requests = adafruit_requests.Session(self.socketpool, ssl.create_default_context())
                break  # Break of the loop if initialization is successful
            except (AttributeError, ValueError, TypeError, RuntimeError) as e:
                log_create(ServerLogType.ERROR, ServerLogCode.WIFI_REQUESTS_POTENTIAL_HUMAN_ERROR,
                           type(e).__name__ + ": " + str(e))
                break  # Human Error
            except NameError as e:
                log_create(ServerLogType.ERROR, ServerLogCode.WIFI_REQUESTS_CREATION_ERROR_UNDEFINED_POOL,
                           type(e).__name__ + ": " + str(e))
            except Exception as e:
                print("Retrying Session Creation, Attempt:", str(attempts + 1))
                log_create(ServerLogType.ERROR, ServerLogCode.WIFI_REQUESTS_CREATION_ERROR,
                           type(e).__name__ + ": " + str(e))
                attempts += 1
                time.sleep(self.delay_between_attempts)
        else:
            print("Failed Session Creation")

    def send_log_entry_to_server(self, log):
        # Don't log on failure that we cannot send the entry
        return self.send_data(config.log_url, log, False)

    def send_sensor_data_to_server(self, sensor_data: AQData):
        json_data = {"pm25": sensor_data.pm25,
                     "pm10": sensor_data.pm10,
                     "pm100": sensor_data.pm100
                     }
        return self.send_data(config.data_url, json_data)

    def send_data(self, url, data, should_log=True):
        if self.requests is not None:
            attempts = 1
            while attempts <= self.max_attempts:
                try:
                    response = self.requests.post(url, json=data, headers=self.headers)
                    if int(response.status_code) != 200:
                        # TODO: Blink failure
                        if should_log:
                            log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                                       "Error: Received unexpected response from server." + response.status_code + response.text)
                        response.close()
                    else:
                        # TODO: Blink success
                        print("Success: Data sent to server.", response.status_code)
                        response.close()
                        return True
                except RuntimeError as re:
                    if should_log:
                        log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                                   "Error: Timeout in sending data to server. Exception: " + str(re))
                    attempts += 1
                except Exception as e:
                    if should_log:
                        log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED,
                                   "Error: Exception in sending data to server. Exception: " + str(e))
                    print("Exception occurred in sending data to server:", type(e), str(e))
                    attempts += 1

                attempts += 1
                time.sleep(self.delay_between_attempts)

            print("Max retry of sending reached")
            if should_log:
                log_create(ServerLogType.ERROR, ServerLogCode.DATA_POST_FAILED_MAX_RETRY,
                           "Error: Max Retry Reached in Sending Data")
            return False

        else:
            print("Network requests have not yet been defined.")
            return False

    def is_connected(self):
        return wifi.radio.connected


def flash_led(error_type: int):
    for i in range(error_type):
        led.value = True
        time.sleep(1)
        led.value = False
        time.sleep(1)
    time.sleep(3)  # Circuit python has 5-second delay between errors, must not use 5 as value


def flash_led_active():
    for i in range(2):
        led.value = True
        time.sleep(0.1)
        led.value = False
        time.sleep(0.1)


def report_error(error_type, label):
    print("Error type:", error_type, label)
    for i in range(5):
        flash_led(error_type)


def load_toml_config():
    try:
        # Get configuration variables from settings.toml file
        wifi_ssid = os.getenv("WIFI_SSID")
        wifi_pass = os.getenv("WIFI_PASSWORD")

        data_endpoint_url = os.getenv("DATA_ENDPOINT_URL")
        log_endpoint_url = os.getenv("LOG_ENDPOINT_URL")
        client_key = os.getenv("CLIENT_KEY")

        if wifi_ssid is None or wifi_pass is None:
            report_error(Error.CONFIG_WIFI, "WiFi config missing from toml configuration.")
            return None
        elif data_endpoint_url is None or log_endpoint_url is None or client_key is None:
            report_error(Error.CONFIG_ENDPOINT, "Endpoint config missing from toml configuration.")
            return None

        config = Config(wifi_ssid, wifi_pass, data_endpoint_url, log_endpoint_url, client_key)

        return config
    except:
        return None


def connect_to_wifi(is_initial=True):
    attempts = 1
    delay = 1
    max_attempts = 25

    print("Attempting to Connect to SSID:", config.wifi_ssid)

    mac_address = [hex(i) for i in wifi.radio.mac_address]

    while attempts <= max_attempts:
        try:
            wifi.radio.connect(config.wifi_ssid, config.wifi_pass)
            if is_initial:
                log_create(ServerLogType.INFO, ServerLogCode.WIFI_CONNECT_SUCCESS,
                           "Successfully Connected to the wifi: " +
                           str(config.wifi_ssid) + " | " +
                           "Mac: " + str(mac_address) + " IP: " +
                           str(wifi.radio.ipv4_address) + " | Attempt: " + str(attempts))
            break
        except (ValueError, TypeError, RuntimeError, SyntaxError, KeyError, ConnectionError, Exception) as e:
            log_create(ServerLogType.ERROR, ServerLogCode.WIFI_CONNECT_FAILED,
                       "Unable to connect to wifi | Attempt: " + str(attempts) + "Exception:" + type(e).__name__ +
                       "Error:  " + str(e))

            print("Retrying connection, Attempt:", str(attempts))
            attempts += 1
            time.sleep(delay)
    else:
        # At this point, if we cannot connect to wifi after max attempts, report failure
        if is_initial:
            report_error(Error.WIFI_FAILURE, "Failed to Connect to WiFi")
        return False

    return True


def log_create(log_type, code, string):
    print("Log Created: ", log_type, code, string)
    log = {
        "type": log_type,  # "INFO" | "WARNING" | "ERROR"
        "code": code,
        "message": string
    }

    # Attempt to send log to server, if we cannot or network is not setup, append
    if network is None or not network.send_log_entry_to_server(log):
        log_list.append(log)


def print_sensor_data(sensor_data: AQData):
    print("Sensor Reading:", sensor_data.pm25, "pm25")


def flush_log():
    print("Attempting to Flush Log List")
    success = []
    for log in log_list:
        print("\tAttempting to send:", log)
        result = network.send_log_entry_to_server(log)
        if result == False:
            print("\tUnable to send log entry:", log)
        else:
            print("\tSent log entry", log)
            success.append(log)

    # Remove the entries that were successful
    for log in success:
        log_list.remove(log)


'''
Define variables and globals we will use throughout
'''
# Time between readings
delay = 60

# Defines led for testing
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Log list will hold a queue of logs to send to the server
log_list = []

# Config and network will be used globally, so declare here
config = None
network = None

'''
Main Execution 
'''
log_create(ServerLogType.INFO, ServerLogCode.DEVICE_POWER_ON, "Pico Powered On")
config = load_toml_config()
while config is None:
    report_error(Error.CONFIG_WIFI, "None config returned")
    config = load_toml_config()

# Initialize wifi, network, and sensor
connect_to_wifi()
network = Network(config)
flush_log()
sensor = Sensor()

# Read sensor and post data to server
while True:
    try:
        flash_led_active()
        connected = connect_to_wifi(False)
        if connected:
            print("Network is connected: ")
            data = sensor.read()
            print("Sensor data received:", data.pm25)
            print_sensor_data(data)
            network.send_sensor_data_to_server(data)

            # Make sure any log entries are sent
            flush_log()

            print("Attempting next reading in", delay, "seconds")
            time.sleep(delay)
        else:
            log_create(ServerLogType.INFO, ServerLogCode.WIFI_INITIAL_LOST, "Initial WiFi Lost - Recreating")
            network = Network(config)
    except Exception as e:
        log_create(ServerLogType.ERROR, ServerLogCode.GENERAL_EXCEPTION,
                   "An general exception occurred" + str(e) + type(e))
    except Error as e:
        log_create(ServerLogType.ERROR, ServerLogCode.GENERAL_EXCEPTION,
                   "An general exception occurred" + str(e) + type(e))
