"""
Angels-TV-Animator: Flask extension instances.
Created here to avoid circular imports - all modules import from this file.
"""

from datetime import timedelta
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager

import config
from config import __version__

# Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'angels-tv-animator-secret-key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Upload size limit

# Socket.IO with eventlet async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin.admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'


# =============================================================================
# OBS Client Service Holder
# =============================================================================
# The OBS client is created/destroyed at runtime by multiple routes.
# Stored here so blueprints can access it without importing app.py
# (which would cause a double-import when app.py runs as __main__).

_obs_client = None


def get_obs_client():
    """Get the current OBS WebSocket client instance."""
    return _obs_client


def set_obs_client(client):
    """Set the OBS WebSocket client instance."""
    global _obs_client
    _obs_client = client
