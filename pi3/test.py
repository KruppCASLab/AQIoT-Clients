import requests
import json
from datetime import datetime


# testing to create some sensor data 
date = datetime.now()

sensor_data = {
    "userToken": "user-1234",
    "authToken": "auth-5678"
}

x = requests.post('http://localhost:8080/sensors', json=sensor_data)

if x.status_code == 201:
    print("sensor created successfully")
else:
    print("failed to create sensor")
