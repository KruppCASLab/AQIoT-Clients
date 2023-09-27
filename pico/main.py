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


class Config:
    def __init__(self, wifi_ssid: string, wifi_pass: string, data_url: string, log_url: string, client_key: string):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.client_key
        }


def flash_led(error_type: int):
    for i in range(error_type):
        led.value = True
        time.sleep(1)
        led.value = False
        time.sleep(1)
    time.sleep(3)  # Circuit python has 5-second delay between errors, must not use 5 as value


def report_exit_error(error_type, label):
    print("Error type:", error_type, label)
    while True:
        flash_led(error_type)


def load_toml_config():
    # Get configuration variables from settings.toml file
    wifi_ssid = os.getenv("WIFI_SSID")
    wifi_pass = os.getenv("WIFI_PASSWORD")

    data_endpoint_url = os.getenv("DATA_ENDPOINT_URL")
    log_endpoint_url = os.getenv("LOG_ENDPOINT_URL")
    client_key = os.getenv("CLIENT_KEY")

    if wifi_ssid is None or wifi_pass is None:
        report_exit_error(Error.CONFIG_WIFI, "WiFi config missing from toml configuration.")
    elif data_endpoint_url is None or log_endpoint_url is None or client_key is None:
        report_exit_error(Error.CONFIG_ENDPOINT, "Endpoint config missing from toml configuration.")

    config = Config(wifi_ssid, wifi_pass, data_endpoint_url, log_endpoint_url, client_key)

    return config


def connect_to_wifi():
    attempts = 1
    delay = 1
    max_attempts = 25

    print("Attempting to Connect to SSID:", config.wifi_ssid)

    while attempts <= max_attempts:
        try:
            wifi.radio.connect(config.wifi_ssid, config.wifi_pass)
            log_create(ServerLogType.INFO, ServerLogCode.WIFI_CONNECT_SUCCESS,
                       "Successfully Connected to the wifi | Attempt: " + str(attempts))
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
        report_exit_error(Error.WIFI_FAILURE, "Failed to Connect to WiFi")


def initialize_socket_pool():
    global socketpool

    delay = 1
    attempts = 1
    max_attempts = 5

    while attempts < max_attempts:
        try:
            socketpool = socketpool.SocketPool(wifi.radio)
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
            time.sleep(delay)
    else:
        print("Failed Pool Creation")


def initialize_requests():
    global requests

    delay = 1
    attempts = 1
    max_attempts = 5

    while attempts <= max_attempts:
        try:
            requests = adafruit_requests.Session(pool, ssl.create_default_context())
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
            time.sleep(delay)
    else:
        print("Failed Session Creation")


def log_create(log_type, code, string):
    print("Log Created", log_type, code, string)
    log = {
        "type": log_type,  # "INFO" | "WARNING" | "ERROR"
        "code": code,
        "message": string
    }

    try:
        request = requests.post(config.log_url, json=log, headers=config.headers)
        if int(request.status_code) != 200:
            # TODO: Blink failure
            print("Error - Response from server: ", r.status_code, r.text)
            print("Failed to post log, temporarily adding to log list")
            log_list.append(log)
        else:
            # TODO: Blink success
            print("Log successfully posted")
    except Exception as e:
        print("Exception occurred:", e, "Will add to log to report.")
        log_list.append(log)


'''
Define variables and globals we will use throughout
'''
# Defines led for testing
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Log list will hold a queue of logs to send to the server
log_list = []

'''
Main Execution 
'''
config = load_toml_config()

connect_to_wifi()
initialize_socket_pool()
initialize_requests()

sys.exit(1)

max_pm_retry = 50

# Log list that will append all logs that were unsuccessful in posting


# Count variable that keeps track on the amount of times wifi tried to reconnect
wifi_reconnect_count = 0


# API Key and headers


def check_if_running():
    """
    Will blink on and off continuously for 2 seconds after the initial handling functions are successful and then at
    the end of each response from the server after posting the json

    This will allow us to see whether the code is running properly from the pico's led alone
    """
    times = 0
    while times < 5:
        led.value = True
        time.sleep(0.2)
        led.value = False
        time.sleep(0.2)
        times += 1


def handle_uart():
    """
    Create UART object by defining the pins and baudrate and handles possible exceptions.
    """
    global uart

    try:
        uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
    except Exception as e:
        print("Caught", type(e).__name__, ":", str(e))
        log_create("ERROR", 10, type(e).__name__ + ": " + str(e))


