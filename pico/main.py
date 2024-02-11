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
from micropython import const
import micropython


READINGS_DELAY_SECS = const(60)
SENSOR_READ_MAX_ATTEMPTS = const(500)
SENSOR_READ_ATTEMPT_DELAY = const(0)
WEB_API_REQUESTS_DELAY_SECS = const(1)
WEB_API_MAX_ATTEMPTS = const(5)
WIFI_CONNECT_ATTEMPT_DELAY = const(5)
WIFI_CONNECT_CHECK_DELAY = const(5)
LOG_QUEUE_MAX_SIZE = const(20)
# every MEM_REPORTING_FREQ readings, it will report memory status
MEM_REPORTING_FREQ = const(120)
WATCHDOG_TIMEOUT_MSEC = const(1000)

led = Pin("LED", Pin.OUT)


# Corresponds to server log types
# unsupported inheriting from `Enum` in micropython
class LogType:
    INFO = const("INFO")
    WARNING = const("WARNING")
    ERROR = const("ERROR")


# Corresponds to server log codes
# unsupported inheriting from `Enum` in micropython
class LogCode:
    WIFI_CONNECT_SUCCESS = const(30)
    WIFI_CONNECT_FAILED = const(4)
    WIFI_SOCKET_POOL_HUMAN_ERROR = const(5)
    WIFI_SOCKET_POOL_CREATION_ERROR = const(6)
    WIFI_REQUESTS_POTENTIAL_HUMAN_ERROR = const(7)
    WIFI_REQUESTS_CREATION_ERROR_UNDEFINED_POOL = const(8)
    WIFI_REQUESTS_CREATION_ERROR = const(9)
    SENSOR_UART_FAIL = const(10)
    SENSOR_PM25_CREATE_FAIL_NO_UART = const(11)
    SENSOR_PM25_CREATE_FAIL = const(12)
    SENSOR_PM25_UNDEFINED = const(13)
    SENSOR_PM25_READ_FAIL = const(14)
    DATA_POST_FAILED = const(16)
    DATA_POST_FAILED_MAX_RETRY = const(18)
    DEVICE_POWER_ON = const(31)
    WIFI_INITIAL_LOST = const(44)
    GENERAL_EXCEPTION = const(-9)
    MEMORY_STATUS = const(69)
    LOG_QUEUE_STATUS = const(32)


class Log:
    @micropython.native
    def __init__(self, type: str, code: int, message: str):
        self.type = type
        self.code = code
        self.message = message

    @micropython.native
    def __str__(self) -> str:
        return f'{self.type} ({self.code}): {self.message}'


class AQData:
    @micropython.native
    def __init__(self, pm10: str, pm25: str, pm100: str):
        self.pm10 = pm10
        self.pm25 = pm25
        self.pm100 = pm100


class WebApi:
    @micropython.native
    def __init__(self, client_key: str, log_url: str, data_url: str):
        self._client_key = client_key
        self._log_url = log_url
        self._data_url = data_url

    @micropython.native
    def send_log(self, log: Log) -> bool:
        return self._send_data(self._log_url, {
            'type': log.type,
            'code': log.code,
            'message': log.message
        })

    @micropython.native
    def send_aq(self, sensor_data: AQData) -> bool:
        json_data = {
            'pm25': sensor_data.pm25,
            'pm10': sensor_data.pm10,
            'pm100': sensor_data.pm100
        }
        return self._send_data(self._data_url, json_data)

    @micropython.native
    def _send_data(self, url: str, data: object):
        attempts = 1
        response = None  # intentional to cleanup if exception is thrown
        while attempts <= WEB_API_MAX_ATTEMPTS:
            try:
                gc.collect()  # server response might be large
                response = None
                response = urequests.post(url,
                                          headers={
                                              'Content-Type': 'application/json',
                                              'x-api-key': self._client_key
                                          },
                                          data=json.dumps(data))
                if response.status_code != 200:
                    Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED,
                                   f'[WebApi] Received unexpected response from server: {response.status_code}: {response.text}')
                    response.close()
                    attempts += 1
                else:
                    print(
                        f'[WebApi] Data sent to server, status code: {response.status_code}')
                    response.close()
                    return True
            except Exception as e:
                if response is not None:
                    response.close()
                Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED,
                               f'[WebApi] Exception in sending data to server. Exception: {e}')
                print(
                    f'[WebApi] Exception occurred in sending data to server: {type(e)}: {e}')
                attempts += 1

            time.sleep(WEB_API_REQUESTS_DELAY_SECS)

        print('[WebApi] Max retry of sending reached')
        Logger().queue(LogType.ERROR, LogCode.DATA_POST_FAILED_MAX_RETRY,
                       '[WebApi] Max Retry Reached in Sending Data')
        return False


