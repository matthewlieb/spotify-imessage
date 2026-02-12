#!/usr/bin/env python3
"""
Development server for spotify-message React app.

This server serves the React app and provides API endpoints for development.
In production, you would use a proper web server like nginx.
"""

import os
import subprocess
import tempfile
import json
import sqlite3
import shutil
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading

# Import resilience systems
try:
    from api_resilience import (
        resilient_api_call, check_system_health, 
        api_adapter, version_manager, degradation_handler
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    print("Warning: API resilience module not available. Running in basic mode.")
import logging
import traceback

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")

# Import security and error handling modules
try:
    from security_config import (
        SECURITY_CONFIG, get_secure_session_config, secure_headers,
        validate_spotify_credentials, log_security_event
    )
    from error_handler import (
        handle_api_error, handle_spotify_error, handle_file_error,
        safe_api_call, register_error_handlers, log_request_info
    )
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    print("Warning: Security modules not available. Running in basic mode.")

# Configure logging: INFO in production to reduce I/O; DEBUG only when FLASK_DEBUG=1
_log_level = logging.DEBUG if os.getenv('FLASK_DEBUG') == '1' else logging.INFO
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('flask_server.log')
    ]
)
logger = logging.getLogger(__name__)
import queue

# Spotify API imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("Warning: spotipy not available. Playlist name lookup disabled.")

# Redis caching imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis not available. Caching disabled.")

# Session management for OAuth
from flask import session, redirect, url_for
import secrets

app = Flask(__name__)

# Apply security configuration
if SECURITY_AVAILABLE:
    # Set secure session configuration
    session_config = get_secure_session_config()
    for key, value in session_config.items():
        app.config[key] = value

    # Enable CORS with security settings
    CORS(app, supports_credentials=True, origins=SECURITY_CONFIG['CORS_ORIGINS'])
    
    # Register error handlers
    register_error_handlers(app)
    
    # Validate Spotify credentials
    try:
        validate_spotify_credentials()
        logger.info("✅ Spotify credentials validated")
    except ValueError as e:
        logger.error(f"❌ Spotify credentials validation failed: {e}")
        raise
else:
    # Basic CORS for development
    CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configure session settings for better reliability (Spotify OAuth best practices)
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for both localhost and 127.0.0.1
app.config['SESSION_COOKIE_PATH'] = '/'  # Ensure cookie is available for all paths
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security: prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cross-site cookies for OAuth redirect
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24  # 24 hours (Spotify tokens last 1 hour, refresh when needed)

logger.info("Flask app created successfully")
logger.info("CORS enabled")  # Enable CORS for development

# Apply security headers to all responses
if SECURITY_AVAILABLE:
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        headers = secure_headers()
        for header, value in headers.items():
            response.headers[header] = value
        return response

# Initialize Redis cache
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            db=int(os.environ.get('REDIS_DB', 0)),
            decode_responses=True
        )
        # Test connection
        redis_client.ping()
        logger.info("Redis cache connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'csv'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables for processing status
processing_status = {}
status_queue = queue.Queue()

# Store OAuth states temporarily (in production, use Redis or database)
oauth_states = {}

# Store temporary auth tokens (in production, use Redis or database)
temp_auth_tokens = {}

# Spotify configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8004/callback')

# Frontend URL configuration (for OAuth redirects)
# Note: Spotify no longer supports 'localhost' - must use '127.0.0.1' for local dev
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://127.0.0.1:3000')

# Validate required environment variables
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables")

# OAuth scope for Spotify
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private user-read-private"

# Cache helper functions
def get_cache_key(prefix, *args):
    """Generate a cache key from prefix and arguments."""
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def get_from_cache(key, default=None):
    """Get value from Redis cache."""
    if not redis_client:
        return default
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return default
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return default

def set_cache(key, value, expire=3600):
    """Set value in Redis cache with expiration."""
    if not redis_client:
        return False
    try:
        redis_client.setex(key, expire, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False

def invalidate_cache_pattern(pattern):
    """Invalidate cache entries matching a pattern."""
    if not redis_client:
        return False
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")
        return False

def get_spotify_client():
    """Get authenticated Spotify client from session with token refresh."""
    if not SPOTIFY_AVAILABLE:
        return None
    
    try:
        # Check if user is authenticated via session
        if 'spotify_token' not in session:
            logger.debug("No spotify_token in session")
            return None
        
        token_info = session['spotify_token']
        access_token = token_info.get('access_token')
        
        if not access_token:
            logger.warning("No access_token in session token_info")
            return None
        
        # Create Spotify client with session token
        sp = spotipy.Spotify(auth=access_token)
        
        # Test the token by making a simple API call
        try:
            sp.current_user()
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 401:
                logger.warning("Access token expired, attempting refresh")
                # Try to refresh the token
                oauth = get_spotify_oauth()
                if oauth and 'refresh_token' in token_info:
                    try:
                        new_token_info = oauth.refresh_access_token(token_info['refresh_token'])
                        session['spotify_token'] = new_token_info
                        session.modified = True
                        sp = spotipy.Spotify(auth=new_token_info['access_token'])
                        logger.info("Token refreshed successfully")
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed: {refresh_error}")
                        session.pop('spotify_token', None)
                        return None
                else:
                    logger.warning("No refresh token available")
                    session.pop('spotify_token', None)
                    return None
        
        return sp
    except Exception as e:
        logger.error(f"Error initializing Spotify client: {e}")
        # Clear invalid token from session
        session.pop('spotify_token', None)
        return None

def get_spotify_oauth():
    """Get Spotify OAuth manager."""
    if not SPOTIFY_AVAILABLE:
        return None
    
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE
    )

# Regex for Spotify IDs
SPOTIFY_ID_RE = re.compile(r"[A-Za-z0-9]{22}")

def _validate_playlist_id(playlist_id: str) -> None:
    """Validate Spotify playlist ID format."""
    if not playlist_id or len(playlist_id) != 22 or not SPOTIFY_ID_RE.fullmatch(playlist_id):
        raise ValueError(f"Invalid playlist ID: {playlist_id}. Expected 22-character alphanumeric string.")

def _existing_track_ids(sp, playlist_id: str) -> set:
    """Get set of existing track IDs in a playlist."""
    try:
        existing = set()
        results = sp.playlist_items(playlist_id, fields='items(track(id))')
        for item in results.get('items', []):
            if item.get('track') and item['track'].get('id'):
                existing.add(item['track']['id'])
        return existing
    except Exception as e:
        logger.error(f"Error fetching existing tracks: {e}")
        return set()

def search_playlist_by_name(playlist_name):
    """Search for a playlist by name and return its ID."""
    sp = get_spotify_client()
    if not sp:
        return None
    
    try:
        # Search for playlists with the given name
        results = sp.search(q=playlist_name, type='playlist', limit=10)
        playlists = results['playlists']['items']
        
        # Find exact match (case-insensitive)
        for playlist in playlists:
            if playlist['name'].lower() == playlist_name.lower():
                return {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'owner': playlist['owner']['display_name'],
                    'tracks': playlist['tracks']['total']
                }
        
        # If no exact match, return first result
        if playlists:
            playlist = playlists[0]
            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'owner': playlist['owner']['display_name'],
                'tracks': playlist['tracks']['total']
            }
        
        return None
    except Exception as e:
        print(f"Error searching playlist: {e}")
        return None

