import serial
import requests
import time

# Adjust your COM port and baud rate
ser = serial.Serial('COM5', 9600)  # Replace COM5 with your Arduino's COM port
server_url = 'http://10.16.2.192:5000/upload_data'  # Update to match your Flask route

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        print("Received:", line)

        # Parse the data
        parts = line.split(',')
        data = {}
        for part in parts:
            key, value = part.split(':')
            data[key.strip()] = int(value.strip())

        # Send to server
        response = requests.post(server_url, json=data)
        print("Sent to server, response:", response.status_code, response.text)

    except Exception as e:
        print("Error:", e)

    time.sleep(5)
