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

def report_config_error(type):
    print(type, "Configuration missing from toml configuration file, please make sure these are configured first.")
    sys.exit(1)

# Get configuration variables from settings.toml file
wifi_ssid = os.getenv("WIFI_SSID")
wifi_pass = os.getenv("WIFI_PASSWORD")

data_endpoint_url = os.getenv("DATA_ENDPOINT_URL")
log_endpoint_url = os.getenv("LOG_ENDPOINT_URL")
client_key = os.getenv("CLIENT_KEY")

max_pm_retry = 50

if wifi_ssid == None or wifi_pass == None:
    report_config_error("WiFi")
elif data_endpoint_url == None or log_endpoint_url == None or client_key == None:
    report_config_error("Client")

# Defines led for testing
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Log list that will append all logs that were unsuccessful in posting
log_list = []

# Count variable that keeps track on the amount of times wifi tried to reconnect
wifi_reconnect_count = 0

# API Key and headers
headers = {
    "Content-Type": "application/json",
    "x-api-key": client_key
}

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

def handle_wifi_connection(count = 0, max_attempts = 5, delay = 1):
    """
    Connect to WiFi Network using the SSID and password retrieved from setting.toml.
    """
    print("Attempting to Connect to SSID:", wifi_ssid)
    attempts = 0
    
    while attempts < max_attempts:
        try:
            wifi.radio.connect(wifi_ssid, wifi_pass)
            log_create("INFO", 30, "Successfully Connected to the wifi | Count: " + str(count))
            break # Break of the loop if connection is successful
        except (ValueError, TypeError, RuntimeError, SyntaxError, KeyError, ConnectionError) as e:
            print(type(e).__name__, ":", str(e))
            log_create("ERROR", 3, type(e).__name__ + ": " + str(e))
            report_config_error("Client Misconfig")
            break # Break of the loop if connection is successful
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying connection, Attempt:", str(attempts + 1))
            log_create("ERROR", 4, type(e).__name__ + ": " + str(e))
            attempts += 1
            time.sleep(delay)
    else:
        print("Failed to Connect to WiFi")
        
def handle_socketpool(max_attempts = 5, delay = 1):
    """
    Creates a socket pool for managing sockets using the provided WiFi radio object.
    """
    global pool
    attempts = 0
    
    while attempts < max_attempts:
        try:
            pool = socketpool.SocketPool(wifi.radio)
            break # Break of the loop if initialization is successful
        except (AttributeError, ValueError, TypeError, RuntimeError, SyntaxError) as e:
            print(type(e).__name__, ":", str(e))
            print("Potential human error")
            log_create("ERROR", 5, type(e).__name__ + ": " + str(e))
            break # Break of the loop if connection is successful
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying Pool Creation, Attempt:", str(attempts + 1))
            log_create("ERROR", 6, type(e).__name__ + ": " + str(e))
            attempts += 1
            time.sleep(delay)
    else:
        print("Failed Pool Creation")
        
def handle_requests_session(max_attempts = 5, delay = 1):
    """
    Create an Adafruit Requests session with the provided socket pool and SSL context.
    """
    global requests
    attempts = 0
    
    while attempts < max_attempts:
        try:
            requests = adafruit_requests.Session(pool, ssl.create_default_context())
            break # Break of the loop if initialization is successful
        except (AttributeError, ValueError, TypeError, RuntimeError) as e:
            print(type(e).__name__, ":", str(e))
            print("Potential human error")
            log_create("ERROR", 7, type(e).__name__ + ": " + str(e))
            break # Break of the loop if connection is successful
        except NameError as e:
            print("NameError:", str(e))
            log_create("ERROR", 8, type(e).__name__ + ": " + str(e))
            handle_socketpool()
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying Session Creation, Attempt:", str(attempts + 1))
            log_create("ERROR", 9, type(e).__name__ + ": " + str(e))
            attempts += 1
            time.sleep(delay)
    else:
        print("Failed Session Creation")

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
    
def log_create(log_type, code, string):
    log = {
        "type": log_type, #"INFO" | "WARNING" | "ERROR"
        "code": code, 
        "message": string
    }
    
    try:
        r = requests.post(log_endpoint_url, json=log, headers=headers)
        if (int(r.status_code) != 200):
            #print("Error - Response from server: ", r.status_code, r.text)
            print("Failed to post log, temporarily adding to log list")
            log_list.append(log)
        else:
            #print("Success - Response from server: ", r.status_code, r.text)
            print("Log successfully posted")
    except Exception as e:
        print("Failed to post log, temporarily adding to log list")
        log_list.append(log)
        
def post_log_list():
    if not log_list:
        pass # List was empty
    else:
        try:
            for i in log_list:
                r = requests.post(log_endpoint_url, json=i, headers=headers)
                if (int(r.status_code) != 200):
                    #print("Error - Response from server: ", r.status_code, r.text)
                    print("Could not post log_list. Try again later")
                else:
                    #print("Successfully Posted Log - Response from server: ", r.status_code, r.text)
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
#adafruit_requests.request(method: "post", url: "", json_data, float = 60)adafruit_requests.Session(pool, ssl.create_default_context())

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
            log_create("ERROR", 14, type(e).__name__ + ": " + str(e) + " | Retry Count: " + retry_count)
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
                         "pm10" : aqdata["pm10 env"],
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
            break # Break of the loop if connection is successful
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