def create_new_playlist(playlist_name, description=""):
    """Create a new playlist and return its ID."""
    sp = get_spotify_client()
    if not sp:
        return None
    
    try:
        # Get current user
        user = sp.current_user()
        
        # Create playlist
        playlist = sp.user_playlist_create(
            user=user['id'],
            name=playlist_name,
            description=description or f"Created by spotify-message from chat messages"
        )
        
        return {
            'id': playlist['id'],
            'name': playlist['name'],
            'owner': user['display_name'],
            'tracks': 0
        }
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return None


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def scan_imessage_chats():
    """Scan iMessage database for chats with Spotify links using imessage-exporter pipeline."""
    try:
        # Check cache first
        cache_key = get_cache_key('imessage_scan')
        cached_chats = get_from_cache(cache_key)
        if cached_chats is not None:
            logger.info("Returning cached iMessage scan results")
            return cached_chats
        
        # Create a temporary directory for export
        temp_dir = tempfile.mkdtemp(prefix="spotify_scan_")
        
        # Use imessage-exporter to export all chats
        export_cmd = [
            'imessage-exporter',
            '--format', 'txt',
            '--db-path', os.path.expanduser("~/Library/Messages/chat.db"),
            '--export-path', temp_dir
        ]
        
        result = subprocess.run(
            export_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            return {'error': f'Failed to export messages: {result.stderr}'}
        
        # Find all exported chat files
        chat_files = []
        for file in os.listdir(temp_dir):
            if file.endswith('.txt'):
                chat_files.append(os.path.join(temp_dir, file))
        
        chats = []
        
        # Process each chat file to find Spotify links
        for chat_file in chat_files:
            raw_chat_name = os.path.basename(chat_file).replace('.txt', '')
            # Clean up chat name by removing ID numbers (e.g., "Chat Name - 4" -> "Chat Name")
            chat_name = raw_chat_name
            if ' - ' in raw_chat_name:
                # Remove the ID part (e.g., " - 4", " - 10")
                parts = raw_chat_name.split(' - ')
                if len(parts) > 1 and parts[-1].isdigit():
                    chat_name = ' - '.join(parts[:-1])
            
            # Use grep to find Spotify track URLs
            grep_cmd = [
                'grep', '-Eo', 'open\\.spotify\\.com/track/[A-Za-z0-9]+',
                chat_file
            ]
            
            grep_result = subprocess.run(
                grep_cmd,
                capture_output=True,
                text=True
            )
            
            if grep_result.returncode == 0 and grep_result.stdout.strip():
                # Count unique track IDs
                track_ids = set()
                for line in grep_result.stdout.strip().split('\n'):
                    if line:
                        track_id = line.split('/')[-1]
                        if len(track_id) == 22:  # Valid Spotify track ID length
                            track_ids.add(track_id)
                
                if track_ids:
                    # Get file modification time as last activity
                    mtime = os.path.getmtime(chat_file)
                    last_date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    ids_list = list(track_ids)
                    chats.append({
                        'name': chat_name,
                        'type': 'imessage',
                        'trackCount': len(ids_list),
                        'trackIds': ids_list,
                        'lastActivity': last_date_str
                    })
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Sort by track count (most tracks first)
        chats.sort(key=lambda x: x['trackCount'], reverse=True)
        
        # Cache the results for 30 minutes
        result = {'success': True, 'chats': chats}
        set_cache(cache_key, result, expire=1800)
        
        return result
        
    except subprocess.TimeoutExpired:
        return {'error': 'Export timed out after 5 minutes'}
    except Exception as e:
        return {'error': f'Error scanning iMessage: {str(e)}'}


def run_spotify_message_command(command_type, options, chat_name=None):
    """Run spotify-message command and capture output."""
    try:
        # Build command based on type - use the installed CLI
        if command_type == 'imessage':
            cmd = ['spotify-imessage', 'imessage', '--chat', chat_name]
        elif command_type == 'android':
            cmd = ['spotify-imessage', 'android-cmd', '--file', options.get('file_path', '')]
        elif command_type == 'file':
            cmd = ['spotify-imessage', 'file', '--file', options.get('file_path', '')]
        else:
            return {'error': f'Unknown command type: {command_type}'}
        
        # Add options
        for key, value in options.items():
            if value and value != '' and key != 'file_path':
                if key == 'playlist_id':
                    cmd.extend(['--playlist', value])
                elif key == 'start_date':
                    cmd.extend(['--start-date', value])
                elif key == 'end_date':
                    cmd.extend(['--end-date', value])
                elif key == 'days_back':
                    cmd.extend(['--days-back', str(value)])
                elif key == 'show_metadata' and value:
                    cmd.append('--show-metadata')
                elif key == 'dry_run' and value:
                    cmd.append('--dry-run')
                elif key == 'stats' and value:
                    cmd.append('--stats')
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Parse track count from output
        tracks_found = 0
        tracks_added = 0
        if result.returncode == 0:
            import re
            
            # Look for "Found X Spotify tracks" pattern (total found)
            match = re.search(r'Found (\d+) Spotify tracks', result.stdout)
            if match:
                tracks_found = int(match.group(1))
            
            # Look for "Added X tracks" pattern (actually added)
            added_match = re.search(r'Added (\d+) tracks', result.stdout)
            if added_match:
                tracks_added = int(added_match.group(1))
            elif 'Nothing new to add' in result.stdout:
                tracks_added = 0
            else:
                # If no specific "Added" message, assume all were added (for backward compatibility)
                tracks_added = tracks_found
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'tracks_found': tracks_found,
            'tracks_added': tracks_added
        }
        
    except subprocess.TimeoutExpired:
        return {'error': 'Command timed out after 5 minutes'}
    except Exception as e:
        return {'error': f'Error running command: {str(e)}'}


