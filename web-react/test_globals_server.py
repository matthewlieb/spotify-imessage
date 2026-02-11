#!/usr/bin/env python3
"""
Test server with global variables and configuration from main server.
"""

import os
import logging
import queue
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

logger.info("Test globals Flask app created successfully")

# Test the exact configuration from main server
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'csv'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

logger.info("✅ App config set successfully")

# Test creating upload directory
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info("✅ Upload directory created/accessed successfully")
except Exception as e:
    logger.error(f"❌ Upload directory failed: {e}")

# Test global variables
try:
    processing_status = {}
    status_queue = queue.Queue()
    logger.info("✅ Global variables created successfully")
except Exception as e:
    logger.error(f"❌ Global variables failed: {e}")

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    logger.info("Health check endpoint called")
    try:
        response = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        logger.info(f"Health check response: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-config')
def test_config():
    """Test endpoint to check configuration."""
    logger.info("Config test endpoint called")
    config = {
        'upload_folder': app.config.get('UPLOAD_FOLDER'),
        'max_content_length': app.config.get('MAX_CONTENT_LENGTH'),
        'processing_status_exists': 'processing_status' in globals(),
        'status_queue_exists': 'status_queue' in globals()
    }
    return jsonify(config)

@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({'message': 'Test globals server working'})

if __name__ == '__main__':
    logger.info("Starting test globals Flask server on port 8008")
    app.run(host='0.0.0.0', port=8008, debug=False)
