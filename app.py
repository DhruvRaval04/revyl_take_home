from flask import Flask, request, jsonify
from demo_booking_agent import run_booking_automation
import os
import traceback
from dotenv import load_dotenv
import logging
from flask_cors import CORS

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("booking_api.log"),
        logging.StreamHandler()
    ]
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

@app.route('/api/book-demo', methods=['POST'])
def book_demo():
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if not data:
            logging.warning("No data provided in request")
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        url = data.get('url')
        booking_details = data.get('booking_details', {})
        
        if not url:
            logging.warning("URL is required but not provided")
            return jsonify({"success": False, "error": "URL is required"}), 400
            
        # Validate booking details
        required_fields = ["name", "email"]
        missing_fields = [field for field in required_fields if field not in booking_details]
        
        if missing_fields:
            logging.warning(f"Missing required booking details: {', '.join(missing_fields)}")
            return jsonify({
                "success": False,
                "error": f"Missing required booking details: {', '.join(missing_fields)}"
            }), 400
            
        # Log the request
        logging.info(f"Processing booking request for URL: {url}")

        # Run the booking automation
        process_log = run_booking_automation(url=url, booking_details=booking_details)
        print(process_log)

        # Check the status from the last entry in the process log
        final_status = next((item.get("status") for item in reversed(process_log) 
                        if "status" in item), None)

        success = final_status == "success"

        # Format the logs for better readability
        formatted_logs = []
        for log_entry in process_log:
            for key, value in log_entry.items():
                formatted_logs.append(f"{key}: {value}")

        # Return response with the full process log
        if success:
            logging.info(f"Booking completed successfully for URL: {url}")
            return jsonify({
                "success": True, 
                "message": "Booking completed successfully",
                "logs": formatted_logs
            }), 200
        else:
            logging.error(f"Booking process failed for URL: {url}")
            return jsonify({
                "success": False, 
                "error": "Booking process failed",
                "logs": formatted_logs
            }), 500

            
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Error processing booking request: {str(e)}\n{error_details}")
        return jsonify({
            "success": False, 
            "error": str(e), 
            "details": error_details,
            "logs": []
        }), 500

if __name__ == '__main__':
    app.run(port=5000)