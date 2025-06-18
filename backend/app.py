from flask import Flask, request, jsonify
import google.generativeai as genai
import requests
from PIL import Image
import io
import os
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import random

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS to allow all origins and methods
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure Gemini AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro-vision')

# Constants for calculations
TOTAL_LENGTH = 250  # Total length of shelf in cm

# In-memory storage
sales_history = []
potential_thefts = []
alerts = []

# In-memory storage for sensor data
sensor_data = {
    "D1": 0,  # Ultrasonic sensor 1
    "F1": 0,  # Force sensor 1
    "D2": 0,  # Ultrasonic sensor 2
    "F2": 0   # Force sensor 2
}

# Shelf configuration
SHELVES = {
    "D1": {
        "product_name": "Product 1",
        "force_sensor": "F1",
        "item_weight": 50,  # Weight of one item in grams
        "item_height": 10,  # Height of one item in cm
        "empty_distance": 200,  # Distance when shelf is empty
        "full_distance": 50     # Distance when shelf is full
    },
    "D2": {
        "product_name": "Product 2",
        "force_sensor": "F2",
        "item_weight": 30,  # Different weight for different product
        "item_height": 8,   # Different height for different product
        "empty_distance": 200,  # Distance when shelf is empty
        "full_distance": 50     # Distance when shelf is full
    }
}

def calculate_stock(sensor_id):
    """Calculate number of items using both ultrasonic and force sensors"""
    config = SHELVES[sensor_id]
    
    # Get readings from both sensors
    distance = sensor_data[sensor_id]
    weight = sensor_data[config["force_sensor"]]
    
    # Calculate from ultrasonic
    empty_distance = config["empty_distance"]
    full_distance = config["full_distance"]
    distance_range = empty_distance - full_distance
    occupied_space = empty_distance - distance
    count_from_distance = max(0, int((occupied_space / distance_range) * 20))  # Assuming max 20 items
    
    # Calculate from force
    count_from_weight = max(0, int(weight / config["item_weight"]))
    
    # Use the average of both measurements
    return (count_from_distance + count_from_weight) // 2

def generate_shelf_status():
    status = {}
    for sensor_id, config in SHELVES.items():
        # Calculate current count using both sensors
        current_count = calculate_stock(sensor_id)
        
        # Determine status based on count
        if current_count == 0:
            status_text = "empty"
            alerts.append({
                "id": f"empty-{sensor_id}-{datetime.now().isoformat()}",
                "title": "Empty Shelf Alert",
                "message": f"{config['product_name']} shelf is empty and needs restocking",
                "severity": "high",
                "timestamp": datetime.now().isoformat(),
                "type": "stock"
            })
        elif current_count < 5:
            status_text = "low"
            alerts.append({
                "id": f"low-{sensor_id}-{datetime.now().isoformat()}",
                "title": "Low Stock Alert",
                "message": f"{config['product_name']} shelf is running low on stock. Current count: {current_count}",
                "severity": "medium",
                "timestamp": datetime.now().isoformat(),
                "type": "stock"
            })
        else:
            status_text = "normal"
        
        # Store status for both sensors
        status[sensor_id] = {
            "objects_count": current_count,
            "status": status_text,
            "product_name": config["product_name"],
            "height": sensor_data[sensor_id]  # Add raw height value
        }
        status[config["force_sensor"]] = {
            "objects_count": current_count,
            "status": status_text,
            "product_name": config["product_name"],
            "weight": sensor_data[config["force_sensor"]]  # Add raw weight value
        }
    
    # Keep only last 50 alerts
    alerts[:] = alerts[-50:]
    return status

@app.route('/test', methods=['GET'])
def test_connection():
    return jsonify({'status': 'ok', 'message': 'Server is running'}), 200

