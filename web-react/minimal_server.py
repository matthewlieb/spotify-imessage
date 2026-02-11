#!/usr/bin/env python3
"""
Minimal version of the main server to isolate issues.
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

logger.info("Minimal Flask app created successfully")

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

@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({'message': 'Minimal server working'})

if __name__ == '__main__':
    logger.info("Starting minimal Flask server on port 8006")
    app.run(host='0.0.0.0', port=8006, debug=False)
