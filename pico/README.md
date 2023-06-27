# Raspberry Pi Pico W - RP2040
These are instructions specific to Raspberry Pi 2040 board.

## Overview
* The Raspberry Pi Pico W is a microcontroller that is powered by Raspberry Pi's RP2040 chip. The RP2040 processor has two cores and has more than enough processing power for this project. It is an affordable board that is perfect for this job.

## Update CircuitPython
* The Pico W may not come with the latest install installation of CircuitPython. To install the latest, you can go to the following website: [Pico W Download](https://circuitpython.org/board/raspberry_pi_pico_w/) and download the .UF2 file. Once you download it and connect your Pico, you can drag and drop this file onto your Pico board. Below are the instructions from the site that describe how to do this:

> **Inside the RP2040 is a 'permanent ROM' USB UF2 bootloader**. What that means is when you want to program new firmware, you can hold down the BOOTSEL button while plugging it into USB (or pulling down the RUN/Reset pin to ground) and it will appear as a USB disk drive you can drag the firmware onto.   

* At the time of this writing, the latest version that was tested is ::8.1.0::

## Required Libraries
* There are several libraries that are required for the Pico to read from the PM sensor and transmit air quality data. These libraries are included below: