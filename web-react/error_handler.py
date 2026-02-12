#!/usr/bin/env python3
"""
Error handling utilities for spotify-message web application.
"""

import logging
import traceback
from datetime import datetime
from flask import jsonify, request
from functools import wraps

# Configure error logging
error_logger = logging.getLogger('error_handler')
error_logger.setLevel(logging.ERROR)

def handle_api_error(error, message="An error occurred", status_code=500):
    """Handle API errors with proper logging and response."""
    error_logger.error(f"API Error: {message} - {str(error)}")
    error_logger.error(f"Traceback: {traceback.format_exc()}")
    
    return jsonify({
        'error': message,
        'timestamp': datetime.now().isoformat(),
        'status': 'error'
    }), status_code

def handle_spotify_error(error, message="Spotify API error"):
    """Handle Spotify-specific errors."""
    error_logger.error(f"Spotify Error: {message} - {str(error)}")
    
    # Check for common Spotify API errors
    if "401" in str(error):
        return jsonify({
            'error': 'Authentication failed. Please log in again.',
            'timestamp': datetime.now().isoformat(),
            'status': 'auth_error'
        }), 401
    elif "403" in str(error):
        return jsonify({
            'error': 'Access denied. Please check your Spotify permissions.',
            'timestamp': datetime.now().isoformat(),
            'status': 'permission_error'
        }), 403
    elif "429" in str(error):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'timestamp': datetime.now().isoformat(),
            'status': 'rate_limit_error'
        }), 429
    else:
        return jsonify({
            'error': 'Spotify service temporarily unavailable. Please try again.',
            'timestamp': datetime.now().isoformat(),
            'status': 'service_error'
        }), 503

def handle_file_error(error, message="File processing error"):
    """Handle file-related errors."""
    error_logger.error(f"File Error: {message} - {str(error)}")
    
    return jsonify({
        'error': 'File processing failed. Please check your file format.',
        'timestamp': datetime.now().isoformat(),
        'status': 'file_error'
    }), 400

def safe_api_call(func):
    """Decorator for safe API calls with error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_logger.error(f"Error in {func.__name__}: {str(e)}")
            error_logger.error(f"Traceback: {traceback.format_exc()}")
            return handle_api_error(e, f"Error in {func.__name__}")
    return wrapper

def log_request_info():
    """Log request information for debugging."""
    error_logger.info(f"Request: {request.method} {request.url}")
    error_logger.info(f"Headers: {dict(request.headers)}")
    if request.is_json:
        error_logger.info(f"JSON Data: {request.get_json()}")

def create_error_response(error_type, message, status_code=500):
    """Create a standardized error response."""
    return jsonify({
        'error': message,
        'type': error_type,
        'timestamp': datetime.now().isoformat(),
        'status': 'error'
    }), status_code

# Global error handlers
def register_error_handlers(app):
    """Register global error handlers with Flask app."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return create_error_response('bad_request', 'Invalid request', 400)
    
    @app.errorhandler(401)
    def unauthorized(error):
        return create_error_response('unauthorized', 'Authentication required', 401)
    
    @app.errorhandler(403)
    def forbidden(error):
        return create_error_response('forbidden', 'Access denied', 403)
    
    @app.errorhandler(404)
    def not_found(error):
        return create_error_response('not_found', 'Resource not found', 404)
    
    @app.errorhandler(413)
    def file_too_large(error):
        return create_error_response('file_too_large', 'File too large', 413)
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return create_error_response('rate_limit', 'Too many requests', 429)
    
    @app.errorhandler(500)
    def internal_error(error):
        return create_error_response('internal_error', 'Internal server error', 500)
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        error_logger.error(f"Unexpected error: {str(error)}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response('unexpected_error', 'An unexpected error occurred', 500)