@app.route('/record_sale', methods=['POST', 'OPTIONS'])
def record_sale():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        logger.info("Received sale recording request")
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        
        if not data:
            logger.error("No data received in request")
            return jsonify({'error': 'No data received'}), 400
        
        # Validate required fields
        required_fields = ['shelf_id', 'items_sold']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400
        
        # Add the sale to history
        sales_history.append(data)
        logger.info(f"Sale recorded successfully: {data}")
        
        return jsonify({
            'message': 'Sale recorded successfully',
            'sale': data,
            'total_sales': len(sales_history)
        }), 200
    except Exception as e:
        logger.error(f"Error recording sale: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_sales_data', methods=['GET'])
def get_sales_data():
    try:
        logger.info("Received sales data request")
        
        # Initialize default response
        response_data = {
            'sales': [],
            'total_sales': 0,
            'hourly_rate': 0,
            'daily_rate': 0,
            'last_sale': None,
            'timestamp': datetime.now().isoformat()
        }

        # If we have sales history, calculate metrics
        if sales_history:
            try:
                now = datetime.now()
                one_hour_ago = now - timedelta(hours=1)
                one_day_ago = now - timedelta(days=1)

                # Filter sales for different time periods
                hourly_sales = []
                daily_sales = []
                
                for sale in sales_history:
                    try:
                        sale_time = datetime.fromisoformat(sale.get('timestamp', ''))
                        if sale_time > one_hour_ago:
                            hourly_sales.append(sale)
                        if sale_time > one_day_ago:
                            daily_sales.append(sale)
                    except Exception as e:
                        logger.error(f"Error processing sale timestamp: {str(e)}")
                        continue

                # Calculate rates
                hourly_rate = len(hourly_sales)
                daily_rate = len(daily_sales)

                # Get the last sale
                last_sale = sales_history[-1] if sales_history else None

                # Update response data
                response_data.update({
                    'sales': sales_history,
                    'total_sales': len(sales_history),
                    'hourly_rate': hourly_rate,
                    'daily_rate': daily_rate,
                    'last_sale': last_sale.get('timestamp') if last_sale else None
                })

            except Exception as e:
                logger.error(f"Error calculating sales metrics: {str(e)}")
                # Continue with default values if calculation fails

        logger.info(f"Returning sales data: {response_data}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting sales data: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch sales data',
            'details': str(e),
            'sales': [],  # Return empty list on error
            'total_sales': 0,
            'hourly_rate': 0,
            'daily_rate': 0,
            'last_sale': None,
            'timestamp': datetime.now().isoformat()
        }), 200  # Return 200 even on error to prevent frontend issues

@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    try:
        logger.info("Received sensor data request")
        shelf_status = generate_shelf_status()
        return jsonify({
            'shelf_status': shelf_status,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting sensor data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_potential_thefts', methods=['GET'])
def get_potential_thefts():
    try:
        logger.info("Received potential thefts request")
        
        # Initialize default response
        response_data = {
            'thefts': [],
            'timestamp': datetime.now().isoformat()
        }

        # Check for expired pending sales
        now = datetime.now()
        expired_sales = []
        
        # Check sales history for potential thefts
        for sale in sales_history:
            try:
                sale_time = datetime.fromisoformat(sale.get('timestamp', ''))
                time_diff = (now - sale_time).total_seconds() / 60  # in minutes
                
                # If sale was more than 10 minutes ago and no matching removal
                if time_diff > 10:
                    # Check if this was already marked as a theft
                    if not any(t.get('sale_id') == sale.get('sale_id') for t in potential_thefts):
                        theft = {
                            'sale_id': sale.get('sale_id', 'unknown'),
                            'shelf_id': sale.get('shelf_id', 'unknown'),
                            'items_removed': sale.get('items_sold', 0),
                            'timestamp': sale.get('timestamp', now.isoformat()),
                            'confidence': 'high',
                            'reason': 'No matching removal found within time window',
                            'product_name': sale.get('product_name', 'Unknown Product')
                        }
                        potential_thefts.append(theft)
                        expired_sales.append(sale)
            except Exception as e:
                logger.error(f"Error processing sale: {str(e)}")
                continue
        
        # Remove expired sales from history
        for sale in expired_sales:
            if sale in sales_history:
                sales_history.remove(sale)
        
        # Keep only last 20 potential thefts
        potential_thefts[:] = potential_thefts[-20:]
        
        # Update response with current thefts
        response_data['thefts'] = potential_thefts
        
        logger.info(f"Returning {len(potential_thefts)} potential thefts")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting potential thefts: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch potential thefts',
            'details': str(e),
            'thefts': []  # Return empty list on error
        }), 200  # Return 200 even on error to prevent frontend issues

