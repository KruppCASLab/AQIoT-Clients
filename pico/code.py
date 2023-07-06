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
    print(type, "configuration missing from toml configuration file, please make sure these are configured first.")
    sys.exit(1)

# Get configuration variables from settings.toml file
wifi_ssid = os.getenv("WIFI_SSID")
wifi_pass = os.getenv("WIFI_PASSWORD")

client_id = os.getenv("CLIENT_ID")
client_key = os.getenv("CLIENT_KEY")

if wifi_ssid == None or wifi_pass == None:
    report_config_error("WiFi")
elif client_id == None or client_key == None:
    report_config_error("Client")
    
print("Sensor Client Id:", client_id)

# Defines led for testing
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

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

def handle_wifi_connection(max_attempts = 5, delay = 1):
    """
    Connect to WiFi Network using the SSID and password retrieved from setting.toml.
    """
    print("Attempting to Connect to SSID:", wifi_ssid)
    attempts = 0
    
    while attempts < max_attempts:
        try:
            wifi.radio.connect(wifi_ssid, wifi_pass)
            break # Break of the loop if connection is successful
        except (AttributeError, ValueError, TypeError, RuntimeError, SyntaxError, KeyError) as e:
            print(type(e).__name__, ":", str(e))
            report_config_error("Client Misconfig")
            break # Break of the loop if connection is successful
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying connection, Attempt:", str(attempts + 1))
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
            pool = socketpool.SocketPool(wifi.radio)
            break # Break of the loop if connection is successful
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying Pool Creation, Attempt:", str(attempts + 1))
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
            requests = adafruit_requests.Session(pool, ssl.create_default_context())
            break # Break of the loop if connection is successful
        except NameError as e:
            print("NameError:", str(e))
            handle_socketpool()
        except Exception as e:
            print("Caught", type(e).__name__, ":", str(e))
            print("Retrying Session Creation, Attempt:", str(attempts + 1))
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
        uart = busio.UART(board.GP0, board.GP1, baudrate=9600)

def handle_pm25():
    """
    Initialize the PM2.5 sensor connected via UART and handles possible exceptions.
    """
    global pm25
    
    try:
        pm25 = PM25_UART(uart, reset_pin)
    except NameError as e:
        print("NameError:", str(e))
        handle_uart()
    except Exception as e:
        print("Caught", type(e).__name__, ":", str(e))
        pm25 = PM25_UART(uart, reset_pin)

handle_wifi_connection()
handle_socketpool()
print("Connection to WiFi", wifi_ssid, "Success!")
handle_requests_session()
#adafruit_requests.request(method: "post", url: "", json_data, float = 60)adafruit_requests.Session(pool, ssl.create_default_context())

reset_pin = None
handle_uart()
handle_pm25()

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

while True:
    time.sleep(1)

    try:
        print("Attempting pm25 read again...")
        aqdata = pm25.read()
    except NameError as e:
        print("NameError:", str(e))
        handle_pm25()
    except Exception as e:
        print("Exception: " + str(e) + ": retrying...")
        continue

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
            json_data = {"sensor_id" : client_id,
                         "pm25": aqdata["pm25 env"],
                         "pm1" : aqdata["pm10 env"],
                         "pm10": aqdata["pm100 env"]
                         }
            print("trying to send JSON post request")
            r = requests.post('https://mopsdev.bw.edu/~bkrupp/aq/postreading.php', json=json_data)   
            if (int(r.status_code) != 200):
                print("Error - Response from server: ", r.status_code, r.text)
            else:
                print("Success - Response from server: ", r.status_code, r.text)
            check_if_running()
            break # Break of the loop if connection is successful
        except Exception as e:
            print("Unable to send data to server, will attempt on next reading. Error:",str(e))
            attempts += 1
            time.sleep(3)
    time.sleep(60)

