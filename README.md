# AQIoT - Clients
## Code
This repository contains code for the sensor microcontrollers and single-board computers. They are organized in separate folders by the type of board. For example, code for the Raspberry Pi Pico board will be found in the `pico` folder. 

Common code is located in the `common` folder. 

Each folder should have a `Readme.md` folder for specific instructions for that board. For example, one might include a reference to Thonny for programming the Pico board and how to update the boot loader.

## Air Sensor Siting Checklist
### Pre-Install Checklist
- [ ] Communications: Sensor is in range of any wireless communication
- [ ] Secure: The sensor is in a location where it will not be tampered with or stolen
- [ ] Power: The sensor has a consistent reliable power source
- [ ] Height: Verify height is around 6 feet from ground level or rooftop
- [ ] Airflow: The airflow of the sensor should be free and not altered by a nearby source that could modify the natural airflow (e.g. HVAC unit)
- [ ] Emission Sources: Verify emission sensors are not nearby sensor
- [ ] Access: Ensure we have regular access to the site in case we need to perform maintenance on the sensor
- [ ] Building: If placed on a building, ensure it is on the upwind side

### Post-Install Checklist
- [ ] Take a photo of the sensor
- [ ] Verify that at least for 5 minutes the sensor reports readings before leaving site
- [ ] Test unplugging and plugging back in the power source and verify sensor continues to report
- [ ] Record location of sensor and update deployment through dashboard

### Resources
* https://www.epa.gov/air-sensor-toolbox/guide-siting-and-installing-air-sensors
