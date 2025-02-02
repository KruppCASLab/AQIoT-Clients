import requests
import json
import datetime


# testing to create some sensor data 
date = datetime.now()

sensor_data = {
    "sensor_id": 1,
    "sensor_date": int(date.strftime('%Y%m%d')),
    "type": "AQ_IOT",
    "description": "AQ sensor",
    "userToken": "user-1234",
    "authToken": "auth-5678"
}

x = requests.post('http://localhost:8080/sensor', json=json.dumps(sensor_data))

if x.status_code == 201:
    print("sensor created successfully")
else:
    print("failed to create sensor")
