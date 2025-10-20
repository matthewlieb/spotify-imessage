"""
Android Messages integration for spotify-message.

This module handles parsing Android Messages export files and extracting
Spotify track IDs from various Android export formats.
"""

import re
import os
from datetime import datetime
from typing import Set, List, Optional, Tuple
from pathlib import Path


# Regex patterns for different Android export formats
ANDROID_DATE_PATTERNS = [
    # Standard format: 2024-01-15 14:30:22
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
    # US format: Jan 21, 2024 16:45:22
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4} \d{2}:\d{2}:\d{2}',
    # European format: 21/01/2024 17:30:15
    r'(\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2})',
    # ISO format: 2024-01-22T20:15:33
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
]

# Spotify URL pattern (same as iMessage)
SPOTIFY_URL_RE = re.compile(r'open\.spotify\.com/track/([A-Za-z0-9]{22})')

# Android message line patterns
ANDROID_LINE_PATTERNS = [
    # Standard: 2024-01-15 14:30:22 - John Doe: Message
    r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - .*: .*$',
    # US format: Jan 21, 2024 16:45:22 - Jane Smith: Message
    r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4} \d{2}:\d{2}:\d{2} - .*: .*$',
    # European: 21/01/2024 17:30:15 - Bob: Message
    r'^\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2} - .*: .*$',
    # Group chat: 2024-01-23 14:01:00 - Music Group - John Doe: Message
    r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - .* - .*: .*$',
]


