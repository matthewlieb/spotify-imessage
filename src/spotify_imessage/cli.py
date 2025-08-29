#!/usr/bin/env python3
"""
spotify-imessage: Sync Spotify tracks into a Spotify playlist from various sources.

Usage:
  spotify-imessage imessage --chat "My Group" --playlist <PLAYLIST_ID> [--dry-run]
  spotify-imessage file --file track_ids.txt --playlist <PLAYLIST_ID> [--dry-run]

Env (recommended):
  export SPOTIPY_CLIENT_ID=...
  export SPOTIPY_CLIENT_SECRET=...
  export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000/callback"
"""

import os
import re
import glob
import sqlite3
import plistlib
import subprocess
import tempfile
import json
import csv
from datetime import datetime
from typing import Iterable, List, Set
from pathlib import Path

import click
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# Defaults
DEFAULT_DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")
DEFAULT_ATTACH_DIR = os.path.expanduser("~/Library/Messages/Attachments")
DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/spotify-imessage/spotify_token.json")
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/spotify-imessage/config.json")

# Regexes
SPOTIFY_ID_RE = re.compile(r"[A-Za-z0-9]{22}")
SPOTIFY_URL_RE = re.compile(r"open\.spotify\.com/track/([A-Za-z0-9]{22})")


def _validate_spotify_credentials(client_id: str, client_secret: str) -> None:
    """Validate that Spotify credentials are provided."""
    if not client_id:
        raise click.ClickException(
            "Spotify Client ID is required. Set SPOTIPY_CLIENT_ID environment variable or use --client-id"
        )
    if not client_secret:
        raise click.ClickException(
            "Spotify Client Secret is required. Set SPOTIPY_CLIENT_SECRET environment variable or use --client-secret"
        )


def _validate_playlist_id(playlist_id: str) -> None:
    """Validate Spotify playlist ID format."""
    if not playlist_id or len(playlist_id) != 22 or not SPOTIFY_ID_RE.fullmatch(playlist_id):
        raise click.ClickException(
            f"Invalid playlist ID: {playlist_id}. Expected 22-character alphanumeric string."
        )


def _validate_chat_name(chat_name: str) -> None:
    """Validate chat name is not empty."""
    if not chat_name or not chat_name.strip():
        raise click.ClickException("Chat name cannot be empty")


def _check_imessage_exporter() -> None:
    """Check if imessage-exporter is available and working."""
    try:
        result = subprocess.run(['imessage-exporter', '--help'], 
                              capture_output=True, text=True, check=True)
        if 'Usage:' not in result.stdout:
            raise click.ClickException("imessage-exporter appears to be installed but not working correctly")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise click.ClickException(
            "imessage-exporter not found. Install it with: brew install imessage-exporter\n"
            "Visit: https://github.com/ReagentX/imessage-exporter"
        )


def _check_database_access(db_path: str) -> None:
    """Check if we can access the iMessage database."""
    if not os.path.exists(db_path):
        raise click.ClickException(
            f"iMessage database not found at: {db_path}\n"
            "Make sure you're on macOS and have granted Full Disk Access to your terminal.\n"
            "System Settings → Privacy & Security → Full Disk Access → enable your Terminal/IDE"
        )
    
    try:
        # Try to read the database file
        with open(db_path, 'rb') as f:
            f.read(1024)  # Read first 1KB to test access
    except PermissionError:
        raise click.ClickException(
            f"Permission denied accessing: {db_path}\n"
            "Grant Full Disk Access to your terminal in System Settings → Privacy & Security → Full Disk Access"
        )
    except Exception as e:
        raise click.ClickException(f"Cannot access database {db_path}: {e}")


def _safe_spotify_auth(client_id: str, client_secret: str, redirect_uri: str, cache_path: str) -> Spotify:
    """Safely authenticate with Spotify with better error handling."""
    try:
        return _get_spotify_client(client_id, client_secret, redirect_uri, cache_path)
    except Exception as e:
        if "No client_id" in str(e):
            raise click.ClickException(
                "Spotify credentials not found. Set environment variables:\n"
                "export SPOTIPY_CLIENT_ID='your_client_id'\n"
                "export SPOTIPY_CLIENT_SECRET='your_client_secret'\n"
                "Or use --client-id and --client-secret options"
            )
        elif "redirect_uri_mismatch" in str(e):
            raise click.ClickException(
                f"Redirect URI mismatch. Make sure your Spotify app's redirect URI matches: {redirect_uri}\n"
                "Update your Spotify app settings at: https://developer.spotify.com/dashboard"
            )
        elif "invalid_client" in str(e):
            raise click.ClickException(
                "Invalid Spotify credentials. Check your Client ID and Client Secret.\n"
                "Get them from: https://developer.spotify.com/dashboard"
            )
        else:
            raise click.ClickException(f"Spotify authentication failed: {e}")


def _validate_ids(ids: Iterable[str]) -> List[str]:
    valid, bad = [], []
    for tid in ids:
        if SPOTIFY_ID_RE.fullmatch(tid):
            valid.append(tid)
        else:
            bad.append(tid)
    if bad:
        click.echo(f"⚠️  Skipped {len(bad)} invalid IDs (first few): {bad[:5]}", err=True)
    return valid


