#!/usr/bin/env python3
"""
Security configuration for spotify-message web application.
"""

import os
import secrets
from datetime import timedelta

def _cors_origins():
    """CORS allowed origins: localhost + any production frontend URL from env."""
    origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001'
    ]
    extra = os.getenv('CORS_ORIGINS', '').strip()
    if extra:
        origins.extend(o.strip() for o in extra.split(',') if o.strip())
    return origins

# Security configuration
SECURITY_CONFIG = {
    # CORS settings (production: set CORS_ORIGINS=https://your-netlify-site.netlify.app)
    'CORS_ORIGINS': _cors_origins(),
    
    # Security headers
    'SECURITY_HEADERS': {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://sdk.scdn.co https://accounts.spotify.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.spotify.com https://accounts.spotify.com https://*.railway.app; frame-src https://accounts.spotify.com;"
    },
    
    # Rate limiting
    'RATE_LIMIT': {
        'enabled': True,
        'requests_per_minute': 60,
        'burst_limit': 10
    },
    
    # Session security
    'SESSION_SECURITY': {
        'secure': False,  # Set to True in production with HTTPS
        'httponly': True,
        'samesite': 'Lax',
        'permanent': True,
        'lifetime': timedelta(hours=1)
    },
    
    # Input validation
    'INPUT_VALIDATION': {
        'max_file_size': 50 * 1024 * 1024,  # 50MB
        'allowed_extensions': {'txt', 'csv'},
        'max_filename_length': 255
    }
}

def get_secure_session_config():
    """Get secure session configuration."""
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    return {
        'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32)),
        'SESSION_COOKIE_SECURE': is_production or SECURITY_CONFIG['SESSION_SECURITY']['secure'],
        'SESSION_COOKIE_HTTPONLY': SECURITY_CONFIG['SESSION_SECURITY']['httponly'],
        'SESSION_COOKIE_SAMESITE': SECURITY_CONFIG['SESSION_SECURITY']['samesite'],
        'PERMANENT_SESSION_LIFETIME': SECURITY_CONFIG['SESSION_SECURITY']['lifetime']
    }

def secure_headers():
    """Get security headers."""
    return SECURITY_CONFIG['SECURITY_HEADERS']

def validate_spotify_credentials():
    """Validate Spotify credentials are properly configured."""
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    
    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
    
    if not redirect_uri:
        raise ValueError("SPOTIFY_REDIRECT_URI must be set")
    
    return True

def log_security_event(event_type, details):
    """Log security events."""
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Security Event - {event_type}: {details}")

def rate_limit_check(client_ip, request_count):
    """Check if client has exceeded rate limit."""
    # Simple in-memory rate limiting (use Redis in production)
    # This is a basic implementation
    return request_count <= SECURITY_CONFIG['RATE_LIMIT']['requests_per_minute']

def validate_input(data, input_type):
    """Validate input data based on type."""
    if input_type == 'filename':
        if len(data) > SECURITY_CONFIG['INPUT_VALIDATION']['max_filename_length']:
            return False, "Filename too long"
        if not data.replace('.', '').replace('-', '').replace('_', '').isalnum():
            return False, "Invalid filename characters"
    
    return True, "Valid"
