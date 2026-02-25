#!/usr/bin/env python3
"""
Local Development Server for Angels-TV-Animator
================================================
A lightweight dev server for frontend work (HTML, CSS, JS, templates).
Provides hot reload without rebuilding Docker.

NOTE: This is for FRONTEND DEVELOPMENT ONLY.
OBS integration, scene watchers, file trigger watchers, and the raw
WebSocket server are NOT started here. Use Docker for full-stack testing:
    docker compose up -d --build

Requirements:
    Python 3.11+
    pip install -r requirements.txt

Usage (from project root):
    python z_extras/dev_local.py
"""

# CRITICAL: eventlet monkey patching must happen before any other imports
# (matches production app.py behavior)
import eventlet
eventlet.monkey_patch()

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — make project root importable and set working directory
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Environment
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'

# ---------------------------------------------------------------------------
# Application bootstrap (mirrors the import block in app.py)
# ---------------------------------------------------------------------------
from extensions import app, socketio          # noqa: E402
import auth_manager                           # noqa: E402, F401 — registers user_loader
import websocket_handlers                     # noqa: E402, F401 — registers SocketIO events
from media_manager import ensure_state_file   # noqa: E402
from config import (                          # noqa: E402
    ANIMATIONS_DIR, VIDEOS_DIR, DATA_DIR, CONFIG_DIR, LOGS_DIR, THUMBNAILS_DIR
)
from routes import register_routes            # noqa: E402

register_routes(app)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Create required directories (same as production startup)
    for d in (ANIMATIONS_DIR, VIDEOS_DIR, DATA_DIR, LOGS_DIR, THUMBNAILS_DIR, CONFIG_DIR):
        d.mkdir(exist_ok=True)
    ensure_state_file()

    print("=" * 64)
    print("  Angels-TV-Animator  —  LOCAL Development Server")
    print("=" * 64)
    print()
    print("  Mode:  Frontend only (no OBS, watchers, or raw WebSocket)")
    print("         Use Docker for full-stack testing.")
    print()
    print("  URLs:")
    print("    TV Display:   http://localhost:5000")
    print("    Admin Panel:  http://localhost:5000/admin")
    print("    Health Check: http://localhost:5000/health")
    print()
    print("  Hot reload is active — edit templates, CSS, or JS and")
    print("  refresh the browser to see changes instantly.")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 64)

    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True,
        )
    except KeyboardInterrupt:
        print("\nDevelopment server stopped.")
    except Exception as e:
        print(f"\nError starting development server: {e}")
        sys.exit(1)