@app.route('/get_alerts', methods=['GET'])
def get_alerts():
    try:
        # Sort alerts by timestamp (newest first)
        sorted_alerts = sorted(alerts, key=lambda x: x["timestamp"], reverse=True)
        return jsonify(sorted_alerts)
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_latest_image', methods=['GET'])
def get_latest_image():
    try:
        # Get the most recent image from the uploads directory
        image_dir = 'uploads'
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
            
        image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
        if not image_files:
            return jsonify({
                "image_url": "https://via.placeholder.com/800x600?text=No+Image+Available",
                "timestamp": datetime.now().isoformat()
            }), 200
            
        latest_image = max(image_files, key=lambda x: os.path.getctime(os.path.join(image_dir, x)))
        image_url = f"{request.host_url}uploads/{latest_image}"
        
        return jsonify({
            "image_url": image_url,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting latest image: {str(e)}")
        return jsonify({
            "error": "Failed to get latest image",
            "details": str(e)
        }), 200

@app.route('/check_misplacement', methods=['POST'])
def check_misplacement():
    try:
        data = request.get_json()
        shelf_id = data.get('shelf_id')
        expected_product = data.get('expected_product')
        image_url = data.get('image_url')

        if not all([shelf_id, expected_product, image_url]):
            return jsonify({
                'error': 'Missing required parameters',
                'details': 'shelf_id, expected_product, and image_url are required'
            }), 400

        # Get the image from the URL
        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({
                'error': 'Failed to fetch image',
                'details': f'HTTP status code: {response.status_code}'
            }), 400

        # Convert image to bytes
        image_bytes = response.content
        image = Image.open(io.BytesIO(image_bytes))

        # Prepare the prompt for Gemini AI
        prompt = f"""
        Analyze this shelf image and check if the products match the expected product type.
        Expected product: {expected_product}
        
        Look for any products that don't belong in this shelf. For example, if this is a Pepsi shelf,
        check if there are any Coke bottles or other products that don't belong.
        
        Return a JSON response with:
        - misplaced: true/false (true if any wrong products are found)
        - detected_product: name of the product actually on the shelf
        - confidence: high/medium/low (confidence in the detection)
        - details: brief explanation of what was found
        """

        # Generate content with Gemini AI
        response = model.generate_content([prompt, image])
        
        # Parse the response
        try:
            result = eval(response.text)  # Convert string response to dict
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error parsing Gemini AI response: {str(e)}")
            return jsonify({
                'error': 'Failed to parse AI response',
                'details': str(e),
                'raw_response': response.text
            }), 200

    except Exception as e:
        logger.error(f"Error checking misplacement: {str(e)}")
        return jsonify({
            'error': 'Failed to check misplacement',
            'details': str(e)
        }), 200

@app.route('/get_shelf_config', methods=['GET'])
def get_shelf_config():
    try:
        logger.info("Received shelf configuration request")
        return jsonify({
            "shelves": SHELVES
        }), 200
    except Exception as e:
        logger.error(f"Error getting shelf configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Configure image storage
IMAGE_FOLDER = 'uploads'
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    image = request.data
    if image:
        filename = f"uploads/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        os.makedirs("uploads", exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(image)
        logger.info(f"[+] Saved image: {filename}")
        return "Image received and saved", 200
    return "No image data received", 400

@app.route('/upload_data', methods=['POST'])
def upload_data():
    try:
        data = request.get_json()
        logger.info(f"Received sensor data: {data}")
        
        # Update sensor data
        for sensor_id, value in data.items():
            if sensor_id in sensor_data:
                sensor_data[sensor_id] = value
        
        return jsonify({
            'message': 'Sensor data updated successfully',
            'sensor_data': sensor_data
        }), 200
    except Exception as e:
        logger.error(f"Error updating sensor data: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask server...")
    app.run(debug=True, port=5000, host='0.0.0.0') 