def is_android_export_line(line: str) -> bool:
    """
    Check if a line matches Android Messages export format.
    
    Args:
        line: The line to check
        
    Returns:
        True if the line matches Android format, False otherwise
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return False
    
    return any(re.match(pattern, line) for pattern in ANDROID_LINE_PATTERNS)


def parse_android_date(date_str: str) -> Optional[datetime]:
    """
    Parse Android date format into datetime object.
    
    Args:
        date_str: Date string from Android export
        
    Returns:
        datetime object or None if parsing fails
    """
    date_formats = [
        '%Y-%m-%d %H:%M:%S',      # 2024-01-15 14:30:22
        '%b %d, %Y %H:%M:%S',     # Jan 21, 2024 16:45:22
        '%d/%m/%Y %H:%M:%S',      # 21/01/2024 17:30:15
        '%Y-%m-%dT%H:%M:%S',      # 2024-01-22T20:15:33
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def extract_track_ids_from_android_export(export_file: str, 
                                        start_date: Optional[datetime] = None,
                                        end_date: Optional[datetime] = None) -> Set[str]:
    """
    Extract Spotify track IDs from Android Messages export file.
    
    Args:
        export_file: Path to Android export file
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        Set of unique Spotify track IDs
    """
    track_ids: Set[str] = set()
    
    if not os.path.exists(export_file):
        raise FileNotFoundError(f"Android export file not found: {export_file}")
    
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Check if it's an Android export line
                if not is_android_export_line(line):
                    continue
                
                # Extract date if filtering is enabled
                if start_date or end_date:
                    date_match = None
                    for pattern in ANDROID_DATE_PATTERNS:
                        match = re.search(pattern, line)
                        if match:
                            date_match = match.group(1)
                            break
                    
                    if date_match:
                        parsed_date = parse_android_date(date_match)
                        if parsed_date:
                            if start_date and parsed_date < start_date:
                                continue
                            if end_date and parsed_date > end_date:
                                continue
                
                # Extract Spotify track IDs
                matches = SPOTIFY_URL_RE.findall(line)
                track_ids.update(matches)
                
    except UnicodeDecodeError:
        # Try with different encoding
        with open(export_file, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if is_android_export_line(line):
                    matches = SPOTIFY_URL_RE.findall(line)
                    track_ids.update(matches)
    
    return track_ids


def extract_track_ids_with_metadata(export_file: str) -> List[Tuple[str, str, datetime]]:
    """
    Extract Spotify track IDs with sender and timestamp metadata.
    
    Args:
        export_file: Path to Android export file
        
    Returns:
        List of tuples: (track_id, sender, timestamp)
    """
    tracks_with_metadata = []
    
    if not os.path.exists(export_file):
        raise FileNotFoundError(f"Android export file not found: {export_file}")
    
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                if not is_android_export_line(line):
                    continue
                
                # Extract date
                date_match = None
                for pattern in ANDROID_DATE_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        date_match = match.group(1)
                        break
                
                if not date_match:
                    continue
                
                parsed_date = parse_android_date(date_match)
                if not parsed_date:
                    continue
                
                # Extract sender (simplified - could be improved)
                sender_match = re.search(r' - ([^-]+): ', line)
                if not sender_match:
                    continue
                
                sender = sender_match.group(1).strip()
                
                # Extract track IDs
                track_ids = SPOTIFY_URL_RE.findall(line)
                
                for track_id in track_ids:
                    tracks_with_metadata.append((track_id, sender, parsed_date))
                    
    except UnicodeDecodeError:
        # Try with different encoding
        with open(export_file, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if not is_android_export_line(line):
                    continue
                
                # Extract date
                date_match = None
                for pattern in ANDROID_DATE_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        date_match = match.group(1)
                        break
                
                if not date_match:
                    continue
                
                parsed_date = parse_android_date(date_match)
                if not parsed_date:
                    continue
                
                # Extract sender
                sender_match = re.search(r' - ([^-]+): ', line)
                if not sender_match:
                    continue
                
                sender = sender_match.group(1).strip()
                
                # Extract track IDs
                track_ids = SPOTIFY_URL_RE.findall(line)
                
                for track_id in track_ids:
                    tracks_with_metadata.append((track_id, sender, parsed_date))
    
    return tracks_with_metadata


def validate_android_export_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that a file appears to be an Android Messages export.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Check first 10 lines for Android format
            android_lines = 0
            total_lines = 0
            
            for i, line in enumerate(f):
                if i >= 10:  # Only check first 10 lines
                    break
                
                line = line.strip()
                if line and not line.startswith('#'):
                    total_lines += 1
                    if is_android_export_line(line):
                        android_lines += 1
            
            if total_lines == 0:
                return False, "File appears to be empty or contains only comments"
            
            # If more than 50% of lines match Android format, consider it valid
            if android_lines / total_lines >= 0.5:
                return True, "File appears to be a valid Android Messages export"
            else:
                return False, "File does not appear to be an Android Messages export"
                
    except UnicodeDecodeError:
        return False, "File encoding not supported (try UTF-8)"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def get_android_export_stats(file_path: str) -> dict:
    """
    Get statistics about an Android Messages export file.
    
    Args:
        file_path: Path to the Android export file
        
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total_lines': 0,
        'android_lines': 0,
        'spotify_tracks': 0,
        'unique_tracks': 0,
        'date_range': None,
        'senders': set(),
        'errors': []
    }
    
    if not os.path.exists(file_path):
        stats['errors'].append(f"File not found: {file_path}")
        return stats
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            dates = []
            
            for line in f:
                stats['total_lines'] += 1
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                if is_android_export_line(line):
                    stats['android_lines'] += 1
                    
                    # Extract date
                    for pattern in ANDROID_DATE_PATTERNS:
                        match = re.search(pattern, line)
                        if match:
                            parsed_date = parse_android_date(match.group(1))
                            if parsed_date:
                                dates.append(parsed_date)
                            break
                    
                    # Extract sender
                    sender_match = re.search(r' - ([^-]+): ', line)
                    if sender_match:
                        stats['senders'].add(sender_match.group(1).strip())
                    
                    # Count Spotify tracks
                    track_ids = SPOTIFY_URL_RE.findall(line)
                    stats['spotify_tracks'] += len(track_ids)
            
            # Calculate unique tracks
            all_tracks = extract_track_ids_from_android_export(file_path)
            stats['unique_tracks'] = len(all_tracks)
            
            # Calculate date range
            if dates:
                stats['date_range'] = {
                    'start': min(dates),
                    'end': max(dates),
                    'days': (max(dates) - min(dates)).days
                }
            
            # Convert set to list for JSON serialization
            stats['senders'] = list(stats['senders'])
            
    except UnicodeDecodeError:
        stats['errors'].append("File encoding not supported (try UTF-8)")
    except Exception as e:
        stats['errors'].append(f"Error processing file: {str(e)}")
    
    return stats