class Logger:
    # Logger | None (unsupported `from __future__ import annotations` in micropython)
    _instance = None

    @micropython.native
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    @micropython.native
    def _init(self):
        self._log_queue: list[Log] = []

    @micropython.native
    def queue(self, type: str, code: int, message: str):
        if len(self._log_queue) >= LOG_QUEUE_MAX_SIZE:
            print(f'[Logger] Unable to queue log. Queue full')
            self._log_queue[len(self._log_queue) - 1] = \
                Log(LogType.WARNING, LogCode.LOG_QUEUE_STATUS,
                    "[Logger] Log Queue Full. Truncating new logs")
        else:
            log = Log(type, code, message)
            self._log_queue.append(log)
            print(f'[Logger] Queued log type: {type}, code: {code}')

    @micropython.native
    def flush_to_server(self, api: WebApi):
        print(f'[Logger] Flushing {len(self._log_queue)} logs to server...')
        sent = []
        for log in self._log_queue:
            result = api.send_log(log)
            if result == False:
                print(
                    f'[Logger] Failed to send log type: {log.type}, code: {log.code}')
            else:
                print(f'[Logger] Sent log type: {log.type}, code: {log.code}')
                sent.append(log)

        for log in sent:
            self._log_queue.remove(log)

        gc.collect()  # removing logs frees up memory


# unsupported inheriting from `Enum` in micropython
class ClientError:
    CONFIG_GENERIC = const(1)
    CONFIG_WIFI = const(2)
    CONFIG_ENDPOINT = const(3)
    WIFI_FAILURE = const(4)


class ClientConfig:
    @micropython.native
    def __init__(self, wifi_ssid: str, wifi_pass: str, data_url: str, log_url: str, client_key: str):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.data_url = data_url
        self.log_url = log_url
        self.client_key = client_key


@micropython.native
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
    @micropython.native
    def __init__(self):
        self._buffer = bytearray(32)
        self._uart = UART(0)

        self._uart.init(baudrate=9600, bits=8, parity=None,
                        stop=1, tx=Pin(0), rx=Pin(1))

    @micropython.native
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

        for attempt in range(1, SENSOR_READ_MAX_ATTEMPTS):
            print(
                f'[Sensor] Attempt {attempt}/{SENSOR_READ_MAX_ATTEMPTS} to read from sensor...')
            time.sleep(SENSOR_READ_ATTEMPT_DELAY)
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
                print(f'[Sensor] Exception reading sensor: {e}: retrying...')

        Logger().queue(LogType.ERROR, LogCode.SENSOR_PM25_READ_FAIL,
                       f'[Sensor] PM25 Read Failure: Reached Max Retry Count: {SENSOR_READ_MAX_ATTEMPTS}')


class Wifi:
    # Wifi | None (unsupported `from __future__ import annotations` in micropython)
    _instance = None

    @micropython.native
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Wifi, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    @micropython.native
    def _init(self):
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)

    @micropython.native
    def connect(self, ssid: str, password: str) -> None:
        print(f'[Wifi] Attempting to Connect to SSID: {ssid}')

        mac_address = ubinascii.hexlify(network.WLAN(
            network.STA_IF).config('mac'), ':').decode()
        self._wlan.disconnect()
        self._wlan.connect(ssid, password)

        attempt_count = 1
        while True:
            print(
                f'[Wifi] Attempt {attempt_count} to connect')
            self._wlan.connect(ssid, password)
            print(
                f'[Wifi] Waiting {WIFI_CONNECT_CHECK_DELAY} secs to establish before checking connection status...')
            time.sleep(WIFI_CONNECT_CHECK_DELAY)
            if self._wlan.status() == network.STAT_GOT_IP:
                ip = self._wlan.ifconfig()[0]
                Logger().queue(LogType.INFO, LogCode.WIFI_CONNECT_SUCCESS,
                               f'[Wifi] Successfully Connected to the wifi. Mac: {mac_address} IP: {ip} | Attempt: {attempt_count}')
                return
            print("[Wifi] Connection not established, retrying...")
            time.sleep(WIFI_CONNECT_ATTEMPT_DELAY)
            attempt_count += 1

    @micropython.native
    def connected(self) -> bool:
        return self._wlan.status() == network.STAT_GOT_IP


