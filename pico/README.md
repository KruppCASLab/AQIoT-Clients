# Raspberry Pi Pico W - RP2040
These are instructions specific to the Raspberry Pi Pico 2040 board and how to configure it to detect air quality and report it tour services.

## Overview
* The Raspberry Pi Pico W is a microcontroller that is powered by Raspberry Pi's RP2040 chip. The RP2040 processor has two cores and has more than enough processing power for this project. It is an affordable board that is a great fit for this type of application.

## Update CircuitPython
* The Pico W may not come with the latest install installation of CircuitPython. To install the latest, you can go to the following website: [Pico W Download](https://circuitpython.org/board/raspberry_pi_pico_w/) and download the .UF2 file. Once you download it and connect your Pico, you can drag and drop this file onto your Pico drive. Below are the instructions from the site that describe how to do this:

> Inside the RP2040 is a 'permanent ROM' USB UF2 bootloader. What that means is when you want to program new firmware, you can hold down the BOOTSEL button while plugging it into USB (or pulling down the RUN/Reset pin to ground) and it will appear as a USB disk drive you can drag the firmware onto.     

* At the time of this writing, the latest version that was tested is ::8.1.0::

## Required Libraries
* There are several libraries that are required for the Pico to read from the PM sensor and transmit air quality data. These libraries are listed below:

	1. adafruit_bus_device
	2. adafruit_pm25
	3. adafruit_requests

* You can download these libraries directly from the circuitpython.org website: [Libraries](https://circuitpython.org/libraries)
	* Simply drag the `adafruit_requets.mpy` file into the lib folder as well as the `adafruit_bus_device` folder and `adafruit_pm25` folder. 

## Configure Connectivity
* Inside this repository, you will find a `settings.toml` file. Within this file, you can configure variables that can be read by your CircuitPython code. 
* Be sure to set the values for the following settings:
	* `WIFI_SSID` This is the name of the WiFi network you are connecting to. The Pico W must connect via WiFi at the time of this writing to upload air quality data.
	* `WIFI_PASSWORD` This is the PSK that is used to connect to the WiFi network. If a password is not required, this can be left blank and just use two double quotes:
		* `WIFI_PASSWORD=""`
	* `CLIENT_ID` This is a legacy setting that is still used in some applications. This does not need to be set and can be left blank
	* `CLIENT_KEY` This is the key that you acquired when you registered your sensor.

## Testing
* The code in the Pico will detect if there is a misconfiguration and print it out in the console. Use Thonny to ensure that it does report a reading successfully. You will know this succeeds when you receive back a `200 Success`. Below is example output:

```
Sensor Client Id: 33
Attempting to Connect to SSID: TheResistance
Connection to WiFi TheResistance Success!
My MAC addr: ['0x28', '0xcd', '0xc1', '0x0', '0xdc', '0x53']
My IP address is 10.0.1.75
Found PM2.5 sensor, reading data...
Attempting pm25 read again...

Concentration Units (standard)
---------------------------------------
PM 1.0: 3	PM2.5: 4	PM10: 4
Concentration Units (environmental)
---------------------------------------
PM 1.0: 3	PM2.5: 4	PM10: 4
---------------------------------------
Particles > 0.3um / 0.1L air: 678
Particles > 0.5um / 0.1L air: 206
Particles > 1.0um / 0.1L air: 36
Particles > 2.5um / 0.1L air: 4
Particles > 5.0um / 0.1L air: 0
Particles > 10 um / 0.1L air: 0
---------------------------------------
trying to send JSON post request
Success - Response from server:  200 Success
```