# Raspberry Pi 3 B+ Setup Guide

## 1. Download Raspberry Pi Imagers 
1. Visit the official Raspberry Pi website: [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
2. Download and install the Raspberry Pi Imager tool for your computer (Windows, macOS, or Linux).

## 2. Flash the OS onto the SD Card
1. Insert your SD card (minimum 8GB reccomended) into your computer.
2. Open the Pi imager.
3. Select `Choose OS`and select one of the following:
  - `Raspberry Pi OS (32-bit)` for general use.
  - `Raspberry Pi OS (64-bit)` if you need 64-bit support.
4. Click `CHOOSE STORAGE` and select your SD card.
5. Click `WRITE` and wait for the process to complete. This will flash the OS onto the SD card.
6. Safely eject the SD card from your computer.

## 3. Set Up Your Raspberry Pi
1. Insert the SD card into the Raspberry Pi 3 B+.
2. Connect the following to your Raspberry Pi:
   - HDMI cable to your monitor.
   - USB keyboard and mouse.
3. Connect any other external hardware (Pico Sensor)
4. Plug in micro-USB power supply to power up Raspberry Pi
   - choose your country, language, and time zone.
   - set up a new password for the "pi" user.
   - connect to a WIFI network if ethernet port not enabled.
   - update the software
  
## 4. Set up Python and Write Code 

### Python is preinstalled 
- Open terminal and verify Python installation with `python3 --version`
- first type nano hello.py
- write a print statement `print("Hello, Raspberry Pi!")`
- save the file and run in terminal `python3 hello_world.py`
- Additionally, you can write in thonny IDE and run and save your code there as well.

## 5. Enable SSH Access


## 6. Set up client code for PM25 sensor
