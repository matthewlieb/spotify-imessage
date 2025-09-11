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

app = Flask(__name__)
CORS(app)

logger.info("Flask app created successfully")
logger.info("CORS enabled")  # Enable CORS for development

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

# Spotify configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', 'ee9c48a1cfe44fe392fd3ff39d95b3a5')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '47750a0f67494b30a59e739bc8d9e535')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8000/callback')

def get_spotify_client():
    """Get authenticated Spotify client."""
    if not SPOTIFY_AVAILABLE:
        return None
    
    try:
        cache_path = os.path.expanduser("~/.cache/spotify_token.json")
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="playlist-modify-public playlist-modify-private playlist-read-private",
            cache_path=cache_path
        ))
        return sp
    except Exception as e:
        print(f"Error initializing Spotify client: {e}")
        return None

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
            chat_name = os.path.basename(chat_file).replace('.txt', '')
            
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
        
        return {'success': True, 'chats': chats}
        
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
        port = find_available_port(8004)
        logger.info(f"Starting Flask server on port {port}")
        print(f"🚀 Flask server starting on port {port}")
        print(f"🔧 API endpoints: http://localhost:{port}/api/")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        logger.error(traceback.format_exc())
        raise
