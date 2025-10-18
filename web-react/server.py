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
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import logging
import traceback

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
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
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])

# Configure session for OAuth
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configure session settings for better reliability
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JavaScript access for debugging
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for both localhost and 127.0.0.1
app.config['SESSION_COOKIE_PATH'] = '/'  # Ensure cookie is available for all paths
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

logger.info("Flask app created successfully")
logger.info("CORS enabled")  # Enable CORS for development

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
    """Get authenticated Spotify client from session."""
    if not SPOTIFY_AVAILABLE:
        return None
    
    try:
        # Check if user is authenticated via session
        if 'spotify_token' not in session:
            return None
        
        # Create Spotify client with session token
        sp = spotipy.Spotify(auth=session['spotify_token']['access_token'])
        return sp
    except Exception as e:
        print(f"Error initializing Spotify client: {e}")
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
                    
                    chats.append({
                        'name': chat_name,
                        'type': 'imessage',
                        'trackCount': len(track_ids),
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
        # Build command based on type
        if command_type == 'imessage':
            cmd = ['spotify_message', 'imessage', '--chat', chat_name]
        elif command_type == 'android':
            cmd = ['spotify_message', 'android', '--file', options.get('file_path', '')]
        elif command_type == 'file':
            cmd = ['spotify_message', 'file', '--input', options.get('file_path', '')]
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


@app.route('/')
def serve_react_app():
    """Serve the React app."""
    return send_from_directory('build', 'index.html')


@app.route('/<path:path>')
def serve_static_files(path):
    """Serve static files from build directory."""
    return send_from_directory('build', path)


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
    """Health check endpoint."""
    logger.info("Health check endpoint called")
    try:
        response = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        logger.info(f"Health check response: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/track-details', methods=['POST'])
def get_track_details():
    """Get detailed track information for a chat using real data from Smart Detection"""
    try:
        data = request.get_json()
        chat_name = data.get('chat_name')
        
        if not chat_name:
            return jsonify({'success': False, 'error': 'Chat name required'}), 400
        
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
                    # The file might have an ID suffix, so we need to match the base name
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
            
            if not chat_file:
                return jsonify({
                    'success': False,
                    'error': f'No chat file found for "{chat_name}" after export'
                }), 500
            
            # Extract Spotify track IDs from the chat file
            grep_cmd = [
                'grep', '-Eo', 'open\\.spotify\\.com/track/[A-Za-z0-9]+',
                chat_file
            ]
            
            grep_result = subprocess.run(
                grep_cmd,
                capture_output=True,
                text=True
            )
            
            if grep_result.returncode != 0 or not grep_result.stdout.strip():
                return jsonify({
                    'success': True,
                    'tracks': []
                })
            
            # Extract unique track IDs
            track_ids = set()
            for line in grep_result.stdout.strip().split('\n'):
                if 'open.spotify.com/track/' in line:
                    track_id = line.split('/track/')[-1]
                    if len(track_id) == 22:  # Valid Spotify track ID length
                        track_ids.add(track_id)
            
            if not track_ids:
                return jsonify({
                    'success': True,
                    'tracks': []
                })
            
            # Get track details from Spotify API
            try:
                sp = get_spotify_client()
                if not sp:
                    return jsonify({
                        'success': False,
                        'error': 'Spotify authentication required'
                    }), 401
                
                # Get track details in batches (Spotify API limit is 50 tracks per request)
                tracks = []
                track_ids_list = list(track_ids)
                
                for i in range(0, len(track_ids_list), 50):
                    batch_ids = track_ids_list[i:i+50]
                    track_details = sp.tracks(batch_ids)
                    
                    for track in track_details['tracks']:
                        if track:  # Skip None tracks (invalid IDs)
                            tracks.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                                'album': track['album']['name'],
                                'duration': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
                                'spotify_url': track['external_urls']['spotify'],
                                'album_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                'release_date': track['album']['release_date'],
                                'popularity': track['popularity']
                            })
                
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
        
        # Exchange code for token
        oauth = get_spotify_oauth()
        if not oauth:
            return jsonify({'error': 'Spotify OAuth not available'}), 500
        
        token_info = oauth.get_access_token(code)
        
        # Store token in session
        session['spotify_token'] = token_info
        logger.info(f"Stored spotify_token in session: {bool(session.get('spotify_token'))}")
        
        # Get user info
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user = sp.current_user()
        
        # Store user info in session
        session['spotify_user'] = {
            'id': user['id'],
            'display_name': user['display_name'],
            'email': user.get('email', ''),
            'country': user.get('country', ''),
            'product': user.get('product', '')
        }
        logger.info(f"Stored spotify_user in session: {bool(session.get('spotify_user'))}")
        logger.info(f"Session keys after storing: {list(session.keys())}")
        
        # Generate a temporary auth token
        auth_token = secrets.token_urlsafe(32)
        
        # Store auth data in temporary storage
        temp_auth_tokens[auth_token] = {
            'spotify_token': token_info,
            'spotify_user': {
                'id': user['id'],
                'display_name': user['display_name'],
                'email': user.get('email', ''),
                'country': user.get('country', ''),
                'product': user.get('product', '')
            },
            'timestamp': datetime.now()
        }
        
        # Now clear the oauth_state from session
        if 'oauth_state' in session:
            del session['oauth_state']
        
        # Force session to be saved
        session.permanent = True
        session.modified = True
        
        # Redirect to frontend with success and auth token
        logger.info("About to redirect to frontend with auth token")
        return redirect(f'http://localhost:3000?spotify_auth=success&token={auth_token}')
        
    except Exception as e:
        logger.error(f"Error in Spotify callback: {e}")
        return redirect('http://localhost:3000?spotify_auth=error')

@app.route('/api/auth/exchange-token', methods=['POST'])
def exchange_auth_token():
    """Exchange temporary auth token for session data."""
    try:
        data = request.get_json()
        auth_token = data.get('token')
        
        if not auth_token:
            return jsonify({'error': 'No token provided'}), 400
        
        # Check if token exists and is not expired (1 hour)
        if auth_token not in temp_auth_tokens:
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        auth_data = temp_auth_tokens[auth_token]
        
        # Check if token is expired (1 hour)
        if (datetime.now() - auth_data['timestamp']).seconds > 3600:
            del temp_auth_tokens[auth_token]
            return jsonify({'error': 'Token expired'}), 400
        
        # Store auth data in session
        session['spotify_token'] = auth_data['spotify_token']
        session['spotify_user'] = auth_data['spotify_user']
        session.permanent = True
        session.modified = True
        
        # Remove the temporary token
        del temp_auth_tokens[auth_token]
        
        logger.info(f"Exchanged token for session data: {list(session.keys())}")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user': auth_data['spotify_user']
        })
        
    except Exception as e:
        logger.error(f"Error exchanging auth token: {e}")
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


if __name__ == '__main__':
    print("🚀 Starting spotify_message web server...")
    print()
    print("📱 React app will be available at: http://localhost:3000")
    print("🔧 API endpoints available at: http://localhost:8004/api/")
    print()
    
    # Check if build directory exists
    if not os.path.exists('build'):
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
        
        logger.info(f"Starting Flask server on port {port}")
        print(f"🚀 Flask server starting on port {port}")
        print(f"🔧 API endpoints: http://localhost:{port}/api/")
        
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        logger.error(traceback.format_exc())
        raise