@micropython.native
def flash_led_error(blinks: int):
    for _ in range(blinks):
        led.on()
        time.sleep(0.5)
        led.off()
        time.sleep(0.5)

    time.sleep(5)


# TODO: This seems to overlap with error blinking
@micropython.native
def flash_led_active():
    for _ in range(2):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)


@micropython.native
def halt_client_error(client_error: int, label: str):
    print(f'[Client] Error type: {client_error}: {label}')
    while True:
        flash_led_error(client_error)


@micropython.native
def load_client_config() -> ClientConfig:  # type: ignore (Returns or halts)
    try:
        with open("config.json") as fd:
            config_data = json.load(fd)
            config = ClientConfig(config_data["wifi_ssid"],
                                  config_data["wifi_pass"],
                                  config_data["data_url"],
                                  config_data["log_url"],
                                  config_data["client_key"])
            if config.wifi_ssid is None or config.wifi_pass is None:
                halt_client_error(ClientError.CONFIG_WIFI,
                                  "Wifi config missing from toml configuration.")
            elif config.data_url is None or config.log_url is None or config.client_key is None:
                halt_client_error(ClientError.CONFIG_ENDPOINT,
                                  "Endpoint config missing from toml configuration.")
            return config
    except:
        halt_client_error(ClientError.CONFIG_GENERIC, "Error with config")


@micropython.native
def main():
    # TODO: watchdog

    led.on()

    Logger().queue(LogType.INFO, LogCode.DEVICE_POWER_ON,
                   "[Main] Pico Powered On")
    config = load_client_config()

    Wifi().connect(config.wifi_ssid, config.wifi_pass)

    api = WebApi(config.client_key, config.log_url, config.data_url)
    Logger().flush_to_server(api)

    while True:
        try:
            sensor = Sensor()
            break
        except Exception as e:
            Logger().queue(LogType.ERROR,
                           LogCode.SENSOR_UART_FAIL,    # TODO: Not quite the right category
                           f'[Main] {type(e).__name__}: {e} | Trying again...')
            time.sleep(5)

    loop_count = 0
    # Read sensor and post data to server
    while True:
        try:
            gc.collect()
            if loop_count % MEM_REPORTING_FREQ == 0:
                Logger().queue(LogType.INFO, LogCode.MEMORY_STATUS,
                               f'[Main] Free RAM: {gc.mem_free()} bytes')
                Logger().flush_to_server(api)

            loop_count += 1
            flash_led_active()

            connected = Wifi().connected()
            if not connected:
                Logger().queue(LogType.INFO, LogCode.WIFI_INITIAL_LOST,
                               "[Main] Initial WiFi Lost - Reconnecting")
                Wifi().connect(config.wifi_ssid, config.wifi_pass)

            data = sensor.read()
            if data is None:
                print("[Main] No sensor data was returned")
            else:
                print(f'[Main] Sensor data received: {data.pm25} pm25')
                api.send_aq(data)

            Logger().flush_to_server(api)

            print(
                f'[Main] Attempting next reading in {READINGS_DELAY_SECS} secs')
            time.sleep(READINGS_DELAY_SECS)
        except MemoryError:
            while True:
                led.on()
                time.sleep(0.1)
                led.off()
                time.sleep(0.1)
        except Exception as e:
            Logger().queue(LogType.ERROR, LogCode.GENERAL_EXCEPTION,
                           f'[Main] {type(e)}: {e}')
            Logger().flush_to_server(api)
            time.sleep(READINGS_DELAY_SECS)


main()
