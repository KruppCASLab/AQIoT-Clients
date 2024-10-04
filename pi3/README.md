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
5. During the **OS Customisation** step, navigate to the `Services` tab.
6. Tick the checkbox to `Enable SSH`.
7. Select `password authentication` to log in using the same username and password you use while physically using your Raspberry Pi. Select `Allow public-key authentication only` to [configure an SSH key](https://www.raspberrypi.com/documentation/computers/remote-access.html#configure-ssh-without-a-password) for passwordless login.
8. Click `WRITE` and wait for the process to complete. This will flash the OS onto the SD card.
9. Safely eject the SD card from your computer.

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

## 5. Connect to an SSH server

### Local

Open a terminal window on your computer and enter the following command, replacing the `<ip address>` placeholder with the [IP address of the Raspberry Pi you’re trying to connect to](https://www.raspberrypi.com/documentation/computers/remote-access.html#ip-address) and `<username>` with your username:

```bash
$ ssh <username>@<ip address>
# default
$ ssh <username>@raspberrypi.local
```

When the connection works, you will see a security warning. Type `yes` to continue. You will only see this warning the first time you connect.

Enter your account password when prompted.

You should now see the Raspberry Pi command prompt:

```bash
<username>@<hostname> ~ $
# default
<username>@raspberrypi ~ $
```

You are now connected to the Raspberry Pi remotely, and can execute commands.

> If you receive a `connection timed out` error, you may have entered the wrong IP address for the Raspberry Pi. Go to your router settings(Usually it's [http://192.168.1.1](http://192.168.1.1), but differs with different routers) and find the IP address of your Raspberry Pi.

### Windows SSH Softwares

> Softwares like PuTTY, Xshell, MobaXTerm is commonly used for SSH connection and X11 forwarding.

#### MobaXTerm

1. Click `Session` tab and navigate to `SSH` tab to create a SSH session.
2. Enter the hostname/IP address of your Raspberry Pi and your username.
   <img src="https://cdn.statically.io/gh/Aphcity/aphcity-assets/master/20240930/105214.5fe0e8.png" style="width: 800px;" />
3. Click `OK` and connect to the SSH terminal by entering your password.
   <img src="https://cdn.statically.io/gh/Aphcity/aphcity-assets/master/20240930/105534.929d48.png" style="width: 800px;" />
4. Click `Yes` to save password for future one-click logging in.
   <img src="https://cdn.statically.io/gh/Aphcity/aphcity-assets/master/20240930/110021.b302bd.png" />
5. All set, your SSH terminal should be like
   <img src="https://cdn.statically.io/gh/Aphcity/aphcity-assets/master/20241004/113911.1d33fa.png" />

> You can activate X11 Forward by using commands like `geany &` that supports X11 forwarding.
>
> <img src="https://cdn.statically.io/gh/Aphcity/aphcity-assets/master/20240930/110430.6d5299.png" />

## 6. Set up client code for PM25 sensor

- https://learn.adafruit.com/pm25-air-quality-sensor/python-and-circuitpython

- Follow the Tutorial from this Link and make sure you use `raspi-config` to enable serial communication which is listed in interfaces. reboot the pi after so it can be enabled.

- enable virtual environment to manage packages and install packages for UART import 

```
mkdir project-name && cd project-name
python3 -m venv .venv
source .venv/bin/activate
pip3 install pyserial adafruit-circuitpython-pm25
```

 - Use the UART code for raspi3 and leave out IC2 

```
import time
import board
import busio

reset_pin = None
import serial
uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=0.25)

#Connect to a PM2.5 sensor over UART
from adafruit_pm25.uart import PM25_UART
pm25 = PM25_UART(uart, reset_pin)
```

- Then after using this code and configuring the raspi serial settings, the python should be able to find the sensor.
- Use the code from print statement of "found PM25 sensor" and use the code inside the while loop as well.
- If successful you get some readings from the sensor detecting the air quality.
- If not then check again if you followed the steps and if not it could be an issue with the sensor hardware not being configured correct and notify admins.

## 7. Set up IP report service

The [send_ip.sh](./utils/send-ip.sh) file is a bash script that sends the current IP address of your pi to [Team page on CASLAB](https://caslab.case.edu/team/) using [ipify-api](https://github.com/rdegges/ipify-api) when you reboot/power on your pi. It requires one command line argument: a label which represents the owner of the pi.

The `send-ip.service` file is a systemd service file that runs the script on the pi on reboot.

Replace the comments with the correct information in [send-ip.txt](./utils/send-ip.txt). Remember to include a label argument!

Copy `send-ip.txt` to the `/etc/systemd/system/` directory AND CHANGE IT TO `send-ip.service`

``` bash
sudo cp ./pi3/utils/send-ip.txt /etc/systemd/system/send-ip.service
```

After you have finished the previous steps and saved your changes, run following command to enable the service. Now, the script should be fully working! You can test by running `sudo reboot` and visiting [Team page on CASLAB](https://caslab.case.edu/team/) after. Your pi's IP address should appear with the label that you used in the service folder.

``` bash
sudo systemctl enable send-ip.service
sudo systemctl start send-ip.service
```
