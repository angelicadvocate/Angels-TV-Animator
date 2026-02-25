"""
Angels-TV-Animator: OBS API route blueprint.
Handles OBS WebSocket settings, connection management, scene data, and mappings.
"""

import json
import logging
import time
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify

from config import DATA_DIR
from auth_manager import admin_required
from obs_manager import OBSWebSocketClient
from extensions import get_obs_client as _get_obs_client, set_obs_client as _set_obs_client

obs_api_bp = Blueprint('obs_api', __name__)
logger = logging.getLogger(__name__)


# =============================================================================
# OBS Settings
# =============================================================================

@obs_api_bp.route('/api/obs/settings', methods=['GET'])
@admin_required
def api_obs_settings_get():
    """Get OBS connection settings"""
    try:
        obs_config_path = DATA_DIR / 'config' / 'obs_settings.json'

        if obs_config_path.exists():
            with open(obs_config_path, 'r') as f:
                settings = json.load(f)
        else:
            settings = {
                'host': 'localhost',
                'port': 4455,
                'password': '',
                'enabled': True
            }

        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/settings', methods=['POST'])
@admin_required
def api_obs_settings_post():
    """Save OBS connection settings"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        settings = {
            'host': data.get('host', 'localhost'),
            'port': int(data.get('port', 4455)),
            'password': data.get('password', ''),
            'enabled': data.get('enabled', True)
        }

        config_dir = DATA_DIR / 'config'
        config_dir.mkdir(exist_ok=True)

        obs_config_path = config_dir / 'obs_settings.json'
        with open(obs_config_path, 'w') as f:
            json.dump(settings, f, indent=2)

        obs_client = _get_obs_client()
        needs_restart = False

        if obs_client and obs_client.settings:
            old_settings = obs_client.settings
            if (old_settings.get('host') != settings['host'] or
                old_settings.get('port') != settings['port'] or
                old_settings.get('password') != settings['password']):
                needs_restart = True
                logger.info("Connection settings changed, restart required")
        else:
            needs_restart = True
            logger.info("No existing client or settings, initial connection required")

        if needs_restart:
            logger.info("Restarting OBS client with new settings...")

            if obs_client:
                try:
                    obs_client.disconnect(permanent=True, force=True)
                except:
                    pass

            obs_client = OBSWebSocketClient()
            _set_obs_client(obs_client)

        if settings.get('enabled', True):
            logger.info("OBS connection enabled, ensuring persistent connection...")
            obs_client = _get_obs_client()
            if obs_client:
                obs_client.enable_persistent_connection()
                connected = obs_client.connected
                logger.info("Connection result: %s", connected)
            else:
                connected = False
        else:
            logger.info("OBS connection disabled in settings")
            obs_client = _get_obs_client()
            if obs_client:
                obs_client.disconnect(permanent=True, force=True)
            connected = False

        return jsonify({'success': True, 'auto_connected': connected, 'enabled': settings.get('enabled', True)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# OBS Mappings
# =============================================================================

@obs_api_bp.route('/api/obs/mappings', methods=['GET'])
@admin_required
def api_obs_mappings_get():
    """Get scene to animation mappings"""
    try:
        mappings_path = DATA_DIR / 'config' / 'obs_mappings.json'

        if mappings_path.exists():
            with open(mappings_path, 'r') as f:
                content = f.read().strip()
                if content:
                    try:
                        mappings = json.loads(content)
                        if not isinstance(mappings, list):
                            mappings = []
                    except json.JSONDecodeError:
                        mappings = []
                else:
                    mappings = []
        else:
            mappings = []

        return jsonify({'success': True, 'mappings': mappings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/mappings', methods=['POST'])
@admin_required
def api_obs_mappings_post():
    """Save scene to animation mappings"""
    try:
        data = request.get_json()

        if not data or 'mappings' not in data:
            return jsonify({'success': False, 'error': 'No mappings data provided'}), 400

        mappings = data['mappings']

        for mapping in mappings:
            if not isinstance(mapping, dict) or 'sceneName' not in mapping or 'animation' not in mapping:
                return jsonify({'success': False, 'error': 'Invalid mapping structure'}), 400

        config_dir = DATA_DIR / 'config'
        config_dir.mkdir(exist_ok=True)

        mappings_path = config_dir / 'obs_mappings.json'
        with open(mappings_path, 'w') as f:
            json.dump(mappings, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# OBS Connection Management
# =============================================================================

@obs_api_bp.route('/api/obs/test-connection', methods=['POST'])
@admin_required
def api_obs_test_connection():
    """Test OBS WebSocket connection"""
    logger.info("=== OBS Connection Test Started ===")
    start_time = time.time()

    try:
        logger.debug("Creating temporary OBS client for testing...")
        test_client = OBSWebSocketClient()

        if test_client.load_settings():
            settings_log = test_client.settings.copy()
            if 'password' in settings_log and settings_log['password']:
                settings_log['password'] = '[REDACTED]'
            else:
                settings_log['password'] = '[EMPTY]'
            logger.debug("Loaded settings: %s", settings_log)
        else:
            logger.warning("No OBS settings found!")
            return jsonify({'success': False, 'error': 'No OBS settings configured'})

        logger.debug("Calling test_connection()...")
        success, message = test_client.test_connection()

        duration = time.time() - start_time
        logger.debug("Test completed in %.2f seconds", duration)

        if success:
            logger.info("Connection successful: %s", message)
            return jsonify({'success': True, 'message': message})
        else:
            logger.warning("Connection failed: %s", message)
            return jsonify({'success': False, 'error': message})

    except Exception as e:
        duration = time.time() - start_time
        logger.error("Exception during test after %.2f seconds: %s", duration, e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        logger.info("=== OBS Connection Test Complete ===")


@obs_api_bp.route('/api/obs/connect', methods=['POST'])
@admin_required
def api_obs_connect():
    """Start persistent OBS WebSocket connection"""
    try:
        obs_client = _get_obs_client()

        if obs_client and obs_client.connected:
            obs_client.enable_persistent_connection()
            return jsonify({'success': True, 'message': 'Already connected to OBS (persistent connection enabled)'})

        if not obs_client:
            obs_client = OBSWebSocketClient()
            _set_obs_client(obs_client)

        obs_client.enable_persistent_connection()

        if obs_client.connected:
            return jsonify({'success': True, 'message': 'Connected to OBS WebSocket server with persistent connection'})
        else:
            return jsonify({'success': False, 'error': 'Failed to connect to OBS WebSocket server'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/disconnect', methods=['POST'])
@admin_required
def api_obs_disconnect():
    """Permanently stop OBS WebSocket connection"""
    try:
        obs_client = _get_obs_client()
        if obs_client:
            obs_client.disconnect(permanent=True)
            _set_obs_client(None)

        return jsonify({'success': True, 'message': 'Permanently disconnected from OBS WebSocket server'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/status', methods=['GET'])
@admin_required
def api_obs_status():
    """Get OBS WebSocket connection status"""
    try:
        obs_client = _get_obs_client()
        logger.debug("OBS Status Check - obs_client exists: %s", obs_client is not None)

        obs_config_path = DATA_DIR / 'config' / 'obs_settings.json'
        obs_enabled = True

        if obs_config_path.exists():
            try:
                with open(obs_config_path, 'r') as f:
                    settings = json.load(f)
                    obs_enabled = settings.get('enabled', True)
                    logger.debug("OBS Connection enabled in settings: %s", obs_enabled)
            except Exception as e:
                logger.warning("Error reading settings: %s", e)

        if not obs_enabled:
            logger.debug("OBS Connection is disabled by user")
            return jsonify({
                'success': True,
                'connected': False,
                'current_scene': None,
                'scene_list': [],
                'disabled': True
            })

        if obs_client is None:
            logger.info("obs_client is None, attempting to initialize...")
            try:
                obs_client = OBSWebSocketClient()
                _set_obs_client(obs_client)
                logger.debug("OBS client created successfully")

                if obs_client.load_settings():
                    logger.debug("Settings loaded, enabling persistent connection...")
                    obs_client.enable_persistent_connection()
                    logger.debug("Persistent connection enabled. Connected: %s", obs_client.connected)
                else:
                    logger.warning("No OBS settings found")
            except Exception as init_error:
                logger.error("Failed to initialize obs_client: %s", init_error)
                _set_obs_client(None)
                obs_client = None
        elif obs_client and not obs_client.should_be_connected and obs_enabled:
            logger.debug("Re-enabling persistent connection for existing client...")
            obs_client.enable_persistent_connection()

        if obs_client:
            logger.debug("OBS Status - connected: %s, should_be_connected: %s", obs_client.connected, obs_client.should_be_connected)

        if obs_client and obs_client.connected:
            try:
                logger.debug("Testing connection health by requesting scene data...")
                current_scene = obs_client.get_current_scene()
                scene_list = obs_client.get_scene_list()

                logger.debug("Connection test successful - Current scene: %s, Scene count: %d", current_scene, len(scene_list) if scene_list else 0)

                if current_scene:
                    try:
                        obs_client._save_current_scene_to_storage(current_scene)
                        logger.debug("Updated persistent storage with current scene: %s", current_scene)
                    except Exception as storage_error:
                        logger.warning("Failed to update storage in status check: %s", storage_error)

                return jsonify({
                    'success': True,
                    'connected': True,
                    'current_scene': current_scene,
                    'scene_list': scene_list
                })
            except Exception as e:
                logger.warning("OBS Status - Connection test failed: %s", e)
                obs_client.connected = False

                error_str = str(e)
                if "10060" in error_str or "timeout" in error_str.lower() or "connection" in error_str.lower():
                    error_message = "Connection failed: Please verify your connection details"
                else:
                    error_message = f"Connection error: {str(e)}"

                return jsonify({
                    'success': True,
                    'connected': False,
                    'current_scene': None,
                    'scene_list': [],
                    'error': error_message
                })
        else:
            return jsonify({
                'success': True,
                'connected': False,
                'current_scene': None,
                'scene_list': []
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/scenes', methods=['GET'])
@admin_required
def api_obs_scenes():
    """Get list of all OBS scenes - TRANSIENT DATA for UI only"""
    try:
        obs_client = _get_obs_client()

        if obs_client and obs_client.connected:
            scene_list = obs_client.get_scene_list()
            logger.debug("Fetched scene list for UI: %d scenes", len(scene_list) if scene_list else 0)
            return jsonify({'success': True, 'scenes': scene_list})
        else:
            return jsonify({'success': False, 'error': 'Not connected to OBS'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# Current Scene Persistent Storage
# =============================================================================

@obs_api_bp.route('/api/obs/current-scene', methods=['GET'])
@admin_required
def api_obs_current_scene_get():
    """Get current scene data from persistent storage"""
    try:
        current_scene_path = DATA_DIR / 'config' / 'obs_current_scene.json'

        if current_scene_path.exists():
            with open(current_scene_path, 'r') as f:
                scene_data = json.load(f)
        else:
            scene_data = {
                'current_scene': None,
                'last_updated': None,
                'scene_list': []
            }

        return jsonify({'success': True, 'scene_data': scene_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/current-scene', methods=['POST'])
@admin_required
def api_obs_current_scene_post():
    """Update current scene data in persistent storage"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        current_scene_path = DATA_DIR / 'config' / 'obs_current_scene.json'
        if current_scene_path.exists():
            with open(current_scene_path, 'r') as f:
                loaded_data = json.load(f)
                scene_data = {
                    'current_scene': loaded_data.get('current_scene'),
                    'last_updated': loaded_data.get('last_updated')
                }
        else:
            scene_data = {
                'current_scene': None,
                'last_updated': None
            }

        if 'current_scene' in data:
            scene_data['current_scene'] = data['current_scene']
            scene_data['last_updated'] = datetime.now().isoformat()

        config_dir = DATA_DIR / 'config'
        config_dir.mkdir(exist_ok=True)

        with open(current_scene_path, 'w') as f:
            json.dump(scene_data, f, indent=2)

        return jsonify({'success': True, 'scene_data': scene_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@obs_api_bp.route('/api/obs/current-scene', methods=['DELETE'])
@admin_required
def api_obs_current_scene_delete():
    """Clear/reset current scene data in persistent storage"""
    try:
        current_scene_path = DATA_DIR / 'config' / 'obs_current_scene.json'

        if current_scene_path.exists():
            current_scene_path.unlink()
            logger.info("Cleared persistent scene data file")

        return jsonify({
            'success': True,
            'message': 'Scene data cleared successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
