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
 

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
pool = socketpool.SocketPool(wifi.radio)
print("connected to wifi")
requests = adafruit_requests.Session(pool, ssl.create_default_context())
#adafruit_requests.request(method: "post", url: "", json_data, float = 60)adafruit_requests.Session(pool, ssl.create_default_context())

reset_pin = None
uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
pm25 = PM25_UART(uart, reset_pin)

#  prints MAC address to REPL
print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])

#  prints IP address to REPL
print("My IP address is", wifi.radio.ipv4_address)


print("Found PM2.5 sensor, reading data...")

while True:
    time.sleep(1)

    try:
        print("Attempting pm25 read again...")
        aqdata = pm25.read()

    except Exception as e:
        print("Exception" + str(e) + ": retrying...")
        continue

    print()
    print("Concentration Units (standard)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
    )
    print("Concentration Units (environmental)")
    print("---------------------------------------")
    print(
        "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
        % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
    )
    print("---------------------------------------")
    print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
    print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
    print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
    print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
    print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
    print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
    print("---------------------------------------")

    try:
        time.sleep(1)
        json_data = {"sensor_id" : 11,
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
    except Exception:
        print("Unable to send data to server, will attempt on next reading")
    time.sleep(60)