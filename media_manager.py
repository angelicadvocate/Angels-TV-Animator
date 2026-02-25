"""
Angels-TV-Animator: Media management module.
Handles state persistence, file discovery, media type detection, and broadcast helpers.
"""

import json
import logging
from pathlib import Path

from config import (
    STATE_FILE, ANIMATIONS_DIR, VIDEOS_DIR,
    HTML_EXTENSIONS, VIDEO_EXTENSIONS
)
from extensions import socketio

logger = logging.getLogger(__name__)


# =============================================================================
# State Management
# =============================================================================

def load_state():
    """Load the current state from state.json"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        default_state = {"current_animation": "anim1.html"}
        save_state(default_state)
        return default_state


def save_state(state):
    """Save the current state to state.json"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)


def ensure_state_file():
    """Initialize state file if it doesn't exist"""
    if not STATE_FILE.exists():
        save_state({"current_animation": "anim1.html"})


# =============================================================================
# File Discovery
# =============================================================================

def get_animation_files():
    """Get list of all animation HTML files"""
    if not ANIMATIONS_DIR.exists():
        return []
    return sorted([f.name for f in ANIMATIONS_DIR.glob("*.html")])


def get_video_files():
    """Get list of all video files"""
    if not VIDEOS_DIR.exists():
        return []
    video_files = []
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(VIDEOS_DIR.glob(f"*{ext}"))
    return sorted([f.name for f in video_files])


def get_all_media_files():
    """Get list of all supported media files (HTML animations + videos)"""
    return sorted(get_animation_files() + get_video_files())


# =============================================================================
# Media Type Detection
# =============================================================================

def is_video_file(filename):
    """Check if a filename has a video extension"""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def is_html_file(filename):
    """Check if a filename has an HTML extension"""
    return Path(filename).suffix.lower() in HTML_EXTENSIONS


# =============================================================================
# Media File Lookup
# =============================================================================

def find_media_file(filename):
    """Find a media file in either animations or videos directory"""
    animation_path = ANIMATIONS_DIR / filename
    if animation_path.exists():
        return animation_path, 'animation'
    
    video_path = VIDEOS_DIR / filename
    if video_path.exists():
        return video_path, 'video'
    
    return None, None


# =============================================================================
# Video Serving Helper
# =============================================================================

def serve_video(video_filename):
    """Serve a video file using the video player template"""
    video_url = f"/videos/{video_filename}"
    
    video_ext = Path(video_filename).suffix.lower()
    video_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'video/ogg',
        '.avi': 'video/avi',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska'
    }
    video_type = video_types.get(video_ext, 'video/mp4')
    
    try:
        with open('templates/video_player_template.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        html_content = template_content.replace('{{ video_filename }}', video_filename)
        html_content = html_content.replace('{{ video_url }}', video_url)
        html_content = html_content.replace('{{ video_type }}', video_type)
        
        return html_content, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Error loading video player template: {e}", 500


# =============================================================================
# Broadcast Helper
# =============================================================================

def broadcast_media_change(media_file, media_type, source='api'):
    """
    Broadcast a media change to all connected clients via SocketIO.
    Consolidates the duplicated emit pattern used across routes, watchers, and WebSocket handlers.
    """
    socketio.emit('animation_changed', {
        'current_animation': media_file,
        'media_type': media_type,
        'message': f"Media changed to '{media_file}' ({media_type}) via {source}",
        'refresh_page': True
    })
    
    socketio.emit('page_refresh', {
        'reason': 'media_changed',
        'new_media': media_file,
        'media_type': media_type,
        'source': source
    })
    
    logger.info("[%s] Broadcast media change: '%s' (%s)", source.upper(), media_file, media_type)
