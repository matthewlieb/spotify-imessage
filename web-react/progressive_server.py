#!/usr/bin/env python3
"""
Progressive server to identify which dependency causes hanging.
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

logger.info("Progressive Flask app created successfully")

# Test 1: Basic imports only
logger.info("✅ Basic imports working")

# Test 2: Add datetime and pathlib
from pathlib import Path
logger.info("✅ datetime and pathlib working")

# Test 3: Add threading
import threading
logger.info("✅ threading working")

# Test 4: Add queue
import queue
logger.info("✅ queue working")

# Test 5: Add file operations
import tempfile
import shutil
logger.info("✅ file operations working")

# Test 6: Add subprocess
import subprocess
logger.info("✅ subprocess working")

# Test 7: Add SQLite (this might be the culprit)
try:
    import sqlite3
    logger.info("✅ sqlite3 working")
except Exception as e:
    logger.error(f"❌ sqlite3 failed: {e}")

# Test 8: Add Spotify imports (this might be the culprit)
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    logger.info("✅ spotipy working")
except Exception as e:
    logger.error(f"❌ spotipy failed: {e}")

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

@app.route('/api/test-deps')
def test_dependencies():
    """Test endpoint to check dependencies."""
    logger.info("Dependencies test endpoint called")
    deps = {
        'basic_imports': True,
        'datetime': True,
        'pathlib': True,
        'threading': True,
        'queue': True,
        'file_ops': True,
        'subprocess': True,
        'sqlite3': 'sqlite3' in globals(),
        'spotipy': 'spotipy' in globals()
    }
    return jsonify(deps)

@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({'message': 'Progressive server working'})

if __name__ == '__main__':
    logger.info("Starting progressive Flask server on port 8007")
    app.run(host='0.0.0.0', port=8007, debug=False)
