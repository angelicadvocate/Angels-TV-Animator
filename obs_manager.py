"""
Angels-TV-Animator: OBS WebSocket client integration module.
Handles OBS Studio connection, scene detection, and event handling.
"""

import json
import logging
import time
from datetime import datetime
from threading import Thread
from obswebsocket import obsws, requests, events

from config import DATA_DIR, get_current_port
from extensions import socketio

logger = logging.getLogger(__name__)


class OBSWebSocketClient:
    """OBS WebSocket client with persistent connection and auto-reconnection."""

    def __init__(self):
        self.client = None
        self.connected = False
        self.settings = {}
        self.scene_mappings = []
        self.connection_thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 20
        self.auto_reconnect_enabled = True
        self.connection_monitor_thread = None
        self.should_be_connected = False

    # =========================================================================
    # Settings I/O
    # =========================================================================

    def load_settings(self):
        """Load OBS connection settings from config file"""
        try:
            obs_config_path = DATA_DIR / 'config' / 'obs_settings.json'
            logger.debug("Looking for settings at: %s", obs_config_path)

            if obs_config_path.exists():
                logger.debug("Settings file found, loading...")
                with open(obs_config_path, 'r') as f:
                    self.settings = json.load(f)

                settings_log = self.settings.copy()
                if 'password' in settings_log and settings_log['password']:
                    settings_log['password'] = '[REDACTED]'
                else:
                    settings_log['password'] = '[EMPTY]'
                logger.debug("Loaded settings: %s", settings_log)
                return True
            else:
                logger.warning("Settings file not found")
                return False
        except Exception as e:
            logger.error("Error loading OBS settings: %s", e, exc_info=True)
            return False

    def load_scene_mappings(self):
        """Load scene to animation mappings from config file"""
        try:
            mappings_path = DATA_DIR / 'config' / 'obs_mappings.json'
            if mappings_path.exists():
                with open(mappings_path, 'r') as f:
                    self.scene_mappings = json.load(f)
                return True
            return False
        except Exception as e:
            logger.error("Error loading OBS scene mappings: %s", e)
            return False

    # =========================================================================
    # Connection Management
    # =========================================================================

    def connect(self):
        """Establish connection to OBS WebSocket server"""
        if not self.load_settings():
            logger.warning("No OBS settings found, skipping connection")
            return False

        if not self.load_scene_mappings():
            logger.warning("No scene mappings found, OBS events will be ignored")
            self.scene_mappings = []

        try:
            logger.info("Attempting to connect to OBS at %s:%s", self.settings.get('host', 'localhost'), self.settings.get('port', 4455))

            self.client = obsws(
                host=self.settings.get('host', 'localhost'),
                port=self.settings.get('port', 4455),
                password=self.settings.get('password', '')
            )

            self.client.connect()

            version_info = self.client.call(requests.GetVersion())
            logger.info("Connected to OBS Studio %s", version_info.getObsVersion())
            logger.info("OBS WebSocket version: %s", version_info.getObsWebSocketVersion())

            self.connected = True
            self.should_be_connected = True
            self.reconnect_attempts = 0

            # Register for scene change events
            try:
                if hasattr(events, 'CurrentProgramSceneChanged'):
                    self.client.register(self._on_scene_changed, events.CurrentProgramSceneChanged)
                    logger.debug("Registered for CurrentProgramSceneChanged events")
                elif hasattr(events, 'SwitchScenes'):
                    self.client.register(self._on_scene_changed, events.SwitchScenes)
                    logger.debug("Registered for SwitchScenes events (fallback)")
                else:
                    logger.warning("No suitable scene change event found")
            except Exception as event_error:
                logger.warning("Error registering for scene events: %s", event_error)
                try:
                    self.client.register(self._on_scene_changed, events.SwitchScenes)
                    logger.debug("Fallback: Registered for SwitchScenes events")
                except Exception as fallback_error:
                    logger.error("Failed to register for any scene events: %s", fallback_error)

            logger.info("OBS event listener setup complete, waiting for scene changes...")
            self._start_connection_monitor()
            return True

        except Exception as e:
            logger.error("Failed to connect to OBS: %s", e)
            self.connected = False
            self._schedule_reconnect()
            return False

    def disconnect(self, permanent=False, force=False):
        """Disconnect from OBS WebSocket server

        Args:
            permanent: If True, disables auto-reconnection.
            force: If True, bypasses settings check for permanent disconnection.
        """
        self.connected = False

        if permanent and not force:
            try:
                obs_config_path = DATA_DIR / 'config' / 'obs_settings.json'
                if obs_config_path.exists():
                    with open(obs_config_path, 'r') as f:
                        settings = json.load(f)
                    if settings.get('enabled', True):
                        logger.warning("REFUSING permanent disconnect - OBS is enabled in settings!")
                        logger.info("Keeping auto-reconnection active per user settings")
                        return
            except Exception as settings_error:
                logger.warning("Could not check settings for disconnect: %s", settings_error)
                logger.warning("Refusing permanent disconnect due to settings check failure")
                return

            self.should_be_connected = False
            self.auto_reconnect_enabled = False
            logger.info("Permanently disconnecting from OBS WebSocket server")
        else:
            logger.info("Temporarily disconnecting from OBS WebSocket server")

        if self.client:
            try:
                self.client.disconnect()
                logger.info("Disconnected from OBS WebSocket server")
            except Exception as e:
                logger.warning("Error during OBS disconnect: %s", e)
            finally:
                self.client = None

    def test_connection(self):
        """Test OBS WebSocket connection without establishing persistent connection"""
        logger.debug("test_connection() called")

        if not self.load_settings():
            logger.warning("No settings found")
            return False, "No OBS settings configured"

        connection_info = {
            'host': self.settings.get('host', 'localhost'),
            'port': self.settings.get('port', 4455),
            'password_set': bool(self.settings.get('password', ''))
        }
        logger.debug("Attempting connection to: %s", connection_info)

        try:
            start_time = time.time()

            logger.debug("Creating obsws client...")
            test_client = obsws(
                host=self.settings.get('host', 'localhost'),
                port=self.settings.get('port', 4455),
                password=self.settings.get('password', '')
            )
            logger.debug("obsws client created successfully")

            logger.debug("Calling connect()...")
            test_client.connect()
            connect_time = time.time() - start_time
            logger.debug("Connected successfully in %.2fs", connect_time)

            logger.debug("Calling GetVersion()...")
            version_start = time.time()
            version_info = test_client.call(requests.GetVersion())
            version_time = time.time() - version_start
            logger.debug("GetVersion completed in %.2fs", version_time)

            logger.debug("Disconnecting...")
            test_client.disconnect()

            total_time = time.time() - start_time
            obs_version = version_info.getObsVersion()
            success_msg = f"Connected to OBS Studio {obs_version} (total: {total_time:.2f}s)"
            logger.info("%s", success_msg)

            return True, success_msg

        except Exception as e:
            total_time = time.time() - start_time if 'start_time' in locals() else 0
            error_msg = f"Connection failed: {str(e)}"
            logger.error("%s (after %.2fs)", error_msg, total_time)

            if "10060" in str(e):
                logger.debug("Error 10060 = Connection timeout (target not responding)")
            elif "10061" in str(e):
                logger.debug("Error 10061 = Connection actively refused")

            return False, error_msg

    def enable_persistent_connection(self):
        """Enable persistent auto-reconnection to OBS"""
        logger.info("Enabling persistent OBS connection...")
        self.auto_reconnect_enabled = True
        self.should_be_connected = True

        if not self.connected:
            if not self.settings:
                if not self.load_settings():
                    logger.error("No OBS settings available for persistent connection")
                    return False

            logger.info("Attempting OBS connection for persistent mode...")
            success = self.connect()
            if not success:
                logger.warning("Initial connection failed, but will keep trying...")

        self._start_connection_monitor()
        return self.connected

    # =========================================================================
    # Scene Data
    # =========================================================================

    def get_current_scene(self):
        """Get the current active scene from OBS"""
        if not self.connected or not self.client:
            return None

        try:
            current_scene = self.client.call(requests.GetCurrentProgramScene())
            logger.debug("GetCurrentProgramScene response: %s", current_scene)

            # Use datain dict directly — hasattr / getattr can raise KeyError
            # in obs-websocket-py instead of AttributeError, bypassing hasattr.
            data = getattr(current_scene, 'datain', None) or {}
            scene_name = (
                data.get('currentProgramSceneName')
                or data.get('sceneName')
                or data.get('name')
            )
            if scene_name:
                return scene_name

            # Fallback: try legacy accessor
            try:
                return current_scene.getName()
            except Exception:
                pass

            logger.warning("Unexpected current scene response format: %s, datain=%s", type(current_scene), data)
            return None

        except Exception as e:
            logger.error("GetCurrentProgramScene failed: %s", e)
            try:
                current_scene = self.client.call(requests.GetCurrentScene())
                data = getattr(current_scene, 'datain', None) or {}
                scene_name = (
                    data.get('currentProgramSceneName')
                    or data.get('sceneName')
                    or data.get('name')
                )
                if scene_name:
                    return scene_name
                try:
                    return current_scene.getName()
                except Exception:
                    pass
                return None
            except Exception as fallback_error:
                logger.error("Error getting current OBS scene (both methods failed): %s", fallback_error)
                return None

    def get_scene_list(self):
        """Get list of all scenes from OBS"""
        if not self.connected or not self.client:
            return []

        try:
            scene_list = self.client.call(requests.GetSceneList())
            return [scene['sceneName'] for scene in scene_list.getScenes()]
        except Exception as e:
            logger.error("Error getting OBS scene list: %s", e)
            return []

    def _save_current_scene_to_storage(self, scene_name):
        """Save current scene to persistent storage file"""
        if not scene_name or not isinstance(scene_name, str):
            raise ValueError(f"Invalid scene name for storage: {scene_name}")

        scene_name = str(scene_name).strip()
        if not scene_name:
            raise ValueError("Scene name is empty after cleaning")

        try:
            current_scene_path = DATA_DIR / 'config' / 'obs_current_scene.json'

            scene_data = {
                'current_scene': None,
                'last_updated': None
            }

            if current_scene_path.exists():
                try:
                    with open(current_scene_path, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict):
                            scene_data['current_scene'] = loaded_data.get('current_scene')
                            scene_data['last_updated'] = loaded_data.get('last_updated')
                except (json.JSONDecodeError, UnicodeDecodeError) as parse_error:
                    logger.warning("Could not parse existing storage file: %s", parse_error)
                except Exception as file_error:
                    logger.warning("Could not read existing storage file: %s", file_error)

            scene_data['current_scene'] = scene_name
            scene_data['last_updated'] = datetime.now().isoformat()

            config_dir = DATA_DIR / 'config'
            config_dir.mkdir(parents=True, exist_ok=True)

            # Atomic write
            temp_path = current_scene_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(scene_data, f, indent=2, ensure_ascii=False)
            temp_path.replace(current_scene_path)

        except Exception as e:
            logger.critical("Storage save operation failed: %s", e)
            raise

    # =========================================================================
    # Internal: Event Handling & Reconnection
    # =========================================================================

    def _on_scene_changed(self, message):
        """Handle OBS scene change events"""
        scene_name = None
        event_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        try:
            logger.info("[%s] Scene change event received, type: %s", event_time, type(message))

            try:
                if hasattr(message, 'sceneName') and message.sceneName:
                    scene_name = str(message.sceneName)
                elif hasattr(message, 'getSceneName') and callable(message.getSceneName):
                    scene_name = str(message.getSceneName())
                elif hasattr(message, 'datain') and isinstance(message.datain, dict) and 'sceneName' in message.datain:
                    scene_name = str(message.datain['sceneName'])
                else:
                    logger.warning("Could not extract scene name. Message attributes: %s", dir(message))
                    return
            except Exception as extract_error:
                logger.error("Scene name extraction failed: %s", extract_error)
                return

            if not scene_name or not isinstance(scene_name, str) or len(scene_name.strip()) == 0:
                logger.warning("Invalid scene name extracted: '%s'", scene_name)
                return

            scene_name = scene_name.strip()
            logger.info("[%s] OBS Scene change detected: '%s'", event_time, scene_name)

        except Exception as initial_error:
            logger.error("Initial scene change processing failed: %s", initial_error)
            return

        # 1. Save scene data via HTTP API (for file-based watcher)
        try:
            import requests as http_requests
            current_port = get_current_port()
            response = http_requests.post(
                f'http://localhost:{current_port}/api/obs/current-scene',
                json={'current_scene': scene_name},
                headers={'Content-Type': 'application/json'},
                timeout=1
            )
            storage_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if response.status_code == 200:
                logger.debug("[%s] Scene data saved: %s", storage_time, scene_name)
            else:
                logger.warning("Scene data save failed (status %d): %s", response.status_code, response.text)
        except Exception as api_error:
            logger.warning("Scene data save failed (non-critical): %s", api_error)

        # 2. Emit to frontend
        try:
            emit_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            socketio.emit('scene_changed', {
                'scene_name': scene_name,
                'timestamp': time.time(),
                'event_time': emit_time
            })
            logger.debug("[%s] Socket.IO emission to frontend: %s", emit_time, scene_name)
        except Exception as emit_error:
            logger.warning("Socket.IO emission failed (non-critical): %s", emit_error)

        logger.info("[%s] Scene change processing completed", datetime.now().strftime('%H:%M:%S.%f')[:-3])

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(30, 2 ** self.reconnect_attempts)
            logger.info("Scheduling OBS reconnection attempt %d/%d in %d seconds", self.reconnect_attempts, self.max_reconnect_attempts, delay)

            def reconnect_after_delay():
                time.sleep(delay)
                if not self.connected:
                    logger.info("Attempting OBS reconnection (%d/%d)", self.reconnect_attempts, self.max_reconnect_attempts)
                    self.connect()

            Thread(target=reconnect_after_delay, daemon=True).start()
        else:
            logger.warning("Max OBS reconnection attempts (%d) reached. Will retry later...", self.max_reconnect_attempts)

            def reset_attempts_later():
                time.sleep(300)
                self.reconnect_attempts = 0
                if self.should_be_connected and not self.connected:
                    logger.info("Retrying OBS connection after cooldown period...")
                    self._schedule_reconnect()

            Thread(target=reset_attempts_later, daemon=True).start()

    def _start_connection_monitor(self):
        """Start a background thread to monitor and maintain OBS connection"""
        if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            return

        def connection_monitor():
            logger.info("Starting OBS connection monitor with persistent reconnection...")
            monitor_loop_count = 0
            while self.auto_reconnect_enabled:
                try:
                    time.sleep(10)
                    monitor_loop_count += 1

                    if monitor_loop_count % 6 == 0:
                        logger.debug("Connection monitor status: should_connect=%s, connected=%s, auto_reconnect=%s", self.should_be_connected, self.connected, self.auto_reconnect_enabled)

                    if self.should_be_connected and not self.connected:
                        logger.info("Connection monitor: OBS disconnected — forcing reconnect...")
                        success = self.connect()
                        if success:
                            logger.info("Connection monitor: Reconnection successful")
                        else:
                            logger.warning("Connection monitor: Reconnection failed, will retry in 10 seconds")
                    elif self.connected and self.client:
                        try:
                            self.client.call(requests.GetVersion())
                        except Exception as e:
                            logger.warning("Connection monitor: OBS connection test failed: %s", e)
                            self.connected = False
                            if self.should_be_connected:
                                success = self.connect()
                                if success:
                                    logger.info("Connection monitor: Reconnection after test failure successful")
                                else:
                                    logger.warning("Connection monitor: Reconnection after test failure failed")

                except Exception as e:
                    logger.error("Connection monitor error: %s", e)
                    logger.info("Connection monitor continuing despite error...")
                    time.sleep(30)

        self.connection_monitor_thread = Thread(target=connection_monitor, daemon=True)
        self.connection_monitor_thread.start()
