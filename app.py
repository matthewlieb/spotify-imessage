#!/usr/bin/env python3
"""
Zingaroo Flask Backend
Simple Flask app for Railway deployment
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, request, session, redirect, url_for
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
import json
import re
import sqlite3
from pathlib import Path

# Add web-react directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web-react'))

# Import from web-react directory
try:
    from web-react.server import *
except ImportError:
    # Fallback if imports fail
    print("Warning: Could not import from web-react directory")
    
    # Basic Flask app setup
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
    CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'https://steady-mermaid-2b30bb.netlify.app'])

    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

    @app.route('/')
    def index():
        """Root endpoint."""
        return jsonify({'message': 'Zingaroo Backend API', 'status': 'running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8004))
    app.run(host='0.0.0.0', port=port, debug=False)
