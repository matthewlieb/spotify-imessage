# spotify-imessage

A powerful CLI tool to extract **Spotify** tracks from iMessage conversations and manage them in Spotify playlists.

## ✨ Features

### Core Functionality
- **iMessage Integration**: Extract tracks from iMessage group chats using `imessage-exporter`
- **File Processing**: Add tracks from text files containing track IDs
- **Batch Operations**: Process multiple chats simultaneously
- **Export Formats**: Export playlists to CSV, JSON, TXT, and M3U formats

### Advanced Features
- **Track Metadata**: Display artist and title information when adding tracks
- **Date Filtering**: Process messages from specific date ranges or recent periods
- **Playlist Templates**: Save and reuse playlist configurations
- **Backup & Restore**: Create snapshots of playlist states and restore them later

### User Experience
- **Progress Bars**: Visual feedback for long operations
- **Configuration System**: Persistent settings and credentials
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **Directory Management**: Automatic cleanup and conflict resolution

---

## Requirements

- **macOS** with **Full Disk Access** granted to your terminal/IDE  
  _System Settings → Privacy & Security → Full Disk Access → enable your Terminal/IDE_
- **Python 3.9+**
- **Spotify Developer App** (Client ID/Secret) and Redirect URI (e.g. `http://127.0.0.1:8000/callback`)
- **imessage-exporter** (recommended for robust exports):
  ```bash
  brew install imessage-exporter
  ```

> **Privacy:** All iMessage data is processed **locally**. Only Spotify track IDs are sent to Spotify's Web API.

---

## Installation

From source (editable install):

```bash
# from the repo root (spotify-imessage/)
pip install -e .
```

> Tip: use `pipx install .` if you prefer an isolated CLI install.

---

## Quick Start

### 1. Configure Spotify Credentials

Set environment variables (recommended):

```bash
export SPOTIPY_CLIENT_ID="YOUR_CLIENT_ID"
export SPOTIPY_CLIENT_SECRET="YOUR_CLIENT_SECRET"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000/callback"
```

Or use the configuration system:

```bash
spotify-imessage config --set client_id=YOUR_CLIENT_ID
spotify-imessage config --set client_secret=YOUR_CLIENT_SECRET
spotify-imessage config --set playlist_id=YOUR_DEFAULT_PLAYLIST_ID
```

### 2. Extract Tracks from iMessage

```bash
# Basic usage
spotify-imessage imessage --chat "My Chat Name" --playlist YOUR_PLAYLIST_ID

# With metadata and date filtering
spotify-imessage imessage \
  --chat "My Chat Name" \
  --playlist YOUR_PLAYLIST_ID \
  --show-metadata \
  --days-back 30
```

---

## Usage

### iMessage Mode

Extract Spotify tracks from iMessage group chats:

```bash
spotify-imessage imessage \
  --chat "My daughter is dating Kodak Black" \
  --playlist 1c68uZNKCUx7a1l6wr97D3
```

**Options:**
- `--show-metadata` - Display artist and title when adding tracks
- `--start-date YYYY-MM-DD` - Only process messages from this date
- `--end-date YYYY-MM-DD` - Only process messages until this date
- `--days-back N` - Only process messages from the last N days
- `--force` - Force overwrite existing export directory
- `--keep-export` - Keep exported files (default: cleanup)

### File Mode

Add tracks from a text file:

```bash
spotify-imessage file \
  --file track_ids.txt \
  --playlist 1c68uZNKCUx7a1l6wr97D3 \
  --show-metadata
```

**Track file format:**
```
# Comments start with #
4iV5W9uYEdYUVa79Axb7Rh
6rqhFgbbKwnb9MLmUQDhG6
3CRDbSIZ4r5MsZ0YwxuEkn
```

### Batch Processing

Process multiple chats at once:

```bash
# Single playlist for all chats
spotify-imessage batch \
  --chats "Chat1,Chat2,Chat3" \
  --playlist YOUR_PLAYLIST_ID \
  --show-metadata

# Separate playlists for each chat
spotify-imessage batch \
  --chats "Chat1,Chat2" \
  --playlist "Base Playlist Name" \
  --separate-playlists \
  --days-back 7
```

### Export Playlists

Export playlists to various formats:

```bash
# Export to CSV with metadata
spotify-imessage export \
  --playlist YOUR_PLAYLIST_ID \
  --format csv \
  --include-metadata \
  --output my_playlist.csv

# Export to JSON
spotify-imessage export \
  --playlist YOUR_PLAYLIST_ID \
  --format json \
  --output my_playlist.json

# Export to M3U playlist
spotify-imessage export \
  --playlist YOUR_PLAYLIST_ID \
  --format m3u \
  --output my_playlist.m3u
```

**Supported formats:** `csv`, `json`, `txt`, `m3u`

### Playlist Templates

Create and use playlist templates:

```bash
# Create a template
spotify-imessage template create \
  --name "Family Music" \
  --playlist YOUR_PLAYLIST_ID \
  --description "Music shared in family chats" \
  --tags "family,shared,music"

# List templates
spotify-imessage template list --tag "family"

# Use a template
spotify-imessage template use \
  --name "Family Music" \
  --chat "Familia" \
  --show-metadata \
  --days-back 30
```

### Backup & Restore

Create and restore playlist snapshots:

```bash
# Create a backup
spotify-imessage backup create \
  --name "Before Changes" \
  --playlist YOUR_PLAYLIST_ID \
  --description "Backup before testing"

# List backups
spotify-imessage backup list

# Preview restore (dry run)
spotify-imessage backup restore \
  --name "Before Changes" \
  --dry-run

# Restore to same playlist
spotify-imessage backup restore \
  --name "Before Changes"

# Restore to different playlist with clear
spotify-imessage backup restore \
  --name "Before Changes" \
  --playlist NEW_PLAYLIST_ID \
  --clear-first
```

### Configuration Management

Manage persistent settings:

```bash
# Set configuration values
spotify-imessage config --set playlist_id=YOUR_PLAYLIST_ID
spotify-imessage config --set client_id=YOUR_CLIENT_ID
spotify-imessage config --set client_secret=YOUR_CLIENT_SECRET

# View configuration
spotify-imessage config --list

# Get specific value
spotify-imessage config --get playlist_id

# Reset configuration
spotify-imessage config --reset
```

---

## Common Options

Most commands support these options:

- `--dry-run` - Discover tracks but don't add them
- `--no-dedupe` - Don't skip tracks already in playlist
- `--show-metadata` - Display artist and title information
- `--start-date YYYY-MM-DD` - Filter by start date
- `--end-date YYYY-MM-DD` - Filter by end date
- `--days-back N` - Filter by recent days
- `--force` - Force overwrite existing directories
- `--keep-export` - Keep exported files

---

## Configuration

The tool uses a configuration file at `~/.config/spotify-imessage/config.json`:

```json
{
  "client_id": "your_spotify_client_id",
  "client_secret": "your_spotify_client_secret",
  "redirect_uri": "http://127.0.0.1:8000/callback",
  "playlist_id": "your_default_playlist_id",
  "db_path": "~/Library/Messages/chat.db",
  "output_dir": "~/Desktop/imessage_dump",
  "cache_path": "~/.cache/spotify-imessage/spotify_token.json",
  "templates": {
    "Family Music": {
      "name": "Family Music",
      "playlist_id": "playlist_id",
      "description": "Music shared in family chats",
      "tags": ["family", "shared", "music"],
      "created_at": "2025-08-29T00:29:42.736699"
    }
  },
  "backups": {
    "Before Changes": {
      "name": "Before Changes",
      "playlist_id": "playlist_id",
      "tracks": [...],
      "description": "Backup before testing",
      "created_at": "2025-08-29T00:37:43.420077",
      "track_count": 100
    }
  }
}
```

---

## How It Works

### iMessage Export Process

1. **Export**: Uses `imessage-exporter` to export your entire iMessage database to TXT files
2. **Extract**: Uses `grep` to find all Spotify track URLs in the exported files
3. **Filter**: Applies date filters if specified
4. **Validate**: Validates 22-character Base62 track IDs
5. **Dedupe**: Checks for existing tracks in the target playlist
6. **Add**: Batches tracks in groups of 100 and adds to Spotify playlist

### File Processing

1. **Read**: Parses track IDs from text file (supports comments with `#`)
2. **Validate**: Ensures all IDs are valid Spotify track IDs
3. **Process**: Same deduplication and batching as iMessage mode

### Date Filtering

- Parses timestamps from iMessage export format: `Dec 01, 2022 5:10:27 PM`
- Supports multiple date formats and time zones
- Filters messages by date range or relative time periods

---

## Troubleshooting

### Permission Issues
- **No messages / permission errors**: Ensure your Terminal/IDE has **Full Disk Access**
- **Can't access Messages database**: Restart your terminal after granting permissions

### Spotify Issues
- **Invalid base62 id**: Check your playlist ID (should be 22 characters like `1c68uZNKCUx7a1l6wr97D3`)
- **OAuth errors**: Verify your Client ID/Secret and Redirect URI
- **Rate limiting**: The tool automatically handles Spotify API rate limits

### Export Issues
- **Directory already exists**: Use `--force` flag or the tool will create unique directories
- **No tracks found**: Check chat name spelling and ensure Spotify links exist in the chat
- **imessage-exporter not found**: Install with `brew install imessage-exporter`

### Configuration Issues
- **Missing credentials**: Set environment variables or use `config --set`
- **Invalid configuration**: Use `config --reset` to start fresh

---

## Development

### Local Development
```bash
# Editable install
pip install -e .

# Run with local changes
spotify-imessage --help
```

### Project Structure
```
src/spotify_imessage/
├── __init__.py
└── cli.py              # Main CLI implementation
```

### Key Functions
- `_extract_track_ids_from_export()` - Extract Spotify IDs from exported files
- `_extract_track_ids_with_date_filter()` - Date-filtered extraction
- `_get_track_metadata()` - Fetch artist/title information
- `_load_config()` / `_save_config()` - Configuration management
- `_load_templates()` / `_save_templates()` - Template management
- `_load_backups()` / `_save_backups()` - Backup management

### Full Command Help

```bash
# Main help
spotify-imessage --help

# Command-specific help
spotify-imessage imessage --help
spotify-imessage file --help
spotify-imessage batch --help
spotify-imessage export --help
spotify-imessage template --help
spotify-imessage backup --help
spotify-imessage config --help
```

---

## License

MIT © Matthew Lieb

