"""
MicroPython Version of Pico AQ Sensor
MicroPython defaults to main.py
"""

import time
import network
import urequests
import ubinascii
from machine import Pin

class NetworkStatus:
    idle = 0
    connecting = 1
    wrong_password = -3
    no_ap = -2
    connect_fail = -1
    connect_success = 3


def connect_to_wifi(is_initial=True):
    wlan.active(True)
    wlan.connect(wifi_ssid, wifi_pass)


'''
Main execution
'''

wifi_ssid = "BW_Hive"
wifi_pass = ""

'''
Initial setup
'''

led = Pin("LED", machine.Pin.OUT)
led.on()

wlan = network.WLAN(network.STA_IF)
wlan.active(True)



mac = wlan.config('mac')
print(ubinascii.hexlify(mac).decode())


while True:
    print("Attempting connect to WiFi")
    wlan.connect(ssid, key)
    if (wlan.status() == NetworkStatus.connect_success):
        break
    print("Connection failed, status is:", wlan.status())
    time.sleep(1)

while True:

    #print("Result is", wlan.ifconfig())
    print("Status is", str(wlan.status('rssi')))
    print("Sending request")
    r = urequests.get("https://mopsdev.bw.edu/")
    print("Received response", r.status_code)
    print(r.content)
    time.sleep(5)



wlan.active(True)
while True:
    print("Attempting connect to WiFi")
    wlan.connect(ssid, key)
    if (wlan.status() == 3):
        break
    print("Connection failed, status is:", wlan.status())
    time.sleep(1)

while True:

    #print("Result is", wlan.ifconfig())
    print("Status is", str(wlan.status('rssi')))
    print("Sending request")
    r = urequests.get("https://mopsdev.bw.edu/")
    print("Received response", r.status_code)
    print(r.content)
    time.sleep(5)