def handle_pm25():
    """
    Initialize the PM2.5 sensor connected via UART and handles possible exceptions.
    """
    global pm25

    try:
        pm25 = PM25_UART(uart, reset_pin)
    except NameError as e:
        print("NameError:", str(e))
        log_create("ERROR", 11, type(e).__name__ + ": " + str(e))
        handle_uart()
    except Exception as e:
        print("Caught", type(e).__name__, ":", str(e))
        log_create("ERROR", 12, type(e).__name__ + ": " + str(e))


def reset_wifi_and_sensor(count):
    # Recall all handling functions
    handle_wifi_connection(count)
    handle_socketpool()
    handle_requests_session()

    print("Finished reinitialization variables and recalling functions")

    time.sleep(2)


def post_log_list():
    if not log_list:
        pass  # List was empty
    else:
        try:
            for i in log_list:
                r = requests.post(log_endpoint_url, json=i, headers=headers)
                if (int(r.status_code) != 200):
                    # print("Error - Response from server: ", r.status_code, r.text)
                    print("Could not post log_list. Try again later")
                else:
                    # print("Successfully Posted Log - Response from server: ", r.status_code, r.text)
                    print("Successfully posted log from log list")
                    log_list.remove(i)
        except Exception as e:
            print("Could not post log_list. Try again later")


log_create("INFO", 31, "Pico Powered on")
handle_wifi_connection()
handle_socketpool()
print("Connection to WiFi", wifi_ssid, "Success!")
handle_requests_session()
post_log_list()
# adafruit_requests.request(method: "post", url: "", json_data, float = 60)adafruit_requests.Session(pool, ssl.create_default_context())

reset_pin = None
handle_uart()
handle_pm25()
post_log_list()

#  prints MAC address to REPL
try:
    print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])
except Exception as e:
    print("Error printing MAC address:", str(e))

#  prints IP address to REPL
try:
    print("My IP address is", wifi.radio.ipv4_address)
except Exception as e:
    print("Error printing IP address:", str(e))

print("Found PM2.5 sensor, reading data...")

check_if_running()

retry_count = 0

while True:
    time.sleep(1)

    try:
        print("Attempting pm25 read again...")
        aqdata = pm25.read()
    except NameError as e:
        print("NameError:", str(e))
        log_create("ERROR", 13, type(e).__name__ + ": " + str(e))
        handle_pm25()
    except Exception as e:
        retry_count = retry_count + 1
        print("Exception: " + str(e) + ": retrying...")
        if retry_count >= max_pm_retry:
            log_create("ERROR", 14, type(e).__name__ + ": " + str(e) + " | Retry Count: " + str(retry_count))
            retry_count = 0
        continue

    # Reset retry on success
    retry_count = 0

    print()
    print("Concentration Units (standard)")
    print("---------------------------------------")
    try:
        print(
            "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
            % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
        )
    except Exception as e:
        print("Failed to print Standard Concentration Units")
    print("Concentration Units (environmental)")
    print("---------------------------------------")
    try:
        print(
            "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
            % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
        )
    except Exception as e:
        print("Failed to print Environmental Concentration Units")
    print("---------------------------------------")
    try:
        print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
        print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
        print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
        print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
        print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
        print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
    except Exception as e:
        print("Failed to print Particle Amounts")
    print("---------------------------------------")

    attempts = 0

    while attempts < 5:
        try:
            time.sleep(1)
            json_data = {"pm25": aqdata["pm25 env"],
                         "pm10": aqdata["pm10 env"],
                         "pm100": aqdata["pm100 env"]
                         }
            print("trying to send JSON post request")
            print("Sending data to", data_endpoint_url)
            print(json_data)
            r = requests.post(data_endpoint_url, json=json_data, headers=headers)
            if (int(r.status_code) != 200):
                print("Error - Response from server: ", r.status_code, r.text)
            else:
                print("Success - Response from server: ", r.status_code, r.text)
            check_if_running()
            break  # Break of the loop if connection is successful
        except RuntimeError as e:
            print(type(e).__name__, ":", str(e))
            log_create("ERROR", 16, type(e).__name__ + ": " + str(e))
            if attempts == 4:
                print("Reached 5 attempts, resetting wifi and sensor variables")
                wifi_reconnect_count += 1
                reset_wifi_and_sensor(wifi_reconnect_count)
            attempts += 1
            time.sleep(1)
        except Exception as e:
            print("Unable to send data to server, will attempt on next reading.", type(e).__name__, ":", str(e))
            log_create("ERROR", 17, type(e).__name__ + ": " + str(e))
            if attempts == 4:
                print("Reached 5 attempts, resetting wifi and sensor variables")
                wifi_reconnect_count += 1
                reset_wifi_and_sensor(wifi_reconnect_count)
            attempts += 1
            time.sleep(3)
    post_log_list()
    time.sleep(60)
