#!/usr/bin/env python3
"""
Angels-TV-Animator: Main application orchestrator.
A Flask-SocketIO server to display HTML/CSS/JS animations on a Smart TV.
Supports dynamic updates triggered via OBS WebSocket, StreamerBot, or REST API.

This file bootstraps the application by importing all modular components
and running the server.
"""

# CRITICAL: Eventlet monkey patching must happen BEFORE any other imports
# This patches stdlib (socket, threading, time, etc.) for green thread compatibility
import eventlet
eventlet.monkey_patch()

import json
import time
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash

# Core application instances (created in extensions.py)
from extensions import app, socketio, login_manager, get_obs_client, set_obs_client
from config import (
    __version__, MAIN_PORT, WEBSOCKET_PORT,
    ANIMATIONS_DIR, VIDEOS_DIR, DATA_DIR, CONFIG_DIR, LOGS_DIR, THUMBNAILS_DIR,
    USERS_FILE, setup_logging
)

# Import modules so they register their handlers / side effects
import auth_manager          # noqa: F401 — registers @login_manager.user_loader
import websocket_handlers    # noqa: F401 — registers all @socketio.on() handlers
from media_manager import (
    ensure_state_file, get_animation_files, get_video_files
)
from device_tracking import set_raw_websocket_server
from obs_manager import OBSWebSocketClient
from scene_watcher import TriggerFileWatcher, OBSSceneWatcher
from websocket_server import RawWebSocketServer

# Register Flask Blueprints
from routes import register_routes
register_routes(app)

logger = logging.getLogger(__name__)


# =============================================================================
# Raw WebSocket Server (instantiated here, started in __main__)
# =============================================================================

raw_websocket_server = RawWebSocketServer(port=WEBSOCKET_PORT)
set_raw_websocket_server(raw_websocket_server)


# =============================================================================
# Main Application Startup
# =============================================================================

