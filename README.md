# Smart-Shelf-Monitoring-System
A comprehensive smart shelf monitoring system that combines hardware sensors, computer vision, and AI to track inventory, detect theft, and monitor shelf conditions in real-time

## Project Overview
This project consists of three main components:

1.Frontend: React-based web application for real-time monitoring and management

2.Backend: Flask server handling data processing and AI integration

3.Hardware: Arduino-based sensor system with ESP32-CAM for computer vision

## Features

- Real-time inventory tracking using ultrasonic and force sensors
- Computer vision-based product placement monitoring  
- AI-powered theft detection and alert system  
- Sales tracking and analytics  
- Real-time alerts for potential thefts and misplacements  
- Interactive dashboard for monitoring shelf status  

## Tech Stack

### FrontEnd

- React.js
- Tailwind CSS
- Axios for API communication
- React Router for navigation

### BackEnd

- Flask
- Google Gemini AI for image analysis
- CORS enabled for cross-origin requests
- RESTful API endpoints

### HardWare

- ESP32-CAM for computer vision
- Ultrasonic sensors for distance measurement
- Force sensors for weight detection
- Arduinofor sensor data collection

  ## Installation

  ### FrontEnd Setup

  ```bash
   cd frontend
   npm install
   npm start

### BackEnd SetUp

  ```bash
  cd backend
  pip install -r requirements.txt
  python app.py

```
### HardWare SetUP

1.Upload the Arduino code to your ESP32-CAM
2.Connect sensors according to the pin configuration
3.Ensure proper power supply and network connectivity

## API Endpoints

- `/test` - Test connection
- `/record_sale` - Record a sale transaction
- `/get_sales_data` - Retrieve sales history
- `/get_sensor_data` - Get real-time sensor readings
- `/get_potential_thefts` - Get theft detection alerts
- `/get_alerts` - Get system alerts
- `/get_latest_image` - Get latest camera feed
- `/check_misplacement` - Check for product misplacement
- `/get_shelf_config` - Get shelf configuration
- `/upload_image` - Upload new image for analysis
- `/upload_data` - Upload sensor data

## Environmental Variables

Create a .env file in the backend directory with:

```bash
GOOGLE_API_KEY=your_api_key_here
```

## Contributing

1.Fork the repository

2.Create your feature branch (`git checkout -b feature/AmazingFeature`)

3.Commit your changes (`git commit -m 'Add some AmazingFeature'`)

4.Push to the branch (`git push origin feature/AmazingFeature`)

5.Open a Pull Request





