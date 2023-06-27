# Raspberry Pi Pico W - RP2040
These are instructions specific to Raspberry Pi 2040 board.

## Overview
> The Raspberry Pi Pico W is a microcontroller that is powered by Raspberry Pi's RP2040 chip. The RP2040 processor has two cores and has more than enough processing power for this project. It is an affordable board that is perfect for this job.  

## Update CircuitPython
* The Pico W may not come with the latest install installation of CircuitPython. To install the latest, you can go to the following website: [Pico W Download](https://circuitpython.org/board/raspberry_pi_pico_w/) and download the .UF2 file. Once you download it and connect your Pico, you can drag and drop this file onto your Pico board.
* At the time of this writing, the latest version that was tested is ::8.1.0::

## Required Libraries
* There are several libraries that are required for the Pico to read from the PM sensor and transmit air quality data. These libraries are included below: