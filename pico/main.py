"""
MicroPython Version of Pico AQ Sensor
MicroPython defaults to main.py
"""
import json
import struct
import time
import network
import ubinascii
import urequests
import gc
from machine import Pin, UART


READINGS_DELAY_SECS = 60
SENSOR_READ_MAX_ATTEMPTS = 50
WEB_API_REQUESTS_DELAY_SECS = 1
WEB_API_MAX_ATTEMPTS = 5
WIFI_CONNECT_MAX_ATTEMPTS = 25

led = Pin("LED", Pin.OUT)  # TODO: string for pin id?


# Corresponds to server log types
# unsupported inheriting from `Enum` in micropython
class LogType:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Corresponds to server log codes
# unsupported inheriting from `Enum` in micropython
class LogCode:
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
    FREE_MEMORY_STATUS = 69


class Log:
    def __init__(self, type: str, code: int, message: str):
        self.type = type
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f'{self.type} ({self.code}): {self.message}'


class AQData:
    def __init__(self, pm10: str, pm25: str, pm100: str):
        self.pm10 = pm10
        self.pm25 = pm25
        self.pm100 = pm100


class WebAPI:
    def __init__(self, client_key: str, log_url: str, data_url: str):
        self._client_key = client_key
        self._log_url = log_url
        self._data_url = data_url

    def send_log(self, log: Log) -> bool:
        return self._send_data(self._log_url, {
            'type': log.type,
            'code': log.code,
            'message': log.message
        })

    def send_aq(self, sensor_data: AQData) -> bool:
        json_data = {
            'pm25': sensor_data.pm25,
            'pm10': sensor_data.pm10,
            'pm100': sensor_data.pm100
        }
        return self._send_data(self._data_url, json_data)

    def _send_data(self, url: str, data: object):
        attempts = 1
        while attempts <= WEB_API_MAX_ATTEMPTS:
            try:
                response = urequests.post(url,
                                          headers={
                                              'Content-Type': 'application/json',
                                              'x-api-key': self._client_key
                                          },
                                          data=json.dumps(data))
                if int(response.status_code) != 200:
                    # TODO: Blink failure
                    Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED,
                                   f'Error: Received unexpected response from server: {response.status_code}: {response.text}')
                    response.close()
                else:
                    # TODO: Blink success
                    print(
                        f'Success: Data sent to server: {response.status_code}')
                    response.close()
                    return True
            except RuntimeError as re:
                Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED,
                               f'Error: Timeout in sending data to server. Exception: {re}')
                attempts += 1
            except Exception as e:
                Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED,
                               f'Error: Exception in sending data to server. Exception: {e}')
                print(
                    f'Exception occurred in sending data to server: {type(e)}: {e}')
                attempts += 1

            attempts += 1
            time.sleep(WEB_API_REQUESTS_DELAY_SECS)

        print('Max retry of sending reached')
        Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED_MAX_RETRY,
                       'Error: Max Retry Reached in Sending Data')
        return False

    def is_connected(self, wlan: network.WLAN):
        return wlan.status() == network.STAT_GOT_IP


class Logger:
    # Logger | None (unsupported `from __future__ import annotations` in micropython)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._log_queue: list[Log] = []

    def queue(self, type: str, code: int, message: str):
        log = Log(type, code, message)
        print(f'Queued log: {log}')
        self._log_queue.append(log)

    def flush_to_server(self, api: WebAPI):
        print("Flushing logs to server...")
        sent = []
        for log in self._log_queue:
            print("\tSending:", log)
            result = api.send_log(log)
            if result == False:
                print(f'\tFailed to send: {log}')
            else:
                print(f'\tSent: {log}')
                sent.append(log)

        # Remove the entries that were successful
        for log in sent:
            self._log_queue.remove(log)

# unsupported inheriting from `Enum` in micropython


class ClientError:
    CONFIG_WIFI = 1
    CONFIG_ENDPOINT = 2
    WIFI_FAILURE = 3


class ClientConfig:
    def __init__(self, wifi_ssid: str, wifi_pass: str, data_url: str, log_url: str, client_key: str):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


