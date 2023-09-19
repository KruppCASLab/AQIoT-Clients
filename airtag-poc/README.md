# AirTag - Proof of Concept
Contains code for creating an AirTag proof of concept to allow opportunistic sensing.

## Resources

* This article links the GitHub repository: [Getting to grips with Bluetooth on Pico W](https://www.raspberrypi.com/news/getting-to-grips-with-bluetooth-on-pico-w/)
  * Takeaways:
    * Pico would use a Generic Access Profile (GAP)
    * It would be a peripheral (instead of central)
    * GAP allows only 31 bytes of data to be sent
      * Apple uses 37 where 6 are reserved for the advertising MAC Address

* Documentation on Bluetooth: [bluetooth — low-level Bluetooth — MicroPython latest documentation](https://docs.micropython.org/en/latest/library/bluetooth.html)
  * This is the aioble library that can be used: [micropython-lib/micropython/bluetooth/aioble at master · micropython/micropython-lib](https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble)
  * Using this model, it uses asyncio in Python: [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)
* Raspberry Pi PDF on Bluetooth: [connecting-to-the-internet-with-pico-w](https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf)
* Examples on GitHub: [pico-micropython-examples/bluetooth/ble_advertising.py at master · raspberrypi/pico-micropython-examples](https://github.com/raspberrypi/pico-micropython-examples/blob/master/bluetooth/ble_advertising.py)