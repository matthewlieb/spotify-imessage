#!/usr/bin/env python3
"""
Simple test Flask server to isolate API issues.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health_check():
    """Simple health check endpoint."""
    logger.info("Health check endpoint called")
    return jsonify({'status': 'healthy', 'message': 'Test server working'})

@app.route('/api/test')
def test_endpoint():
    """Test endpoint to check if Flask is responding."""
    logger.info("Test endpoint called")
    return jsonify({'message': 'Test endpoint working'})

@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({'message': 'Test Flask server is running'})

if __name__ == '__main__':
    logger.info("Starting test Flask server on port 8005")
    app.run(host='0.0.0.0', port=8005, debug=False)