@app.route('/api/scan-imessage', methods=['POST'])
def scan_imessage():
    """Scan iMessage database for chats with Spotify links."""
    try:
        result = scan_imessage_chats()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/search', methods=['POST'])
def search_playlist():
    """Search for a playlist by name."""
    try:
        data = request.get_json()
        playlist_name = data.get('name', '').strip()
        
        if not playlist_name:
            return jsonify({'error': 'Playlist name is required'}), 400
        
        playlist = search_playlist_by_name(playlist_name)
        
        if playlist:
            return jsonify({
                'success': True,
                'playlist': playlist,
                'message': f"Found playlist: {playlist['name']} by {playlist['owner']} ({playlist['tracks']} tracks)"
            })
        else:
            return jsonify({
                'success': False,
                'message': f"No playlist found with name '{playlist_name}'"
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/create', methods=['POST'])
def create_playlist():
    """Create a new playlist."""
    try:
        data = request.get_json()
        playlist_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not playlist_name:
            return jsonify({'error': 'Playlist name is required'}), 400
        
        playlist = create_new_playlist(playlist_name, description)
        
        if playlist:
            return jsonify({
                'success': True,
                'playlist': playlist,
                'message': f"Created new playlist: {playlist['name']}"
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create playlist'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/playlist/add-tracks', methods=['POST'])
def add_tracks_to_playlist():
    """Add specific track IDs to a playlist using Spotify API directly."""
    try:
        data = request.get_json()
        playlist_id = data.get('playlist_id')
        track_ids = data.get('track_ids', [])
        
        if not playlist_id:
            return jsonify({'error': 'Playlist ID is required'}), 400
        
        if not track_ids or len(track_ids) == 0:
            return jsonify({'error': 'At least one track ID is required'}), 400
        
        # Validate playlist ID format
        _validate_playlist_id(playlist_id)
        
        # Get Spotify client
        sp = get_spotify_client()
        if not sp:
            return jsonify({'error': 'Spotify authentication required'}), 401
        
        # Validate track IDs
        valid_track_ids = []
        for tid in track_ids:
            if SPOTIFY_ID_RE.fullmatch(tid):
                valid_track_ids.append(tid)
        
        if not valid_track_ids:
            return jsonify({'error': 'No valid track IDs provided'}), 400
        
        # Check for existing tracks (deduplication)
        existing = _existing_track_ids(sp, playlist_id)
        new_tracks = [tid for tid in valid_track_ids if tid not in existing]
        
        if not new_tracks:
            return jsonify({
                'success': True,
                'tracks_added': 0,
                'message': 'All selected tracks are already in the playlist'
            })
        
        # Convert to URIs and add in batches of 100
        uris = [f"spotify:track:{tid}" for tid in new_tracks]
        tracks_added = 0
        
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            try:
                sp.playlist_add_items(playlist_id, batch)
                tracks_added += len(batch)
            except Exception as e:
                logger.error(f"Error adding batch {i//100 + 1}: {e}")
                # Continue with next batch
        
        return jsonify({
            'success': True,
            'tracks_added': tracks_added,
            'message': f'Successfully added {tracks_added} track(s) to playlist'
        })
        
    except Exception as e:
        logger.error(f"Error adding tracks to playlist: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-chat', methods=['POST'])
def process_chat():
    """Process a specific chat with spotify-message."""
    try:
        data = request.get_json()
        chat_name = data.get('chat_name')
        command_type = data.get('command_type', 'imessage')
        options = data.get('options', {})
        
        if not chat_name:
            return jsonify({'error': 'Chat name is required'}), 400
        
        # Generate job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start processing in background
        def process_in_background():
            processing_status[job_id] = {
                'status': 'processing',
                'progress': 0,
                'message': 'Starting processing...'
            }
            
            # Run the command
            result = run_spotify_message_command(command_type, options, chat_name)
            
            if result.get('success'):
                processing_status[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Processing completed successfully',
                    'output': result.get('stdout', ''),
                    'tracks_found': result.get('tracks_found', 0),
                    'tracks_added': result.get('tracks_added', 0)
                }
            else:
                processing_status[job_id] = {
                    'status': 'error',
                    'progress': 100,
                    'message': result.get('error', 'Processing failed'),
                    'error': result.get('stderr', '')
                }
        
        thread = threading.Thread(target=process_in_background)
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get processing options
        options = request.form.get('options', '{}')
        options = json.loads(options)
        
        # Generate job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start processing in background
        def process_in_background():
            processing_status[job_id] = {
                'status': 'processing',
                'progress': 0,
                'message': 'Starting file processing...'
            }
            
            # Add file path to options
            options['file_path'] = file_path
            
            # Run the command
            result = run_spotify_message_command('file', options)
            
            if result.get('success'):
                processing_status[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'File processing completed successfully',
                    'output': result.get('stdout', ''),
                    'tracks_found': result.get('tracks_found', 0),
                    'tracks_added': result.get('tracks_added', 0)
                }
            else:
                processing_status[job_id] = {
                    'status': 'error',
                    'progress': 100,
                    'message': result.get('error', 'File processing failed'),
                    'error': result.get('stderr', '')
                }
        
        thread = threading.Thread(target=process_in_background)
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'File uploaded and processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<job_id>')
def get_job_status(job_id):
    """Get the status of a processing job."""
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(processing_status[job_id])


@app.route('/api/download/<job_id>')
def download_result(job_id):
    """Download the result file for a completed job."""
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    job = processing_status[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    # Create a temporary file with the output
    output = job.get('output', 'No output available')
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    temp_file.write(output)
    temp_file.close()
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'spotify_message-result-{job_id}.txt'
    )


@app.route('/api/stats')
def get_stats():
    """Get application statistics."""
    total_jobs = len(processing_status)
    completed_jobs = len([j for j in processing_status.values() if j['status'] == 'completed'])
    error_jobs = len([j for j in processing_status.values() if j['status'] == 'error'])
    processing_jobs = len([j for j in processing_status.values() if j['status'] == 'processing'])
    
    return jsonify({
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'error_jobs': error_jobs,
        'processing_jobs': processing_jobs,
        'uptime': 'Running'
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint with resilience status."""
    logger.info("Health check endpoint called")
    try:
        response = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        
        # Add resilience status if available
        if RESILIENCE_AVAILABLE:
            try:
                system_health = check_system_health()
                response['resilience'] = {
                    'api_status': system_health.get('api_status', 'unknown'),
                    'compatibility': system_health.get('compatibility', {}),
                    'degradation_mode': False
                }
            except Exception as resilience_error:
                logger.warning(f"Resilience check failed: {resilience_error}")
                response['resilience'] = {'error': 'Resilience check unavailable'}
        else:
            response['resilience'] = {'status': 'basic_mode'}
        
        logger.info(f"Health check response: {response}")

        json_response = jsonify(response)
        
        # Add security headers if available
        if SECURITY_AVAILABLE:
            for header, value in secure_headers().items():
                json_response.headers[header] = value

        return json_response
    except Exception as e:
        logger.error(f"Health check error: {e}")
        logger.error(traceback.format_exc())
        return handle_api_error(e, "Health check failed")

@app.route('/api/track-details', methods=['POST'])
def get_track_details():
    """Get detailed track information for a chat using real data from Smart Detection, or from track_ids"""
    try:
        data = request.get_json()
        chat_name = data.get('chat_name')
        track_ids = data.get('track_ids', [])
        
        # Support both chat_name and track_ids
        if track_ids and len(track_ids) > 0:
            # Direct track IDs provided (e.g., from pasted text)
            logger.info(f"Getting track details for {len(track_ids)} track IDs")
            
            sp = get_spotify_client()
            if not sp:
                return jsonify({
                    'success': False,
                    'error': 'Spotify authentication required. Please log out and sign in again.',
                    'requires_auth': True
                }), 401
            
            # Get track details in batches (Spotify API limit is 50 tracks per request)
            tracks = []
            for i in range(0, len(track_ids), 50):
                batch_ids = track_ids[i:i+50]
                try:
                    batch_tracks = sp.tracks(batch_ids)
                    for track in batch_tracks['tracks']:
                        if track:
                            tracks.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                'album': track['album']['name'],
                                'album_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                'duration': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
                                'preview_url': track.get('preview_url'),
                                'external_url': track['external_urls']['spotify']
                            })
                except Exception as e:
                    logger.error(f"Error fetching batch of tracks: {e}")
                    continue
            
            return jsonify({
                'success': True,
                'tracks': tracks
            })
        
        if not chat_name:
            return jsonify({'success': False, 'error': 'Chat name or track_ids required'}), 400
        
        logger.info(f"Getting track details for chat: {chat_name}")
        
        # Check cache first
        cache_key = get_cache_key('track_details', chat_name)
        cached_tracks = get_from_cache(cache_key)
        if cached_tracks is not None:
            logger.info(f"Returning cached track details for {chat_name}")
            return jsonify({
                'success': True,
                'tracks': cached_tracks
            })
        
        # Use the same method as Smart Detection to get real track data
        try:
            # Create a temporary directory for export
            temp_dir = tempfile.mkdtemp(prefix="spotify_track_details_")
            
            # Use imessage-exporter to export all chats (since --chat-name is not supported)
            export_cmd = [
                'imessage-exporter',
                '--format', 'txt',
                '--db-path', os.path.expanduser("~/Library/Messages/chat.db"),
                '--export-path', temp_dir
            ]
            
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to export chat {chat_name}: {result.stderr}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to export chat: {result.stderr}'
                }), 500
            
            # Find the exported chat file that matches the requested chat name
            chat_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.txt'):
                    # Check if this file matches the requested chat name
                    file_base_name = file.replace('.txt', '')
                    
                    # Try exact match first
                    if file_base_name == chat_name:
                        chat_file = os.path.join(temp_dir, file)
                        break
                    
                    # Try match without ID suffix (e.g., "Chat Name - 4" matches "Chat Name")
                    if ' - ' in file_base_name:
                        parts = file_base_name.split(' - ')
                        if len(parts) > 1 and parts[-1].isdigit():
                            base_name = ' - '.join(parts[:-1])
                            if base_name == chat_name:
                                chat_file = os.path.join(temp_dir, file)
                                break
                    
                    # Try fuzzy matching for chat names with emojis or special characters
                    # Remove emojis and special characters for comparison
                    import re
                    clean_file_name = re.sub(r'[^\w\s-]', '', file_base_name).strip()
                    clean_chat_name = re.sub(r'[^\w\s-]', '', chat_name).strip()
                    
                    # Try match without ID suffix on cleaned names
                    if ' - ' in clean_file_name:
                        clean_parts = clean_file_name.split(' - ')
                        if len(clean_parts) > 1 and clean_parts[-1].isdigit():
                            clean_base_name = ' - '.join(clean_parts[:-1])
                            if clean_base_name.lower() == clean_chat_name.lower():
                                chat_file = os.path.join(temp_dir, file)
                                break
                    
                    # Try direct fuzzy match on cleaned names
                    if clean_file_name.lower() == clean_chat_name.lower():
                        chat_file = os.path.join(temp_dir, file)
                        break
            
            if not chat_file:
                return jsonify({
                    'success': False,
                    'error': f'No chat file found for "{chat_name}" after export'
                }), 500
            
            # Extract Spotify track IDs and their order in the chat
            # Use the order they appear in the chat as a proxy for when they were sent
            track_data = {}  # track_id -> order_index
            track_order = []  # List to maintain order of tracks as they appear
            
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split content into lines and process each line
                lines = content.split('\n')
                for line_index, line in enumerate(lines):
                    if 'open.spotify.com/track/' in line:
                        # Extract track ID
                        track_id = None
                        for part in line.split():
                            if 'open.spotify.com/track/' in part:
                                # Extract track ID from URL
                                track_id = part.split('/track/')[-1]
                                # Remove any query parameters or fragments
                                track_id = track_id.split('?')[0].split('#')[0]
                                if len(track_id) == 22:  # Valid Spotify track ID length
                                    break
                        
                        if track_id and len(track_id) == 22 and track_id.isalnum():
                            # Use the order they appear in the chat as the "sent" order
                            # This gives us a chronological sequence based on chat position
                            if track_id not in track_data:  # Avoid duplicates
                                track_data[track_id] = len(track_order)  # Store order index
                                track_order.append(track_id)  # Maintain order
                                
            except Exception as e:
                logger.warning(f"Error reading chat file for timestamps: {e}")
                # Fallback to simple grep approach
                grep_cmd = [
                    'grep', '-Eo', 'open\\.spotify\\.com/track/[A-Za-z0-9]+',
                    chat_file
                ]
                
                grep_result = subprocess.run(
                    grep_cmd,
                    capture_output=True,
                    text=True
                )
                
                if grep_result.returncode == 0 and grep_result.stdout.strip():
                    for line in grep_result.stdout.strip().split('\n'):
                        if 'open.spotify.com/track/' in line:
                            track_id = line.split('/track/')[-1]
                            if len(track_id) == 22:
                                track_data[track_id] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if not track_data:
                return jsonify({
                    'success': True,
                    'tracks': []
                })
            
            # Get track details from Spotify API
            try:
                sp = get_spotify_client()
                if not sp:
                    logger.error("Spotify client not available - authentication required")
                    return jsonify({
                        'success': False,
                        'error': 'Spotify authentication required. Please log out and sign in again.',
                        'requires_auth': True
                    }), 401
                
                # Get track details in batches (Spotify API limit is 50 tracks per request)
                tracks = []
                track_ids_list = list(track_data.keys())
                
                # Debug: Log first few track IDs to see what we're working with
                logger.info(f"First 5 track IDs extracted: {track_ids_list[:5]}")
                
                for i in range(0, len(track_ids_list), 50):
                    batch_ids = track_ids_list[i:i+50]
                    logger.info(f"Processing batch {i//50 + 1}: {len(batch_ids)} track IDs")
                    logger.debug(f"Batch track IDs: {batch_ids}")
                    
                    try:
                        track_details = sp.tracks(batch_ids)
                    except spotipy.exceptions.SpotifyException as e:
                        logger.error(f"Spotify API error for batch: {e}")
                        # If it's an auth error, return error immediately
                        if e.http_status == 401 or e.http_status == 403:
                            return jsonify({
                                'success': False,
                                'error': 'Spotify authentication expired. Please log out and sign in again.',
                                'requires_auth': True
                            }), 401
                        logger.error(f"Problematic track IDs: {batch_ids}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error fetching tracks: {e}")
                        continue
                    
                    for idx, track in enumerate(track_details['tracks']):
                        if track:  # Skip None tracks (invalid IDs)
                            track_id = track['id']
                            sent_order = track_data.get(track_id, 0) # Get order in chat
                            
                            # Get album art (prefer largest, fallback to medium, then small)
                            album_art = None
                            if track.get('album') and track['album'].get('images'):
                                # Sort by width descending to get largest first
                                images = sorted(track['album']['images'], key=lambda x: x.get('width', 0), reverse=True)
                                album_art = images[0]['url'] if images else None
                            
                            # Format duration
                            duration_ms = track.get('duration_ms', 0)
                            minutes = duration_ms // 60000
                            seconds = (duration_ms % 60000) // 1000
                            duration = f"{minutes}:{seconds:02d}"
                            
                            # Get artist names
                            artist_names = ', '.join([artist['name'] for artist in track.get('artists', [])])
                            
                            # Validate track data before adding
                            if track.get('name') and track.get('artists'):
                                tracks.append({
                                    'id': track_id,
                                    'name': track['name'],
                                    'artist': artist_names,
                                    'album': track.get('album', {}).get('name', 'Unknown Album'),
                                    'duration': duration,
                                    'spotify_url': track.get('external_urls', {}).get('spotify', ''),
                                    'album_art': album_art,
                                    'release_date': track.get('album', {}).get('release_date', ''),
                                    'popularity': track.get('popularity', 0),
                                    'sent_order': sent_order
                                })
                            else:
                                logger.warning(f"Skipping invalid track data: {track}")
                        else:
                            # Log invalid track IDs for debugging
                            if idx < len(batch_ids):
                                invalid_id = batch_ids[idx]
                                logger.warning(f"Invalid Spotify track ID: {invalid_id}")
                
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Cache the results for 1 hour
                set_cache(cache_key, tracks, expire=3600)
                
                return jsonify({
                    'success': True,
                    'tracks': tracks
                })
                
            except Exception as e:
                logger.error(f"Error getting track details from Spotify: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to get track details from Spotify'
                }), 500
                
        except Exception as e:
            logger.error(f"Error processing chat export: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to process chat export'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in track details endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# OAuth endpoints
@app.route('/api/auth/spotify')
def spotify_login():
    """Initiate Spotify OAuth login."""
    try:
        oauth = get_spotify_oauth()
        if not oauth:
            return jsonify({'error': 'Spotify OAuth not available'}), 500
        
        # Generate state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Store state in both session and global store for redundancy
        session['oauth_state'] = state
        session.permanent = True  # Make session permanent
        oauth_states[state] = {
            'timestamp': datetime.now(),
            'used': False
        }
        
        # Get authorization URL
        auth_url = oauth.get_authorize_url(state=state)
        
        logger.info(f"Generated OAuth state: {state}")
        logger.info(f"Authorization URL: {auth_url}")
        logger.info(f"Session ID: {session.get('_id', 'No session ID')}")
        
        return jsonify({
            'auth_url': auth_url,
            'state': state
        })
    except Exception as e:
        logger.error(f"Error initiating Spotify login: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/callback')
def spotify_callback():
    """Handle Spotify OAuth callback."""
    try:
        # Get state parameter from request
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        global_state = oauth_states.get(state)
        
        logger.info(f"Callback received state: {state}")
        logger.info(f"Stored state in session: {stored_state}")
        logger.info(f"Global state exists: {global_state is not None}")
        logger.info(f"Session ID: {session.get('_id', 'No session ID')}")
        
        # Verify state parameter
        if not state:
            logger.error("No state parameter in callback")
            return jsonify({'error': 'No state parameter provided'}), 400
        
        # Check if state exists in global store (more reliable than session)
        if not global_state:
            logger.error(f"No global state found for: {state}")
            return jsonify({'error': 'Invalid or expired state parameter'}), 400
        
        # Check if state was already used
        if global_state.get('used', False):
            logger.error(f"State already used: {state}")
            return jsonify({'error': 'State parameter already used'}), 400
        
        # Verify state matches session (if session exists)
        if stored_state and state != stored_state:
            logger.error(f"State mismatch: received={state}, stored={stored_state}")
            return jsonify({'error': 'Invalid state parameter'}), 400
        
        # Mark state as used in global store
        oauth_states[state]['used'] = True
        # Don't clear the oauth_state from session yet - do it after storing user data
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'Authorization code not provided'}), 400
        
        # Exchange authorization code for access token (Spotify best practice: do this immediately)
        # Reference: https://developer.spotify.com/documentation/web-api/concepts/authorization
        oauth = get_spotify_oauth()
        if not oauth:
            return jsonify({'error': 'Spotify OAuth not available'}), 500
        
        token_info = oauth.get_access_token(code)
        
        if not token_info or 'access_token' not in token_info:
            logger.error("Failed to get access token from Spotify")
            return redirect(f'{FRONTEND_URL}?spotify_auth=error')
        
        # Get user info immediately (validate token works)
        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])
            user = sp.current_user()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return redirect(f'{FRONTEND_URL}?spotify_auth=error')
        
        # Store token and user in session (session is source of truth)
        session['spotify_token'] = token_info
        session['spotify_user'] = {
            'id': user['id'],
            'display_name': user['display_name'],
            'email': user.get('email', ''),
            'country': user.get('country', ''),
            'product': user.get('product', '')
        }
        
        # Clear oauth_state from session
        if 'oauth_state' in session:
            del session['oauth_state']
        
        # Mark session as permanent and modified
        session.permanent = True
        session.modified = True
        
        logger.info(f"✅ OAuth callback successful - stored token and user in session")
        logger.info(f"Session keys: {list(session.keys())}")
        
        # Generate temporary token for frontend (optional - session already has everything)
        # This allows frontend to verify, but session is the real source of truth
        auth_token = secrets.token_urlsafe(32)
        temp_auth_tokens[auth_token] = {
            'spotify_token': token_info,
            'spotify_user': session['spotify_user'],
            'timestamp': datetime.now()
        }
        
        # Redirect to frontend - session is already set, frontend just needs to check status
        return redirect(f'{FRONTEND_URL}?spotify_auth=success&token={auth_token}')
        
    except Exception as e:
        logger.error(f"Error in Spotify callback: {e}")
        return redirect(f'{FRONTEND_URL}?spotify_auth=error')

@app.route('/api/auth/exchange-code', methods=['POST'])
def exchange_code():
    """Exchange Spotify authorization code for access token (for iOS app)."""
    try:
        data = request.get_json()
        code = data.get('code')
        redirect_uri = data.get('redirect_uri', 'spotifymessage://callback')
        
        if not code:
            return jsonify({'error': 'Authorization code is required'}), 400
        
        # Exchange code for token using Spotify OAuth
        oauth = get_spotify_oauth()
        if not oauth:
            return jsonify({'error': 'Spotify OAuth not available'}), 500
        
        # Create a custom OAuth instance with the iOS redirect URI
        from spotipy.oauth2 import SpotifyOAuth
        ios_oauth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=redirect_uri,
            scope=SPOTIFY_SCOPE
        )
        
        token_info = ios_oauth.get_access_token(code)
        
        if not token_info or 'access_token' not in token_info:
            logger.error("Failed to exchange code for token")
            return jsonify({'error': 'Failed to exchange authorization code'}), 400
        
        return jsonify({
            'access_token': token_info.get('access_token'),
            'refresh_token': token_info.get('refresh_token'),
            'expires_in': token_info.get('expires_in'),
            'token_type': token_info.get('token_type', 'Bearer')
        })
        
    except Exception as e:
        logger.error(f"Error exchanging code: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/exchange-token', methods=['POST'])
def exchange_auth_token():
    """
    Exchange temporary auth token for session data.
    
    This endpoint is idempotent - it can be called multiple times safely.
    Based on Spotify OAuth 2.0 best practices:
    - Authorization codes should be exchanged promptly
    - Session is the source of truth for authentication
    - Token exchange is only needed if session doesn't have token
    """
    try:
        data = request.get_json()
        auth_token = data.get('token')
        
        # CRITICAL: Check session FIRST (idempotent - handles React StrictMode double calls)
        if 'spotify_token' in session and 'spotify_user' in session:
            logger.info("Session already authenticated - returning existing user (idempotent)")
            return jsonify({
                'success': True,
                'message': 'Authentication successful (already authenticated)',
                'user': session['spotify_user']
            })
        
        if not auth_token:
            logger.error("No token provided in exchange request")
            return jsonify({'error': 'No token provided'}), 400
        
        # Check if token exists in temporary storage
        if auth_token not in temp_auth_tokens:
            logger.warning(f"Token not found in temp_auth_tokens. Available: {len(temp_auth_tokens)} tokens")
            # Final check - session might have been set by another request
            if 'spotify_token' in session and 'spotify_user' in session:
                logger.info("Found token in session after temp token check")
                return jsonify({
                    'success': True,
                    'message': 'Authentication successful (session found)',
                    'user': session['spotify_user']
                })
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        auth_data = temp_auth_tokens[auth_token]
        
        # Check if token is expired (5 minutes - Spotify best practice: exchange promptly)
        time_diff = (datetime.now() - auth_data['timestamp']).total_seconds()
        if time_diff > 300:  # 5 minutes
            logger.warning(f"Token expired: {time_diff} seconds old")
            # Check session one more time before failing
            if 'spotify_token' in session and 'spotify_user' in session:
                logger.info("Session has token despite expired temp token")
                return jsonify({
                    'success': True,
                    'message': 'Authentication successful (session active)',
                    'user': session['spotify_user']
                })
            del temp_auth_tokens[auth_token]
            return jsonify({'error': 'Token expired. Please sign in again.'}), 400
        
        # Store auth data in session (session is source of truth)
        session['spotify_token'] = auth_data['spotify_token']
        session['spotify_user'] = auth_data['spotify_user']
        session.permanent = True
        session.modified = True
        
        # Remove temporary token AFTER successful session storage
        # But only if we successfully stored it
        try:
            del temp_auth_tokens[auth_token]
        except KeyError:
            # Token already deleted (race condition), that's okay
            pass
        
        logger.info(f"Successfully exchanged token - session keys: {list(session.keys())}")
        logger.info(f"Token stored - has access_token: {'access_token' in session['spotify_token']}")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user': auth_data['spotify_user']
        })
        
    except Exception as e:
        logger.error(f"Error exchanging auth token: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Check session as fallback
        if 'spotify_token' in session and 'spotify_user' in session:
            logger.info("Returning session data despite error")
            return jsonify({
                'success': True,
                'message': 'Authentication successful (using session)',
                'user': session['spotify_user']
            })
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/status')
def auth_status():
    """Check authentication status."""
    try:
        logger.info(f"Auth status check - Session ID: {session.get('_id', 'No session ID')}")
        logger.info(f"Auth status check - Session keys: {list(session.keys())}")
        logger.info(f"Auth status check - Has spotify_token: {'spotify_token' in session}")
        logger.info(f"Auth status check - Has spotify_user: {'spotify_user' in session}")
        
        if 'spotify_token' not in session:
            logger.info("Auth status check - No spotify_token in session")
            return jsonify({
                'authenticated': False,
                'user': None
            })
        
        # Check if token is still valid
        sp = get_spotify_client()
        if not sp:
            # Token is invalid, clear session
            session.pop('spotify_token', None)
            session.pop('spotify_user', None)
            return jsonify({
                'authenticated': False,
                'user': None
            })
        
        # Try to get user info to verify token
        try:
            user = sp.current_user()
            return jsonify({
                'authenticated': True,
                'user': session.get('spotify_user', {
                    'id': user['id'],
                    'display_name': user['display_name'],
                    'email': user.get('email', ''),
                    'country': user.get('country', ''),
                    'product': user.get('product', '')
                })
            })
        except Exception:
            # Token is invalid, clear session
            session.pop('spotify_token', None)
            session.pop('spotify_user', None)
            return jsonify({
                'authenticated': False,
                'user': None
            })
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def spotify_logout():
    """Logout from Spotify."""
    try:
        session.pop('spotify_token', None)
        session.pop('spotify_user', None)
        session.pop('oauth_state', None)
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'error': str(e)}), 500


# Serve React app (must be last so /api/* routes match first)
@app.route('/')
def serve_react_app():
    """Serve the React app (production build)."""
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    build_path = os.path.join(build_dir, 'index.html')
    
    logger.info(f"Looking for React build at: {build_path}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Server file location: {os.path.dirname(__file__)}")
    
    # List contents of build directory if it exists
    if os.path.exists(build_dir):
        try:
            contents = os.listdir(build_dir)
            logger.info(f"Build directory exists. Contents: {contents}")
        except Exception as e:
            logger.error(f"Error listing build directory: {e}")
    else:
        logger.error(f"Build directory does not exist at: {build_dir}")
    
    if os.path.exists(build_path):
        logger.info(f"✅ Found React build, serving index.html")
        # Use absolute path for send_from_directory
        return send_from_directory(build_dir, 'index.html')
    logger.error(f"❌ React build not found at: {build_path}")
    return jsonify({'error': 'React build not found. Run npm run build or use dev server on port 3000.'}), 404


@app.route('/<path:path>')
def serve_static_files(path):
    """Serve static files from build directory (only if not /api)."""
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    file_path = os.path.join(build_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(build_dir, path)
    # SPA fallback - serve index.html for any route
    index_path = os.path.join(build_dir, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(build_dir, 'index.html')
    return jsonify({'error': 'React build not found'}), 404


if __name__ == '__main__':
    print("🚀 Starting spotify_message web server...")
    print()
    print("📱 React app will be available at: http://localhost:3000")
    print("🔧 API endpoints available at: http://localhost:8004/api/")
    print()
    
    # Check if build directory exists and log details
    build_path = os.path.join(os.path.dirname(__file__), 'build')
    print(f"🔍 Checking for React build at: {build_path}")
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"📄 Server file location: {os.path.dirname(__file__)}")
    
    if os.path.exists(build_path):
        print(f"✅ Build directory found!")
        try:
            contents = os.listdir(build_path)
            print(f"📦 Build directory contents: {contents}")
            index_path = os.path.join(build_path, 'index.html')
            if os.path.exists(index_path):
                print(f"✅ index.html found at: {index_path}")
            else:
                print(f"❌ index.html NOT found in build directory")
        except Exception as e:
            print(f"⚠️  Error listing build directory: {e}")
    else:
        print("⚠️  Build directory not found.")
        print("Please run 'npm run build' first.")
        print()
        print("   For development, you can run the React dev server with 'npm start'")
        print()
    
def find_available_port(start_port=8004):
    """Find an available port starting from start_port."""
    import socket
    
    port = start_port
    while port < 9000:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    
    raise RuntimeError(f"No available ports found between {start_port} and 9000")

if __name__ == "__main__":
    try:
        import os
        
        # Check if running in production
        if os.getenv('PORT'):
            # Production deployment (Railway, Heroku, etc.)
            port = int(os.getenv('PORT'))
            debug = False
            print(f"🚀 Starting spotify_message web server in PRODUCTION mode...")
            print(f"🔧 API endpoints available at: http://localhost:{port}/api/")
        else:
            # Development mode
            port = find_available_port(8004)
            debug = False
            print(f"🚀 Starting spotify_message web server...")
            print(f"📱 React app will be available at: http://localhost:3000")
            print(f"🔧 API endpoints available at: http://localhost:{port}/api/")
        
        # Verify build directory exists before starting
        build_dir = os.path.join(os.path.dirname(__file__), 'build')
        logger.info(f"Checking for React build at: {build_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Server file location: {os.path.dirname(__file__)}")
        
        if os.path.exists(build_dir):
            contents = os.listdir(build_dir)
            logger.info(f"✅ Build directory found! Contents: {contents}")
            index_path = os.path.join(build_dir, 'index.html')
            if os.path.exists(index_path):
                logger.info(f"✅ index.html found at: {index_path}")
            else:
                logger.error(f"❌ index.html NOT found in build directory")
        else:
            logger.error(f"❌ Build directory does not exist at: {build_dir}")
        
        logger.info(f"Starting Flask server on port {port}")
        print(f"🚀 Flask server starting on port {port}")
        print(f"🔧 API endpoints: http://localhost:{port}/api/")
        
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        logger.error(traceback.format_exc())
        raise
