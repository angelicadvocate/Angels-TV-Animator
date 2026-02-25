"""
Angels-TV-Animator: Configuration constants and paths.
Centralized configuration module - no Flask/SocketIO dependencies.
"""

import os
import logging
import logging.handlers
from pathlib import Path

# Version
__version__ = "0.9.5"

# Port configuration
MAIN_PORT = int(os.environ.get('PORT', 8080))
WEBSOCKET_PORT = MAIN_PORT + 1  # Raw WebSocket port is always main port + 1

def get_current_port():
    """Get the current server port based on environment (development vs production)"""
    if os.environ.get('FLASK_ENV') == 'development':
        return 5000
    return MAIN_PORT

# Directory paths
BASE_DIR = Path(__file__).parent
ANIMATIONS_DIR = BASE_DIR / "animations"
VIDEOS_DIR = BASE_DIR / "videos"
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
LOGS_DIR = DATA_DIR / "logs"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
STATE_FILE = DATA_DIR / "state.json"
USERS_FILE = CONFIG_DIR / "users.json"

# Upload limits
MAX_UPLOAD_SIZE_MB = 500  # Maximum file upload size in megabytes

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_FILE = LOGS_DIR / "ata.log"
LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
LOG_BACKUP_COUNT = 3               # Keep 3 rotated backups


def setup_logging():
    """Configure the root logger with console + rotating file handlers.

    Call once at application startup (in app.py) AFTER directories are created.
    Individual modules should use ``logging.getLogger(__name__)``.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Avoid adding duplicate handlers on reload
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (so `docker logs` still works)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotating file handler
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except Exception:
        # If file logging fails (permissions, etc.), continue with console only
        root.warning("Could not create log file at %s — using console only", LOG_FILE)

    # Quieten noisy third-party loggers
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


# Supported file extensions
HTML_EXTENSIONS = {'.html', '.htm'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv'}
