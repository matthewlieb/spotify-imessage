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
from typing import Iterable, List, Set

import click
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# Defaults
DEFAULT_DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")
DEFAULT_ATTACH_DIR = os.path.expanduser("~/Library/Messages/Attachments")
DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/spotify-imessage/spotify_token.json")

# Regexes
SPOTIFY_ID_RE = re.compile(r"[A-Za-z0-9]{22}")
SPOTIFY_URL_RE = re.compile(r"open\.spotify\.com/track/([A-Za-z0-9]{22})")


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
    while True:
        payload = sp.playlist_items(
            playlist_id, fields="items(track(uri)),next", limit=limit, offset=offset
        )
        for it in payload.get("items", []):
            uri = (it.get("track") or {}).get("uri") or ""
            parts = uri.split(":")  # spotify:track:<id>
            if len(parts) == 3 and parts[1] == "track" and SPOTIFY_ID_RE.fullmatch(parts[2]):
                seen.add(parts[2])
        if payload.get("next"):
            offset += limit
        else:
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


@click.group()
def cli():
    """Sync Spotify tracks into a playlist from various sources."""
    pass


@cli.command()
@click.option("--chat", "chat_name", required=True, help="iMessage group name")
@click.option("--playlist", "playlist_id", required=True, help="Target Spotify playlist ID")
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
             keep_export: bool):
    """Extract Spotify tracks from an iMessage group using imessage-exporter and add them to a playlist."""
    # Expand paths
    db_path = os.path.expanduser(db_path)
    output_dir = os.path.expanduser(output_dir)
    cache_path = os.path.expanduser(cache_path)

    # Check if imessage-exporter is installed
    try:
        subprocess.run(['imessage-exporter', '--help'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise click.ClickException(
            "imessage-exporter not found. Install it with: brew install imessage-exporter"
        )

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

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
    track_ids = _extract_track_ids_from_export(output_dir, chat_name)

    valid_ids = _validate_ids(track_ids)
    click.echo(f"Found {len(valid_ids)} Spotify tracks in '{chat_name}'")

    if not valid_ids or dry_run:
        if dry_run:
            click.echo("Dry run: not adding to Spotify.")
        if not keep_export:
            click.echo("🧹 Cleaning up exported files...")
            import shutil
            shutil.rmtree(output_dir)
        return

    # 3) Spotify auth
    sp = _get_spotify_client(client_id, client_secret, redirect_uri, cache_path)

    # 4) Optional dedupe
    if not no_dedupe:
        existing = _existing_track_ids(sp, playlist_id)
        before = len(valid_ids)
        valid_ids = [tid for tid in valid_ids if tid not in existing]
        click.echo(f"Skipping {before - len(valid_ids)} duplicates already in playlist.")

    if not valid_ids:
        click.echo("Nothing new to add after deduplication.")
        if not keep_export:
            click.echo("🧹 Cleaning up exported files...")
            import shutil
            shutil.rmtree(output_dir)
        return

    # 5) Add to playlist
    uris = [f"spotify:track:{tid}" for tid in valid_ids]
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist_id, uris[i:i+100])

    click.echo(f"✅ Done! Added {len(uris)} tracks to playlist {playlist_id}.")

    # 6) Cleanup (unless --keep-export)
    if not keep_export:
        click.echo("🧹 Cleaning up exported files...")
        import shutil
        shutil.rmtree(output_dir)


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
def file(track_file: str,
         playlist_id: str,
         cache_path: str,
         client_id: str,
         client_secret: str,
         redirect_uri: str,
         dry_run: bool,
         no_dedupe: bool):
    """Add Spotify tracks from a text file to a playlist."""
    # Expand paths
    track_file = os.path.expanduser(track_file)
    cache_path = os.path.expanduser(cache_path)

    if not os.path.exists(track_file):
        raise click.ClickException(f"Track file not found: {track_file}")

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
    sp = _get_spotify_client(client_id, client_secret, redirect_uri, cache_path)

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
    for i in range(0, len(uris), 100):
        batch = uris[i:i+100]
        sp.playlist_add_items(playlist_id, batch)

    click.echo(f"🎉 Done — added {len(uris)} tracks to playlist {playlist_id}!")


if __name__ == "__main__":
    cli()