if __name__ == '__main__':
    # Create required directories
    ANIMATIONS_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    THUMBNAILS_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)

    # Initialize logging (must come after LOGS_DIR is created)
    setup_logging()

    # Initialize state file with current scene tracking
    ensure_state_file()

    # Create default admin user if users.json doesn't exist
    if not USERS_FILE.exists():
        logger.info("Creating default admin user configuration...")
        default_users = {
            "admin_users": {
                "admin": {
                    "password": generate_password_hash("admin123"),
                    "created_at": datetime.now().isoformat(),
                    "permissions": ["read", "write", "delete", "upload"],
                    "theme": "dark"
                }
            },
            "session_config": {
                "timeout_minutes": 60,
                "remember_me_days": 7
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, indent=2)
        logger.warning("Default admin credentials: admin / admin123")
        logger.warning("CHANGE THE DEFAULT PASSWORD IMMEDIATELY after first login!")

    # Startup banner
    logger.info("Angels-TV-Animator WebSocket Server Starting...")
    logger.info("=" * 84)
    logger.info("Available animations: %s", get_animation_files())
    logger.info("Available videos: %s", get_video_files())
    logger.info("=" * 84)
    logger.info("HTTP API Routes:")
    logger.info("  GET  /               - Smart TV display (main animation endpoint)")
    logger.info("  GET  /admin          - Admin dashboard and file management")
    logger.info("  POST /trigger        - Update media via API (JSON: {\"animation\": \"file.html|mp4\"})")
    logger.info("  GET  /animations     - List available media files")
    logger.info("  GET  /health         - Health check endpoint")
    logger.info("=" * 84)
    logger.info("WebSocket Integration:")
    logger.info("  Socket.IO (port %d) - Real-time communication", MAIN_PORT)
    logger.info("    Admin dashboard updates")
    logger.info("    Animation page refresh & status")
    logger.info("    ATA Integration (/static/js/ata-integration.js)")
    logger.info("  Raw WebSocket (port %d) - StreamerBot compatibility", WEBSOCKET_PORT)
    logger.info("    Legacy integration support")
    logger.info("=" * 84)
    logger.info("Media Storage:")
    logger.info("  Animations: %s (%d files)", ANIMATIONS_DIR, len(get_animation_files()))
    logger.info("  Videos: %s (%d files)", VIDEOS_DIR, len(get_video_files()))
    logger.info("  Data: %s (users, settings, thumbnails)", DATA_DIR)
    logger.info("=" * 84)
    logger.info("StreamerBot Integration:")
    logger.info("  Use 'StreamerBot C#' buttons in admin file management")
    logger.info("  Copy ready-to-use C# code for each animation")
    logger.info("  HTTP triggers also available for legacy setups")
    logger.info("  Visit /admin/instructions/streamerbot-integration for setup guide")
    logger.info("=" * 84)
    logger.info("Custom Animation Development:")
    logger.info("  Add ATA Integration to your HTML files:")
    logger.info("    <link rel=\"stylesheet\" href=\"/static/css/ata-integration.css\">")
    logger.info("    <script src=\"/static/js/ata-integration.js\"></script>")
    logger.info("  Enables status indicators, WebSocket sync, and page refresh")
    logger.info("  Visit /admin/instructions/getting-started for complete guide")
    logger.info("=" * 84)

    try:
        # Initialize file trigger watcher for StreamerBot
        logger.info("Starting file trigger watcher...")
        trigger_file = DATA_DIR / "trigger.txt"
        file_watcher = TriggerFileWatcher(str(trigger_file))
        file_watcher.start_watching()
        logger.info("File trigger watcher started")

        # Initialize OBS Scene Watcher for automatic animation triggering
        logger.info("Starting OBS Scene Watcher...")
        obs_scene_file = DATA_DIR / "config" / "obs_current_scene.json"
        obs_mappings_file = DATA_DIR / "config" / "obs_mappings.json"
        obs_scene_watcher = OBSSceneWatcher(str(obs_scene_file), str(obs_mappings_file))
        obs_scene_watcher.start_watching()
        logger.info("OBS Scene Watcher started")

        # Start the raw WebSocket server for StreamerBot
        logger.info("Starting Raw WebSocket server on port %d for StreamerBot...", WEBSOCKET_PORT)
        try:
            websocket_thread = raw_websocket_server.start_server()
            logger.info("Raw WebSocket server started successfully")
        except Exception as e:
            logger.error("Error starting Raw WebSocket server: %s", e)
            logger.warning("Continuing without Raw WebSocket server...")

        # Give the WebSocket server a moment to start
        time.sleep(1)
        logger.info("Raw WebSocket server ready!")

        # Initialize OBS WebSocket client (will attempt connection if settings exist)
        logger.info("Initializing OBS WebSocket client...")
        obs_client = OBSWebSocketClient()
        set_obs_client(obs_client)
        logger.info("OBS WebSocket client initialized")

        # Attempt auto-connection if settings exist
        logger.info("Checking for existing OBS settings...")
        if obs_client.load_settings():
            settings_debug = obs_client.settings.copy()
            if 'password' in settings_debug:
                settings_debug['password'] = '[REDACTED]' if settings_debug['password'] else '[EMPTY]'
            logger.info("Found OBS settings: %s", settings_debug)

            logger.info("Forcing persistent OBS connection...")
            try:
                obs_client.auto_reconnect_enabled = True
                obs_client.should_be_connected = True
                logger.debug("Persistent connection flags set: auto_reconnect=True, should_be_connected=True")

                obs_client.enable_persistent_connection()

                if obs_client.connected:
                    logger.info("Successfully connected to OBS - persistent connection active")
                    logger.debug("Connection monitoring active: %s", obs_client.auto_reconnect_enabled)
                else:
                    logger.warning("Initial connection failed but persistent reconnection is active")
                    logger.info("Connection monitor will continuously attempt reconnection...")

            except Exception as e:
                logger.error("OBS connection error during startup: %s", e)
                logger.info("Forcing reconnection monitor anyway...")
                try:
                    obs_client.auto_reconnect_enabled = True
                    obs_client.should_be_connected = True
                    obs_client._start_connection_monitor()
                    logger.info("Forced connection monitor started — will reconnect when OBS available")
                except Exception as monitor_error:
                    logger.critical("Could not start connection monitor: %s", monitor_error)
        else:
            logger.info("No OBS settings found — connection will be available when configured")

        logger.info("Starting production server (eventlet)...")
        socketio.run(app, host='0.0.0.0', port=MAIN_PORT, debug=False)

    except Exception as e:
        logger.critical("FATAL ERROR during startup: %s", e, exc_info=True)
        logger.critical("Server startup failed!")