def network_status_str(value: int) -> str:
    # unsupported `match` in micropython
    if value == network.STAT_IDLE:
        return "Idle"
    elif value == network.STAT_CONNECTING:
        return "Connecting"
    elif value == network.STAT_WRONG_PASSWORD:
        return "Failed due to incorrect password"
    elif value == network.STAT_NO_AP_FOUND:
        return "Failed due to no access point"
    elif value == network.STAT_CONNECT_FAIL:
        return "Failed (generic)"
    else:
        return "Unknown"


class Sensor:
    def __init__(self):
        self._buffer = bytearray(32)
        self._uart = UART(0)
        self._delay_between_attempts = 1

        self._uart.init(baudrate=9600, bits=8, parity=None,
                        stop=1, tx=Pin(0), rx=Pin(1))

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

        for _ in range(0, SENSOR_READ_MAX_ATTEMPTS):
            time.sleep(self._delay_between_attempts)
            try:
                byte = self._uart.read(1)
                # If we did not get a byte or it doesn't match the header, continue to read
                if not byte or byte[0] != 0x42:
                    continue

                # Save the byte and read the remaining
                self._buffer[0] = byte[0]
                remaining_bytes = self._uart.read(31)

                # If we don't have any remaining bytes, or our length is not 31 (not a full message), continue
                if not remaining_bytes or len(remaining_bytes) != 31:
                    continue

                # If we get this far, we have a full message, unpack
                self._buffer[1:] = remaining_bytes
                frame_len = struct.unpack(">H", self._buffer[2:4])[0]

                # Check for invalid frame length
                if frame_len != 28:
                    continue

                '''
                The > is big endian
                H is for unsigned short
                https://docs.python.org/3.0/library/struct.html
                '''

                provided_checksum = struct.unpack(">H", self._buffer[30:32])[0]
                computed_checksum = sum(self._buffer[0:30])

                # If checksum does not match, continue
                if computed_checksum != provided_checksum:
                    continue

                # If we get this far, we have a valid frame length and checksum, unpack data and return
                (
                    reading['pm10 standard'],
                    reading['pm25 standard'],
                    reading['pm100 standard'],
                    reading['pm10 env'],
                    reading['pm25 env'],
                    reading['pm100 env'],
                    reading['particles 03um'],
                    reading['particles 05um'],
                    reading['particles 10um'],
                    reading['particles 25um'],
                    reading['particles 50um'],
                    reading['particles 100um'],
                ) = struct.unpack(">HHHHHHHHHHHH", self._buffer[4:28])

                return AQData(reading["pm10 env"], reading["pm25 env"], reading["pm100 env"])

            except Exception as e:
                print(f'Exception reading sensor: {e}: retrying...')
                time.sleep(self._delay_between_attempts)

        Logger().queue(LogType.ERROR, LogCode.SENSOR_PM25_READ_FAIL,
                       f'PM25 Read Failure: Reached Max Retry Count: {SENSOR_READ_MAX_ATTEMPTS}')


def connect_to_wifi(config: ClientConfig, wlan: network.WLAN, is_initial=True):
    attempts = 1
    delay = 1

    if config == None:
        client_error(ClientError.CONFIG_WIFI, "Config is None")
        return

    print(f'Attempting to Connect to SSID: {config.wifi_ssid}')

    mac_address = ubinascii.hexlify(network.WLAN(
        network.STA_IF).config('mac'), ':').decode()
    wlan.disconnect()
    wlan.connect(config.wifi_ssid, config.wifi_pass)

    while attempts <= WIFI_CONNECT_MAX_ATTEMPTS:
        if wlan.status() == network.STAT_GOT_IP:
            break
        # TODO: check if this prints right
        print(
            f'\tRetrying connection, Attempt: {attempts} WLAN Status: {network_status_str(wlan.status())}')
        attempts += 1
        time.sleep(delay)

    if wlan.status() == network.STAT_GOT_IP:
        ip = wlan.ifconfig()[0]
        if is_initial:
            Logger().queue(LogType.INFO, LogCode.WIFI_CONNECT_SUCCESS,
                           f'Successfully Connected to the wifi. Mac: {mac_address} IP: {ip} | Attempt: {attempts}')
        return True

    else:
        if is_initial:
            client_error(ClientError.WIFI_FAILURE,
                         "Unable to make initial connection to WiFi")
        elif attempts == WIFI_CONNECT_MAX_ATTEMPTS:
            Logger().queue(LogType.ERROR, LogCode.WIFI_CONNECT_FAILED,
                           f'Unable to connect to wifi after max attempts {attempts}')
        else:
            Logger().queue(LogType.ERROR, LogCode.WIFI_CONNECT_FAILED,
                           f'Unable to connect to wifi wlan_status: {wlan.status()}: {network_status_str(wlan.status())}')
        return False