def _parse_date_from_line(line: str) -> datetime:
    """Parse date from iMessage export line format: 'Dec 01, 2022 5:10:27 PM'"""
    try:
        # Handle different date formats
        date_formats = [
            "%b %d, %Y %I:%M:%S %p",  # Dec 01, 2022 5:10:27 PM
            "%B %d, %Y %I:%M:%S %p",  # December 01, 2022 5:10:27 PM
            "%b %d, %Y %H:%M:%S",     # Dec 01, 2022 17:10:27
            "%B %d, %Y %H:%M:%S",     # December 01, 2022 17:10:27
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(line.strip(), fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date: {line}")
    except Exception as e:
        raise ValueError(f"Invalid date format: {line} - {e}")


def _is_line_date(line: str) -> bool:
    """Check if a line contains a date timestamp."""
    line = line.strip()
    if not line:
        return False
    
    # Check if line matches date pattern (e.g., "Dec 01, 2022 5:10:27 PM")
    date_pattern = r'^[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(AM|PM)?$'
    return bool(re.match(date_pattern, line))


def _extract_track_ids_with_date_filter(export_dir: str, chat_name: str, start_date: datetime = None, end_date: datetime = None) -> list:
    """Extract Spotify track IDs from exported files with date filtering."""
    track_ids = []
    matching_files = []
    
    # Find files matching the chat name
    for filename in os.listdir(export_dir):
        if filename.endswith('.txt') and chat_name.lower() in filename.lower():
            matching_files.append(filename)
    
    if not matching_files:
        click.echo(f"⚠️  No TXT file found for chat '{chat_name}' in {export_dir}")
        return track_ids
    
    # Process each matching file
    for filename in matching_files:
        file_path = os.path.join(export_dir, filename)
        current_date = None
        in_date_range = True  # If no date filter, include all
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Check if this line is a date timestamp
                    if _is_line_date(line):
                        try:
                            current_date = _parse_date_from_line(line)
                            
                            # Check if current date is within filter range
                            if start_date and current_date < start_date:
                                in_date_range = False
                            elif end_date and current_date > end_date:
                                in_date_range = False
                            else:
                                in_date_range = True
                                
                        except ValueError:
                            # Skip invalid date lines
                            continue
                    
                    # Only process Spotify URLs if we're in the date range
                    elif in_date_range and 'open.spotify.com/track/' in line:
                        match = SPOTIFY_URL_RE.search(line)
                        if match:
                            track_id = match.group(1)
                            if SPOTIFY_ID_RE.fullmatch(track_id):
                                track_ids.append(track_id)
                                
        except Exception as e:
            click.echo(f"⚠️  Error reading file {filename}: {e}")
            continue
    
    return track_ids


def _extract_track_ids_from_export(export_dir: str, chat_name: str) -> Set[str]:
    """Extract Spotify track IDs from imessage-exporter TXT files using grep."""
    track_ids: Set[str] = set()
    
    # Find the TXT file for this chat
    chat_file = None
    for filename in os.listdir(export_dir):
        if filename.endswith('.txt') and chat_name.lower() in filename.lower():
            chat_file = os.path.join(export_dir, filename)
            break
    
    if not chat_file:
        click.echo(f"⚠️  No TXT file found for chat '{chat_name}' in {export_dir}")
        return track_ids
    
    try:
        # Use grep to extract Spotify track URLs and then sed to get just the IDs
        cmd = [
            'grep', '-Eo', 'open\\.spotify\\.com/track/[A-Za-z0-9]+',
            chat_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extract track IDs from the URLs
        for line in result.stdout.strip().split('\n'):
            if line:
                # Extract the track ID from the URL
                match = SPOTIFY_URL_RE.search(line)
                if match:
                    track_ids.add(match.group(1))
                    
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # grep found no matches
            click.echo(f"ℹ️  No Spotify track URLs found in {chat_file}")
        else:
            click.echo(f"⚠️  Error running grep: {e}")
    except Exception as e:
        click.echo(f"⚠️  Error processing {chat_file}: {e}")
    
    return track_ids


def _existing_track_ids(sp: Spotify, playlist_id: str) -> Set[str]:
    """Fetch existing track IDs from the target playlist to dedupe."""
    seen: Set[str] = set()
    limit, offset = 100, 0
    
    # First, get the total count
    try:
        playlist = sp.playlist(playlist_id, fields="tracks(total)")
        total_tracks = playlist['tracks']['total']
    except Exception as e:
        click.echo(f"⚠️  Could not get playlist info, skipping deduplication: {e}")
        return seen
    
    if total_tracks == 0:
        return seen
    
    with click.progressbar(length=total_tracks, label="Checking existing tracks") as bar:
        while True:
            try:
                payload = sp.playlist_items(
                    playlist_id, fields="items(track(uri)),next", limit=limit, offset=offset
                )
                
                for it in payload.get("items", []):
                    uri = (it.get("track") or {}).get("uri") or ""
                    parts = uri.split(":")  # spotify:track:<id>
                    if len(parts) == 3 and parts[1] == "track" and SPOTIFY_ID_RE.fullmatch(parts[2]):
                        seen.add(parts[2])
                    bar.update(1)
                
                if payload.get("next"):
                    offset += limit
                else:
                    break
            except Exception as e:
                click.echo(f"⚠️  Error fetching playlist tracks: {e}")
                break
    
    return seen


def _get_spotify_client(client_id: str, client_secret: str, redirect_uri: str, cache_path: str) -> Spotify:
    """Create and return a Spotify client with OAuth authentication."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    return Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="playlist-modify-public playlist-modify-private",
        cache_path=cache_path,
    ))


def _prepare_export_directory(output_dir: str, force: bool = False) -> str:
    """Prepare export directory, handling conflicts gracefully."""
    output_dir = os.path.expanduser(output_dir)
    
    if os.path.exists(output_dir):
        if force:
            # User explicitly wants to overwrite
            import shutil
            shutil.rmtree(output_dir)
            click.echo(f"🗑️  Removed existing directory: {output_dir}")
        else:
            # Create unique directory
            import tempfile
            base_name = os.path.basename(output_dir)
            temp_dir = tempfile.mkdtemp(prefix=f"{base_name}_")
            output_dir = temp_dir
            click.echo(f"📁 Using temporary directory: {output_dir}")
    
    # Create directory
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _cleanup_export_directory(output_dir: str, keep_export: bool) -> None:
    """Clean up export directory unless keep_export is True."""
    if not keep_export and os.path.exists(output_dir):
        try:
            import shutil
            shutil.rmtree(output_dir)
            click.echo("🧹 Cleaned up exported files")
        except Exception as e:
            click.echo(f"⚠️  Could not clean up {output_dir}: {e}")


def _get_track_metadata(sp, track_ids: list) -> dict:
    """Fetch track metadata (artist, title) from Spotify API."""
    if not track_ids:
        return {}
    
    metadata = {}
    # Process in batches of 50 (Spotify API limit for tracks endpoint)
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i:i+50]
        try:
            tracks = sp.tracks(batch)
            for track in tracks['tracks']:
                if track:  # Some tracks might be None if not found
                    track_id = track['id']
                    artist = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
                    title = track['name']
                    metadata[track_id] = {
                        'artist': artist,
                        'title': title,
                        'display_name': f"{artist} - {title}"
                    }
        except Exception as e:
            click.echo(f"⚠️  Could not fetch metadata for batch: {e}")
    
    return metadata


@click.group()
def cli():
    """Sync Spotify tracks into a playlist from various sources."""
    pass


@cli.command()
@click.option("--set", "set_key", help="Set a configuration value (format: key=value)")
@click.option("--get", "get_key", help="Get a configuration value")
@click.option("--list", "list_config", is_flag=True, help="List all configuration values")
@click.option("--reset", "reset_config", is_flag=True, help="Reset configuration to defaults")
def config(set_key: str, get_key: str, list_config: bool, reset_config: bool):
    """Manage configuration settings."""
    if set_key:
        if '=' not in set_key:
            raise click.ClickException("Use format: --set key=value")
        
        key, value = set_key.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        config = _load_config()
        config[key] = value
        _save_config(config)
        click.echo(f"✅ Set {key} = {value}")
        
    elif get_key:
        value = _get_config_value(get_key)
        if value is None:
            click.echo(f"❌ {get_key} not set")
        else:
            click.echo(f"{get_key} = {value}")
            
    elif list_config:
        config = _load_config()
        if not config:
            click.echo("No configuration set. Use --set to configure.")
            return
            
        click.echo("📋 Current configuration:")
        for key, value in config.items():
            # Mask sensitive values
            if 'secret' in key.lower() or 'password' in key.lower():
                display_value = '*' * min(len(value), 8) + '...' if value else 'not set'
            else:
                display_value = value
            click.echo(f"  {key} = {display_value}")
            
    elif reset_config:
        if click.confirm("Are you sure you want to reset all configuration?"):
            config_path = Path(DEFAULT_CONFIG_PATH)
            if config_path.exists():
                config_path.unlink()
            click.echo("✅ Configuration reset")
        else:
            click.echo("Configuration reset cancelled")
            
    else:
        click.echo("Use --help to see available options")


@cli.command()
@click.option("--chat", "chat_name", required=True, help="iMessage group name")
@click.option("--playlist", "playlist_id", help="Target Spotify playlist ID")
@click.option("--db", "db_path", help="Path to your Messages chat.db")
@click.option("--output-dir", help="Directory to store exported TXT files")
@click.option("--cache", "cache_path", help="Where to store Spotify OAuth cache")
@click.option("--client-id", help="Spotify Client ID")
@click.option("--client-secret", help="Spotify Client Secret")
@click.option("--redirect-uri", help="Spotify Redirect URI")
@click.option("--dry-run", is_flag=True, help="Export & extract tracks but do not add to Spotify.")
@click.option("--no-dedupe", is_flag=True, help="Do not skip tracks already in the playlist.")
@click.option("--keep-export", is_flag=True, help="Keep the exported TXT files (default: cleanup)")
@click.option("--force", is_flag=True, help="Force overwrite existing export directory")
@click.option("--show-metadata", is_flag=True, help="Show artist and title when adding tracks")
@click.option("--start-date", help="Only process messages from this date (YYYY-MM-DD)")
@click.option("--end-date", help="Only process messages until this date (YYYY-MM-DD)")
@click.option("--days-back", type=int, help="Only process messages from the last N days")
def imessage(chat_name: str,
             playlist_id: str,
             db_path: str,
             output_dir: str,
             cache_path: str,
             client_id: str,
             client_secret: str,
             redirect_uri: str,
             dry_run: bool,
             no_dedupe: bool,
             keep_export: bool,
             force: bool,
             show_metadata: bool,
             start_date: str,
             end_date: str,
             days_back: int):
    """Extract Spotify tracks from an iMessage group using imessage-exporter and add them to a playlist."""
    # Get values from config if not provided
    playlist_id = playlist_id or _get_config_value('playlist_id')
    db_path = db_path or _get_config_value('db_path', DEFAULT_DB_PATH)
    output_dir = output_dir or _get_config_value('output_dir', "~/Desktop/imessage_dump")
    cache_path = cache_path or _get_config_value('cache_path', DEFAULT_CACHE_PATH)
    client_id = client_id or _get_config_value('client_id')
    client_secret = client_secret or _get_config_value('client_secret')
    redirect_uri = redirect_uri or _get_config_value('redirect_uri', "http://127.0.0.1:8000/callback")
    
    # Validate required parameters
    if not playlist_id:
        raise click.ClickException("Playlist ID is required. Set it with --playlist or use 'spotify-imessage config --set playlist_id=YOUR_PLAYLIST_ID'")
    
    # Expand paths
    db_path = os.path.expanduser(db_path)
    cache_path = os.path.expanduser(cache_path)

    # Parse date filters
    start_datetime = None
    end_datetime = None
    
    if days_back:
        from datetime import timedelta
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(days=days_back)
        click.echo(f"📅 Filtering messages from last {days_back} days ({start_datetime.strftime('%Y-%m-%d')} to {end_datetime.strftime('%Y-%m-%d')})")
    elif start_date or end_date:
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                click.echo(f"📅 Filtering messages from {start_date}")
            except ValueError:
                raise click.ClickException(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                click.echo(f"📅 Filtering messages until {end_date}")
            except ValueError:
                raise click.ClickException(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    _validate_playlist_id(playlist_id)
    _validate_chat_name(chat_name)
    _check_imessage_exporter()
    _check_database_access(db_path)

    # Prepare export directory (handles conflicts)
    output_dir = _prepare_export_directory(output_dir, force)

    # 1) Export chat to TXT using imessage-exporter
    click.echo(f"📤 Exporting '{chat_name}' to TXT files...")
    try:
        subprocess.run([
            'imessage-exporter',
            '--format', 'txt',
            '--db-path', db_path,
            '--export-path', output_dir
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Failed to export iMessage data: {e}")

    # 2) Extract Spotify track IDs from the exported files
    click.echo(f"🔍 Extracting Spotify track IDs from exported files...")
    if start_datetime or end_datetime:
        track_ids = _extract_track_ids_with_date_filter(output_dir, chat_name, start_datetime, end_datetime)
    else:
        track_ids = _extract_track_ids_from_export(output_dir, chat_name)

    valid_ids = _validate_ids(track_ids)
    click.echo(f"Found {len(valid_ids)} Spotify tracks in '{chat_name}'")

    if not valid_ids or dry_run:
        if dry_run:
            click.echo("Dry run: not adding to Spotify.")
        _cleanup_export_directory(output_dir, keep_export)
        return

    # 3) Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)

    # 4) Optional dedupe
    if not no_dedupe:
        existing = _existing_track_ids(sp, playlist_id)
        before = len(valid_ids)
        valid_ids = [tid for tid in valid_ids if tid not in existing]
        click.echo(f"Skipping {before - len(valid_ids)} duplicates already in playlist.")

    if not valid_ids:
        click.echo("Nothing new to add after deduplication.")
        _cleanup_export_directory(output_dir, keep_export)
        return

    # 5) Add to playlist
    uris = [f"spotify:track:{tid}" for tid in valid_ids]
    
    # Fetch metadata if requested
    metadata = {}
    if show_metadata and valid_ids:
        click.echo("📊 Fetching track metadata...")
        metadata = _get_track_metadata(sp, valid_ids)
    
    with click.progressbar(length=len(uris), label="Adding tracks to playlist") as bar:
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            batch_ids = valid_ids[i:i+100]
            
            try:
                sp.playlist_add_items(playlist_id, batch)
                
                # Show metadata for this batch if requested
                if show_metadata:
                    for track_id in batch_ids:
                        if track_id in metadata:
                            click.echo(f"  ➕ {metadata[track_id]['display_name']}")
                        else:
                            click.echo(f"  ➕ Track ID: {track_id}")
                
                bar.update(len(batch))
            except Exception as e:
                click.echo(f"⚠️  Error adding batch {i//100 + 1}: {e}")
                # Continue with next batch

    click.echo(f"✅ Done! Added {len(uris)} tracks to playlist {playlist_id}.")

    # 6) Cleanup (unless --keep-export)
    _cleanup_export_directory(output_dir, keep_export)


@cli.command()
@click.option("--chats", "chat_names", required=True, help="Comma-separated list of iMessage group names")
@click.option("--playlist", "playlist_id", required=True, help="Target Spotify playlist ID")
@click.option("--separate-playlists", is_flag=True, help="Create separate playlists for each chat (playlist names will be 'Original Name - Chat Name')")
@click.option("--db", "db_path", default=DEFAULT_DB_PATH, show_default=True,
              help="Path to your Messages chat.db")
@click.option("--output-dir", default="~/Desktop/imessage_dump", show_default=True,
              help="Directory to store exported TXT files")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id",     envvar="SPOTIPY_CLIENT_ID",
              help="Spotify Client ID (or set SPOTIPY_CLIENT_ID)")
@click.option("--client-secret", envvar="SPOTIPY_CLIENT_SECRET",
              help="Spotify Client Secret (or set SPOTIPY_CLIENT_SECRET)")
@click.option("--redirect-uri",  envvar="SPOTIPY_REDIRECT_URI",
              default="http://127.0.0.1:8000/callback", show_default=True,
              help="Spotify Redirect URI (or set SPOTIPY_REDIRECT_URI)")
@click.option("--dry-run", is_flag=True, help="Export & extract tracks but do not add to Spotify.")
@click.option("--no-dedupe", is_flag=True, help="Do not skip tracks already in the playlist.")
@click.option("--keep-export", is_flag=True, help="Keep the exported TXT files (default: cleanup)")
@click.option("--start-date", help="Only process messages from this date (YYYY-MM-DD)")
@click.option("--end-date", help="Only process messages until this date (YYYY-MM-DD)")
@click.option("--days-back", type=int, help="Only process messages from the last N days")
@click.option("--force", is_flag=True, help="Force overwrite existing export directory")
def batch(chat_names: str,
          playlist_id: str,
          separate_playlists: bool,
          db_path: str,
          output_dir: str,
          cache_path: str,
          client_id: str,
          client_secret: str,
          redirect_uri: str,
          dry_run: bool,
          no_dedupe: bool,
          keep_export: bool,
          start_date: str,
          end_date: str,
          days_back: int,
          force: bool):
    """Process multiple iMessage chats and add Spotify tracks to playlist(s)."""
    # Parse chat names
    chats = [name.strip() for name in chat_names.split(',') if name.strip()]
    if not chats:
        raise click.ClickException("No valid chat names provided")
    
    click.echo(f"🎯 Processing {len(chats)} chats: {', '.join(chats)}")
    
    # Expand paths
    db_path = os.path.expanduser(db_path)
    cache_path = os.path.expanduser(cache_path)
    
    # Prepare export directory (handles conflicts)
    output_dir = _prepare_export_directory(output_dir, force)
    
    # Parse date filters
    start_datetime = None
    end_datetime = None
    
    if days_back:
        from datetime import timedelta
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(days=days_back)
        click.echo(f"📅 Filtering messages from last {days_back} days ({start_datetime.strftime('%Y-%m-%d')} to {end_datetime.strftime('%Y-%m-%d')})")
    elif start_date or end_date:
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                click.echo(f"📅 Filtering messages from {start_date}")
            except ValueError:
                raise click.ClickException(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                click.echo(f"📅 Filtering messages until {end_date}")
            except ValueError:
                raise click.ClickException(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    _validate_playlist_id(playlist_id)
    for chat_name in chats:
        _validate_chat_name(chat_name)
    _check_imessage_exporter()
    _check_database_access(db_path)
    
    # 1) Export all chats to TXT files
    click.echo(f"📤 Exporting {len(chats)} chats to TXT files...")
    try:
        subprocess.run([
            'imessage-exporter',
            '--format', 'txt',
            '--db-path', db_path,
            '--export-path', output_dir
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Failed to export iMessage data: {e}")
    
    # 2) Extract tracks from each chat
    all_tracks = {}  # chat_name -> set of track_ids
    total_tracks = 0
    
    for chat_name in chats:
        click.echo(f"🔍 Processing '{chat_name}'...")
        if start_datetime or end_datetime:
            track_ids = _extract_track_ids_with_date_filter(output_dir, chat_name, start_datetime, end_datetime)
        else:
            track_ids = _extract_track_ids_from_export(output_dir, chat_name)
        valid_ids = _validate_ids(track_ids)
        all_tracks[chat_name] = valid_ids
        total_tracks += len(valid_ids)
        click.echo(f"   Found {len(valid_ids)} tracks")
    
    click.echo(f"📊 Total tracks found: {total_tracks}")
    
    if not total_tracks or dry_run:
        if dry_run:
            click.echo("Dry run: not adding to Spotify.")
        _cleanup_export_directory(output_dir, keep_export)
        return
    
    # 3) Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)
    
    if separate_playlists:
        # Create separate playlists for each chat
        for chat_name, track_ids in all_tracks.items():
            if not track_ids:
                continue
                
            # Create playlist name
            playlist_name = f"{playlist_id} - {chat_name}"
            
            # Create new playlist
            try:
                playlist = sp.user_playlist_create(
                    user=sp.current_user()['id'],
                    name=playlist_name,
                    public=False,
                    description=f"Spotify tracks from iMessage chat: {chat_name}"
                )
                new_playlist_id = playlist['id']
                click.echo(f"📝 Created playlist: {playlist_name}")
            except Exception as e:
                raise click.ClickException(f"Failed to create playlist '{playlist_name}': {e}")
            
            # Add tracks to this playlist
            _add_tracks_to_playlist(sp, new_playlist_id, track_ids, no_dedupe)
            
    else:
        # Combine all tracks into single playlist
        combined_tracks = set()
        for track_ids in all_tracks.values():
            combined_tracks.update(track_ids)
        
        click.echo(f"🎵 Adding {len(combined_tracks)} unique tracks to playlist {playlist_id}")
        _add_tracks_to_playlist(sp, playlist_id, list(combined_tracks), no_dedupe)
    
    # 4) Cleanup (unless --keep-export)
    _cleanup_export_directory(output_dir, keep_export)


@cli.command()
@click.option("--playlist", "playlist_id", required=True, help="Spotify playlist ID to export")
@click.option("--format", "export_format", type=click.Choice(['csv', 'json', 'txt', 'm3u']), default='csv', 
              help="Export format")
@click.option("--output", "output_file", help="Output file path (default: playlist_name.format)")
@click.option("--include-metadata", is_flag=True, help="Include track metadata (artist, album, duration)")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id",     envvar="SPOTIPY_CLIENT_ID",
              help="Spotify Client ID (or set SPOTIPY_CLIENT_ID)")
@click.option("--client-secret", envvar="SPOTIPY_CLIENT_SECRET",
              help="Spotify Client Secret (or set SPOTIPY_CLIENT_SECRET)")
@click.option("--redirect-uri",  envvar="SPOTIPY_REDIRECT_URI",
              default="http://127.0.0.1:8000/callback", show_default=True,
              help="Spotify Redirect URI (or set SPOTIPY_REDIRECT_URI)")
def export(playlist_id: str,
           export_format: str,
           output_file: str,
           include_metadata: bool,
           cache_path: str,
           client_id: str,
           client_secret: str,
           redirect_uri: str):
    """Export a Spotify playlist to various formats."""
    import json
    import csv
    from datetime import datetime
    
    # Expand paths
    cache_path = os.path.expanduser(cache_path)
    
    # Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)
    
    # Get playlist info
    try:
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        click.echo(f"📋 Exporting playlist: {playlist_name}")
    except Exception as e:
        raise click.ClickException(f"Failed to fetch playlist: {e}")
    
    # Get all tracks
    tracks = []
    limit, offset = 100, 0
    
    with click.progressbar(length=playlist['tracks']['total'], label="Fetching tracks") as bar:
        while True:
            try:
                payload = sp.playlist_items(
                    playlist_id, 
                    fields="items(track(id,name,artists(name),album(name),duration_ms,external_urls(spotify)))",
                    limit=limit, 
                    offset=offset
                )
                
                for item in payload.get("items", []):
                    track = item.get("track")
                    if track and track.get("id"):
                        tracks.append(track)
                        bar.update(1)
                
                if payload.get("next"):
                    offset += limit
                else:
                    break
                    
            except Exception as e:
                raise click.ClickException(f"Failed to fetch tracks: {e}")
    
    click.echo(f"📊 Found {len(tracks)} tracks")
    
    # Determine output file
    if not output_file:
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_file = f"{safe_name}.{export_format}"
    
    # Export based on format
    try:
        if export_format == 'csv':
            _export_csv(tracks, output_file, include_metadata)
        elif export_format == 'json':
            _export_json(tracks, output_file, include_metadata)
        elif export_format == 'txt':
            _export_txt(tracks, output_file, include_metadata)
        elif export_format == 'm3u':
            _export_m3u(tracks, output_file, include_metadata)
        
        click.echo(f"✅ Exported to: {output_file}")
        
    except Exception as e:
        raise click.ClickException(f"Failed to export: {e}")


def _add_tracks_to_playlist(sp: Spotify, playlist_id: str, track_ids: list, no_dedupe: bool):
    """Helper function to add tracks to a playlist with deduplication."""
    if not track_ids:
        return
    
    # Optional dedupe
    if not no_dedupe:
        existing = _existing_track_ids(sp, playlist_id)
        before = len(track_ids)
        track_ids = [tid for tid in track_ids if tid not in existing]
        click.echo(f"   Skipping {before - len(track_ids)} duplicates already in playlist")
    
    if not track_ids:
        click.echo("   Nothing new to add after deduplication")
        return
    
    # Add to playlist
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    
    with click.progressbar(length=len(uris), label="Adding tracks to playlist") as bar:
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            try:
                sp.playlist_add_items(playlist_id, batch)
                bar.update(len(batch))
            except Exception as e:
                click.echo(f"⚠️  Error adding batch {i//100 + 1}: {e}")
                # Continue with next batch
    
    click.echo(f"   ✅ Added {len(uris)} tracks to playlist")


def _export_csv(tracks: list, output_file: str, include_metadata: bool):
    """Export tracks to CSV format."""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        if include_metadata:
            fieldnames = ['track_id', 'track_name', 'artist', 'album', 'duration_ms', 'spotify_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for track in tracks:
                artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown'
                writer.writerow({
                    'track_id': track['id'],
                    'track_name': track['name'],
                    'artist': artist_name,
                    'album': track['album']['name'] if track['album'] else 'Unknown',
                    'duration_ms': track['duration_ms'],
                    'spotify_url': track['external_urls']['spotify']
                })
        else:
            writer = csv.writer(csvfile)
            writer.writerow(['track_id'])
            for track in tracks:
                writer.writerow([track['id']])


def _export_json(tracks: list, output_file: str, include_metadata: bool):
    """Export tracks to JSON format."""
    if include_metadata:
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_tracks': len(tracks),
            'tracks': tracks
        }
    else:
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_tracks': len(tracks),
            'track_ids': [track['id'] for track in tracks]
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _export_txt(tracks: list, output_file: str, include_metadata: bool):
    """Export tracks to plain text format."""
    with open(output_file, 'w', encoding='utf-8') as f:
        if include_metadata:
            for track in tracks:
                artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown'
                album_name = track['album']['name'] if track['album'] else 'Unknown'
                duration_min = track['duration_ms'] // 60000
                duration_sec = (track['duration_ms'] % 60000) // 1000
                
                f.write(f"{track['id']}\t{track['name']}\t{artist_name}\t{album_name}\t{duration_min}:{duration_sec:02d}\n")
        else:
            for track in tracks:
                f.write(f"{track['id']}\n")


def _export_m3u(tracks: list, output_file: str, include_metadata: bool):
    """Export tracks to M3U playlist format."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        
        for track in tracks:
            if include_metadata:
                artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown'
                duration_sec = track['duration_ms'] // 1000
                f.write(f"#EXTINF:{duration_sec},{artist_name} - {track['name']}\n")
            
            f.write(f"{track['external_urls']['spotify']}\n")


@cli.command()
@click.option("--file", "track_file", required=True, help="Path to text file containing track IDs (one per line)")
@click.option("--playlist", "playlist_id", required=True, help="Target Spotify playlist ID")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id",     envvar="SPOTIPY_CLIENT_ID",
              help="Spotify Client ID (or set SPOTIPY_CLIENT_ID)")
@click.option("--client-secret", envvar="SPOTIPY_CLIENT_SECRET",
              help="Spotify Client Secret (or set SPOTIPY_CLIENT_SECRET)")
@click.option("--redirect-uri",  envvar="SPOTIPY_REDIRECT_URI",
              default="http://127.0.0.1:8000/callback", show_default=True,
              help="Spotify Redirect URI (or set SPOTIPY_REDIRECT_URI)")
@click.option("--dry-run", is_flag=True, help="Load & validate tracks but do not add to Spotify.")
@click.option("--no-dedupe", is_flag=True, help="Do not skip tracks already in the playlist.")
@click.option("--show-metadata", is_flag=True, help="Show artist and title when adding tracks")
def file(track_file: str,
         playlist_id: str,
         cache_path: str,
         client_id: str,
         client_secret: str,
         redirect_uri: str,
         dry_run: bool,
         no_dedupe: bool,
         show_metadata: bool):
    """Add Spotify tracks from a text file to a playlist."""
    # Expand paths
    track_file = os.path.expanduser(track_file)
    cache_path = os.path.expanduser(cache_path)

    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    _validate_playlist_id(playlist_id)
    
    if not os.path.exists(track_file):
        raise click.ClickException(f"Track file not found: {track_file}")
    
    if os.path.getsize(track_file) == 0:
        raise click.ClickException(f"Track file is empty: {track_file}")

    # 1) Read & validate track IDs
    uris = []
    skipped = []
    with open(track_file, 'r') as f:
        for line in f:
            tid = line.strip()
            if tid and not tid.startswith('#'):  # Skip empty lines and comments
                if SPOTIFY_ID_RE.fullmatch(tid):
                    uris.append(f"spotify:track:{tid}")
                else:
                    skipped.append(tid)

    click.echo(f"✅ Loaded {len(uris)} valid track IDs.")
    if skipped:
        click.echo(f"⚠️  Skipped {len(skipped)} invalid IDs (first few): {skipped[:5]}")

    if not uris:
        click.echo("🚨 No valid tracks to add. Check your track file.")
        return

    if dry_run:
        click.echo("Dry run: not adding to Spotify.")
        return

    # 2) Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)

    # 3) Optional dedupe
    if not no_dedupe:
        existing = _existing_track_ids(sp, playlist_id)
        before = len(uris)
        uris = [uri for uri in uris if uri.split(":")[-1] not in existing]
        click.echo(f"Skipping {before - len(uris)} duplicates already in playlist.")

    if not uris:
        click.echo("Nothing new to add after deduplication.")
        return

    # 4) Batch-add in chunks of 100
    # Extract track IDs for metadata
    track_ids = [uri.split(":")[-1] for uri in uris]
    
    # Fetch metadata if requested
    metadata = {}
    if show_metadata and track_ids:
        click.echo("📊 Fetching track metadata...")
        metadata = _get_track_metadata(sp, track_ids)
    
    with click.progressbar(length=len(uris), label="Adding tracks to playlist") as bar:
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            batch_ids = track_ids[i:i+100]
            
            try:
                sp.playlist_add_items(playlist_id, batch)
                
                # Show metadata for this batch if requested
                if show_metadata:
                    for track_id in batch_ids:
                        if track_id in metadata:
                            click.echo(f"  ➕ {metadata[track_id]['display_name']}")
                        else:
                            click.echo(f"  ➕ Track ID: {track_id}")
                
                bar.update(len(batch))
            except Exception as e:
                click.echo(f"⚠️  Error adding batch {i//100 + 1}: {e}")
                # Continue with next batch

    click.echo(f"🎉 Done — added {len(uris)} tracks to playlist {playlist_id}!")


@cli.group()
def template():
    """Manage playlist templates."""
    pass


@template.command()
@click.option("--name", required=True, help="Template name")
@click.option("--playlist", "playlist_id", required=True, help="Spotify playlist ID")
@click.option("--description", help="Template description")
@click.option("--tags", help="Comma-separated tags")
def create(name: str, playlist_id: str, description: str, tags: str):
    """Create a new playlist template."""
    _validate_template_name(name)
    _validate_playlist_id(playlist_id)
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Load existing templates
    templates = _load_templates()
    
    # Check if template already exists
    if name in templates:
        raise click.ClickException(f"Template '{name}' already exists. Use a different name or delete the existing template.")
    
    # Create template
    template_data = _create_template(name, playlist_id, description, tag_list)
    templates[name] = template_data
    _save_templates(templates)
    
    click.echo(f"✅ Created template '{name}' with playlist {playlist_id}")
    if description:
        click.echo(f"   Description: {description}")
    if tag_list:
        click.echo(f"   Tags: {', '.join(tag_list)}")


@template.command()
@click.option("--name", help="Filter by template name")
@click.option("--tag", help="Filter by tag")
def list(name: str, tag: str):
    """List playlist templates."""
    templates = _load_templates()
    
    if not templates:
        click.echo("📝 No templates found. Create one with 'template create'")
        return
    
    # Filter templates
    filtered_templates = {}
    for template_name, template_data in templates.items():
        if name and name.lower() not in template_name.lower():
            continue
        if tag and tag.lower() not in [t.lower() for t in template_data.get('tags', [])]:
            continue
        filtered_templates[template_name] = template_data
    
    if not filtered_templates:
        click.echo("📝 No templates match the specified filters")
        return
    
    click.echo(f"📝 Found {len(filtered_templates)} template(s):")
    click.echo()
    
    for template_name, template_data in sorted(filtered_templates.items()):
        click.echo(f"🎵 {template_name}")
        click.echo(f"   Playlist ID: {template_data['playlist_id']}")
        if template_data.get('description'):
            click.echo(f"   Description: {template_data['description']}")
        if template_data.get('tags'):
            click.echo(f"   Tags: {', '.join(template_data['tags'])}")
        click.echo(f"   Created: {template_data.get('created_at', 'Unknown')}")
        click.echo()


@template.command()
@click.option("--name", required=True, help="Template name to delete")
def delete(name: str):
    """Delete a playlist template."""
    templates = _load_templates()
    
    if name not in templates:
        raise click.ClickException(f"Template '{name}' not found")
    
    # Confirm deletion
    if not click.confirm(f"Are you sure you want to delete template '{name}'?"):
        click.echo("❌ Deletion cancelled")
        return
    
    del templates[name]
    _save_templates(templates)
    click.echo(f"✅ Deleted template '{name}'")


@template.command()
@click.option("--name", required=True, help="Template name to use")
@click.option("--chat", "chat_name", required=True, help="iMessage group name")
@click.option("--db", "db_path", default=DEFAULT_DB_PATH, show_default=True,
              help="Path to your Messages chat.db")
@click.option("--output-dir", default="~/Desktop/imessage_dump", show_default=True,
              help="Directory to store exported TXT files")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id", help="Spotify Client ID")
@click.option("--client-secret", help="Spotify Client Secret")
@click.option("--redirect-uri", help="Spotify Redirect URI")
@click.option("--dry-run", is_flag=True, help="Export & extract tracks but do not add to Spotify.")
@click.option("--no-dedupe", is_flag=True, help="Do not skip tracks already in the playlist.")
@click.option("--keep-export", is_flag=True, help="Keep the exported TXT files (default: cleanup)")
@click.option("--force", is_flag=True, help="Force overwrite existing export directory")
@click.option("--show-metadata", is_flag=True, help="Show artist and title when adding tracks")
@click.option("--start-date", help="Only process messages from this date (YYYY-MM-DD)")
@click.option("--end-date", help="Only process messages until this date (YYYY-MM-DD)")
@click.option("--days-back", type=int, help="Only process messages from the last N days")
def use(name: str, chat_name: str, db_path: str, output_dir: str, cache_path: str,
        client_id: str, client_secret: str, redirect_uri: str, dry_run: bool,
        no_dedupe: bool, keep_export: bool, force: bool, show_metadata: bool,
        start_date: str, end_date: str, days_back: int):
    """Use a playlist template to process an iMessage chat."""
    # Load templates
    templates = _load_templates()
    
    if name not in templates:
        raise click.ClickException(f"Template '{name}' not found. Use 'template list' to see available templates.")
    
    template_data = templates[name]
    playlist_id = template_data['playlist_id']
    
    click.echo(f"🎵 Using template '{name}' with playlist {playlist_id}")
    if template_data.get('description'):
        click.echo(f"   Description: {template_data['description']}")
    click.echo()
    
    # Get values from config if not provided
    db_path = db_path or _get_config_value('db_path', DEFAULT_DB_PATH)
    output_dir = output_dir or _get_config_value('output_dir', "~/Desktop/imessage_dump")
    cache_path = cache_path or _get_config_value('cache_path', DEFAULT_CACHE_PATH)
    client_id = client_id or _get_config_value('client_id')
    client_secret = client_secret or _get_config_value('client_secret')
    redirect_uri = redirect_uri or _get_config_value('redirect_uri', "http://127.0.0.1:8000/callback")
    
    # Parse date filters
    start_datetime = None
    end_datetime = None
    
    if days_back:
        from datetime import timedelta
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(days=days_back)
        click.echo(f"📅 Filtering messages from last {days_back} days ({start_datetime.strftime('%Y-%m-%d')} to {end_datetime.strftime('%Y-%m-%d')})")
    elif start_date or end_date:
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                click.echo(f"📅 Filtering messages from {start_date}")
            except ValueError:
                raise click.ClickException(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                click.echo(f"📅 Filtering messages until {end_date}")
            except ValueError:
                raise click.ClickException(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    _validate_chat_name(chat_name)
    _check_imessage_exporter()
    _check_database_access(db_path)

    # Prepare export directory (handles conflicts)
    output_dir = _prepare_export_directory(output_dir, force)

    # 1) Export chat to TXT using imessage-exporter
    click.echo(f"📤 Exporting '{chat_name}' to TXT files...")
    try:
        subprocess.run([
            'imessage-exporter',
            '--format', 'txt',
            '--db-path', db_path,
            '--export-path', output_dir
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Failed to export iMessage data: {e}")

    # 2) Extract Spotify track IDs from the exported files
    click.echo(f"🔍 Extracting Spotify track IDs from exported files...")
    if start_datetime or end_datetime:
        track_ids = _extract_track_ids_with_date_filter(output_dir, chat_name, start_datetime, end_datetime)
    else:
        track_ids = _extract_track_ids_from_export(output_dir, chat_name)

    valid_ids = _validate_ids(track_ids)
    click.echo(f"Found {len(valid_ids)} Spotify tracks in '{chat_name}'")

    if not valid_ids or dry_run:
        if dry_run:
            click.echo("Dry run: not adding to Spotify.")
        _cleanup_export_directory(output_dir, keep_export)
        return

    # 3) Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)

    # 4) Optional dedupe
    if not no_dedupe:
        existing = _existing_track_ids(sp, playlist_id)
        before = len(valid_ids)
        valid_ids = [tid for tid in valid_ids if tid not in existing]
        click.echo(f"Skipping {before - len(valid_ids)} duplicates already in playlist.")

    if not valid_ids:
        click.echo("Nothing new to add after deduplication.")
        _cleanup_export_directory(output_dir, keep_export)
        return

    # 5) Add to playlist
    uris = [f"spotify:track:{tid}" for tid in valid_ids]
    
    # Fetch metadata if requested
    metadata = {}
    if show_metadata and valid_ids:
        click.echo("📊 Fetching track metadata...")
        metadata = _get_track_metadata(sp, valid_ids)
    
    with click.progressbar(length=len(uris), label="Adding tracks to playlist") as bar:
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            batch_ids = valid_ids[i:i+100]
            
            try:
                sp.playlist_add_items(playlist_id, batch)
                
                # Show metadata for this batch if requested
                if show_metadata:
                    for track_id in batch_ids:
                        if track_id in metadata:
                            click.echo(f"  ➕ {metadata[track_id]['display_name']}")
                        else:
                            click.echo(f"  ➕ Track ID: {track_id}")
                
                bar.update(len(batch))
            except Exception as e:
                click.echo(f"⚠️  Error adding batch {i//100 + 1}: {e}")
                # Continue with next batch

    click.echo(f"✅ Done! Added {len(uris)} tracks to playlist {playlist_id}.")

    # 6) Cleanup (unless --keep-export)
    _cleanup_export_directory(output_dir, keep_export)


@cli.group()
def backup():
    """Manage playlist backups."""
    pass


@backup.command()
@click.option("--name", required=True, help="Backup name")
@click.option("--playlist", "playlist_id", required=True, help="Spotify playlist ID to backup")
@click.option("--description", help="Backup description")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id", help="Spotify Client ID")
@click.option("--client-secret", help="Spotify Client Secret")
@click.option("--redirect-uri", help="Spotify Redirect URI")
def create(name: str, playlist_id: str, description: str, cache_path: str,
           client_id: str, client_secret: str, redirect_uri: str):
    """Create a backup of a playlist's current state."""
    _validate_backup_name(name)
    _validate_playlist_id(playlist_id)
    
    # Get values from config if not provided
    cache_path = cache_path or _get_config_value('cache_path', DEFAULT_CACHE_PATH)
    client_id = client_id or _get_config_value('client_id')
    client_secret = client_secret or _get_config_value('client_secret')
    redirect_uri = redirect_uri or _get_config_value('redirect_uri', "http://127.0.0.1:8000/callback")
    
    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    
    # Load existing backups
    backups = _load_backups()
    
    # Check if backup already exists
    if name in backups:
        raise click.ClickException(f"Backup '{name}' already exists. Use a different name or delete the existing backup.")
    
    # Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)
    
    # Get playlist info
    try:
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        click.echo(f"📋 Creating backup of playlist: {playlist_name}")
    except Exception as e:
        raise click.ClickException(f"Failed to fetch playlist: {e}")
    
    # Get all tracks
    click.echo("📊 Fetching playlist tracks...")
    tracks = _get_playlist_tracks(sp, playlist_id)
    
    if not tracks:
        click.echo("⚠️  Playlist is empty. Creating empty backup.")
    
    # Create backup
    backup_data = _create_backup(name, playlist_id, tracks, description)
    backups[name] = backup_data
    _save_backups(backups)
    
    click.echo(f"✅ Created backup '{name}' with {len(tracks)} tracks")
    if description:
        click.echo(f"   Description: {description}")
    click.echo(f"   Playlist: {playlist_name} ({playlist_id})")


@backup.command()
@click.option("--name", help="Filter by backup name")
@click.option("--playlist", "playlist_id", help="Filter by playlist ID")
def list(name: str, playlist_id: str):
    """List playlist backups."""
    backups = _load_backups()
    
    if not backups:
        click.echo("💾 No backups found. Create one with 'backup create'")
        return
    
    # Filter backups
    filtered_backups = {}
    for backup_name, backup_data in backups.items():
        if name and name.lower() not in backup_name.lower():
            continue
        if playlist_id and playlist_id != backup_data['playlist_id']:
            continue
        filtered_backups[backup_name] = backup_data
    
    if not filtered_backups:
        click.echo("💾 No backups match the specified filters")
        return
    
    click.echo(f"💾 Found {len(filtered_backups)} backup(s):")
    click.echo()
    
    for backup_name, backup_data in sorted(filtered_backups.items()):
        click.echo(f"💾 {backup_name}")
        click.echo(f"   Playlist ID: {backup_data['playlist_id']}")
        click.echo(f"   Tracks: {backup_data['track_count']}")
        if backup_data.get('description'):
            click.echo(f"   Description: {backup_data['description']}")
        click.echo(f"   Created: {backup_data.get('created_at', 'Unknown')}")
        click.echo()


@backup.command()
@click.option("--name", required=True, help="Backup name to delete")
def delete(name: str):
    """Delete a playlist backup."""
    backups = _load_backups()
    
    if name not in backups:
        raise click.ClickException(f"Backup '{name}' not found")
    
    # Confirm deletion
    if not click.confirm(f"Are you sure you want to delete backup '{name}'?"):
        click.echo("❌ Deletion cancelled")
        return
    
    del backups[name]
    _save_backups(backups)
    click.echo(f"✅ Deleted backup '{name}'")


@backup.command()
@click.option("--name", required=True, help="Backup name to restore")
@click.option("--playlist", "playlist_id", help="Target playlist ID (default: original playlist)")
@click.option("--cache", "cache_path", default=DEFAULT_CACHE_PATH, show_default=True,
              help="Where to store Spotify OAuth cache")
@click.option("--client-id", help="Spotify Client ID")
@click.option("--client-secret", help="Spotify Client Secret")
@click.option("--redirect-uri", help="Spotify Redirect URI")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without making changes")
@click.option("--clear-first", is_flag=True, help="Clear playlist before restoring")
def restore(name: str, playlist_id: str, cache_path: str, client_id: str, 
            client_secret: str, redirect_uri: str, dry_run: bool, clear_first: bool):
    """Restore a playlist from a backup."""
    # Load backups
    backups = _load_backups()
    
    if name not in backups:
        raise click.ClickException(f"Backup '{name}' not found. Use 'backup list' to see available backups.")
    
    backup_data = backups[name]
    original_playlist_id = backup_data['playlist_id']
    target_playlist_id = playlist_id or original_playlist_id
    
    click.echo(f"💾 Restoring backup '{name}' to playlist {target_playlist_id}")
    if backup_data.get('description'):
        click.echo(f"   Description: {backup_data['description']}")
    click.echo(f"   Original playlist: {original_playlist_id}")
    click.echo(f"   Tracks to restore: {backup_data['track_count']}")
    click.echo()
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made")
        click.echo("📋 Tracks that would be restored:")
        for i, track in enumerate(backup_data['tracks'][:10], 1):  # Show first 10
            artist = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
            click.echo(f"   {i}. {artist} - {track['name']}")
        if len(backup_data['tracks']) > 10:
            click.echo(f"   ... and {len(backup_data['tracks']) - 10} more tracks")
        return
    
    # Get values from config if not provided
    cache_path = cache_path or _get_config_value('cache_path', DEFAULT_CACHE_PATH)
    client_id = client_id or _get_config_value('client_id')
    client_secret = client_secret or _get_config_value('client_secret')
    redirect_uri = redirect_uri or _get_config_value('redirect_uri', "http://127.0.0.1:8000/callback")
    
    # Validate inputs
    _validate_spotify_credentials(client_id, client_secret)
    _validate_playlist_id(target_playlist_id)
    
    # Spotify auth
    sp = _safe_spotify_auth(client_id, client_secret, redirect_uri, cache_path)
    
    # Clear playlist if requested
    if clear_first:
        click.echo("🗑️  Clearing target playlist...")
        try:
            # Get current tracks
            current_tracks = _get_playlist_tracks(sp, target_playlist_id)
            if current_tracks:
                # Remove all tracks
                track_uris = [f"spotify:track:{track['id']}" for track in current_tracks]
                for i in range(0, len(track_uris), 100):
                    batch = track_uris[i:i+100]
                    sp.playlist_remove_all_occurrences_of_items(target_playlist_id, batch)
                click.echo(f"   Removed {len(current_tracks)} existing tracks")
        except Exception as e:
            raise click.ClickException(f"Failed to clear playlist: {e}")
    
    # Restore tracks
    tracks_to_restore = backup_data['tracks']
    if not tracks_to_restore:
        click.echo("✅ Backup is empty - no tracks to restore")
        return
    
    click.echo(f"🔄 Restoring {len(tracks_to_restore)} tracks...")
    
    # Convert to URIs
    track_uris = [f"spotify:track:{track['id']}" for track in tracks_to_restore]
    
    # Add tracks in batches
    with click.progressbar(length=len(track_uris), label="Restoring tracks") as bar:
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            batch_tracks = tracks_to_restore[i:i+100]
            
            try:
                sp.playlist_add_items(target_playlist_id, batch)
                
                # Show some track info
                if i == 0:  # Show first batch
                    for track in batch_tracks[:5]:  # Show first 5
                        artist = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
                        click.echo(f"  ➕ {artist} - {track['name']}")
                    if len(batch_tracks) > 5:
                        click.echo(f"  ➕ ... and {len(batch_tracks) - 5} more")
                
                bar.update(len(batch))
            except Exception as e:
                click.echo(f"⚠️  Error restoring batch {i//100 + 1}: {e}")
                # Continue with next batch
    
    click.echo(f"✅ Successfully restored {len(tracks_to_restore)} tracks to playlist {target_playlist_id}")


def _load_templates() -> dict:
    """Load playlist templates from config file."""
    config = _load_config()
    return config.get('templates', {})


def _save_templates(templates: dict) -> None:
    """Save playlist templates to config file."""
    config = _load_config()
    config['templates'] = templates
    _save_config(config)


def _create_template(name: str, playlist_id: str, description: str = "", tags: list = None) -> dict:
    """Create a playlist template."""
    if tags is None:
        tags = []
    
    return {
        'name': name,
        'playlist_id': playlist_id,
        'description': description,
        'tags': tags,
        'created_at': datetime.now().isoformat()
    }


def _validate_template_name(name: str) -> None:
    """Validate template name."""
    if not name or not name.strip():
        raise click.ClickException("Template name cannot be empty")
    
    if len(name) > 50:
        raise click.ClickException("Template name must be 50 characters or less")
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
        raise click.ClickException("Template name can only contain letters, numbers, spaces, hyphens, and underscores")


def _load_config() -> dict:
    """Load configuration from file."""
    config_path = Path(DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        click.echo(f"⚠️  Could not load config file: {e}")
        return {}


def _save_config(config: dict) -> None:
    """Save configuration to file."""
    config_path = Path(DEFAULT_CONFIG_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        click.echo(f"⚠️  Could not save config file: {e}")


def _get_config_value(key: str, default=None):
    """Get a value from config, with fallback to environment variables."""
    config = _load_config()
    
    # Check config file first
    if key in config:
        return config[key]
    
    # Fallback to environment variables
    env_mapping = {
        'client_id': 'SPOTIPY_CLIENT_ID',
        'client_secret': 'SPOTIPY_CLIENT_SECRET',
        'redirect_uri': 'SPOTIPY_REDIRECT_URI',
        'playlist_id': 'SPOTIFY_PLAYLIST_ID',
        'db_path': 'IMESSAGE_DB_PATH',
        'output_dir': 'IMESSAGE_OUTPUT_DIR',
        'cache_path': 'SPOTIFY_CACHE_PATH'
    }
    
    env_var = env_mapping.get(key)
    if env_var and env_var in os.environ:
        return os.environ[env_var]
    
    return default


def _load_backups() -> dict:
    """Load playlist backups from config file."""
    config = _load_config()
    return config.get('backups', {})


def _save_backups(backups: dict) -> None:
    """Save playlist backups to config file."""
    config = _load_config()
    config['backups'] = backups
    _save_config(config)


def _create_backup(name: str, playlist_id: str, tracks: list, description: str = "") -> dict:
    """Create a playlist backup."""
    return {
        'name': name,
        'playlist_id': playlist_id,
        'tracks': tracks,
        'description': description,
        'created_at': datetime.now().isoformat(),
        'track_count': len(tracks)
    }


def _validate_backup_name(name: str) -> None:
    """Validate backup name."""
    if not name or not name.strip():
        raise click.ClickException("Backup name cannot be empty")
    
    if len(name) > 50:
        raise click.ClickException("Backup name must be 50 characters or less")
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
        raise click.ClickException("Backup name can only contain letters, numbers, spaces, hyphens, and underscores")


def _get_playlist_tracks(sp, playlist_id: str) -> list:
    """Get all tracks from a playlist with metadata."""
    tracks = []
    limit, offset = 100, 0
    
    try:
        while True:
            payload = sp.playlist_items(
                playlist_id, 
                fields="items(track(id,name,artists(name),album(name),duration_ms,external_urls(spotify)))",
                limit=limit, 
                offset=offset
            )
            
            for item in payload.get("items", []):
                track = item.get("track")
                if track and track.get("id"):
                    tracks.append(track)
            
            if payload.get("next"):
                offset += limit
            else:
                break
                
    except Exception as e:
        raise click.ClickException(f"Failed to fetch playlist tracks: {e}")
    
    return tracks


if __name__ == "__main__":
    cli()