def flash_led_error(error_type: int):
    n_blinks = 0
    if error_type == ClientError.CONFIG_WIFI:
        n_blinks = 1
    elif error_type == ClientError.CONFIG_ENDPOINT:
        n_blinks = 2
    elif error_type == ClientError.WIFI_FAILURE:
        n_blinks = 3

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


def client_error(client_error: int, label: str):
    print(f'Error type: {client_error}: {label}')
    for _ in range(5):
        flash_led_error(client_error)


def load_client_config() -> ClientConfig | None:
    try:
        with open("config.json") as fd:
            config_data = json.load(fd)
            config = ClientConfig(config_data["wifi_ssid"],
                                  config_data["wifi_pass"],
                                  config_data["data_url"],
                                  config_data["log_url"],
                                  config_data["client_key"])
            if config.wifi_ssid is None or config.wifi_pass is None:
                client_error(ClientError.CONFIG_WIFI,
                             "WiFi config missing from toml configuration.")
                return None
            elif config.data_url is None or config.log_url is None or config.client_key is None:
                client_error(ClientError.CONFIG_ENDPOINT,
                             "Endpoint config missing from toml configuration.")
                return None

            return config
    except:
        return None


def main():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    led.on()

    Logger().queue(LogType.INFO, LogCode.DEVICE_POWER_ON, "Pico Powered On")
    config = load_client_config()
    while config is None:
        client_error(ClientError.CONFIG_WIFI, "Config is None")
        config = load_client_config()

    # Initialize wifi, network, and sensor
    while True:
        connect_success = connect_to_wifi(config, wlan)
        if connect_success:
            break

    api = WebAPI(config.client_key, config.log_url, config.data_url)
    Logger().flush_to_server(api)

    while True:
        try:
            sensor = Sensor()
            break
        except Exception as e:
            Logger().queue(LogType.ERROR,
                           LogCode.SENSOR_UART_FAIL,    # TODO: Not quite the right category
                           f'{type(e).__name__}: {e} | Trying again...')
            time.sleep(5)

    loop_count = 0
    # Read sensor and post data to server
    while True:
        try:
            if loop_count % 120 == 0:
                gc.collect()
                Logger().queue(LogType.INFO, LogCode.FREE_MEMORY_STATUS,
                               f'Free RAM: {gc.mem_free()} bytes')
                Logger().flush_to_server(api)
            loop_count += 1
            flash_led_active()
            connected = connect_to_wifi(config, wlan, False)
            if connected:
                print(
                    f'Network is connected: WLAN Status: {network_status_str(wlan.status())}')
                data = sensor.read()
                if data is None:
                    print("No sensor data was returned")
                    continue
                print(f'Sensor data received: {data.pm25}')
                api.send_aq(data)

                Logger().flush_to_server(api)

                print(f'Attempting next reading in {READINGS_DELAY_SECS} secs')
                time.sleep(READINGS_DELAY_SECS)
            else:
                Logger().queue(LogType.INFO, LogCode.WIFI_INITIAL_LOST,
                               "Initial WiFi Lost - Reconnecting")
                api = WebAPI(config.client_key,
                             config.log_url, config.data_url)
        except MemoryError:
            while True:
                led.on()
                time.sleep(0.1)
                led.off()
                time.sleep(0.1)
        except Exception as e:
            Logger().queue(LogType.ERROR, LogCode.GENERAL_EXCEPTION,
                           f'{type(e)}: {e}')


main()
