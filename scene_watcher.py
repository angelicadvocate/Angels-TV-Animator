"""
Angels-TV-Animator: File watcher modules.
TriggerFileWatcher — watches for StreamerBot file triggers.
OBSSceneWatcher    — watches obs_current_scene.json and triggers animations via scene mappings.
"""

import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from threading import Thread

from config import DATA_DIR
from extensions import socketio
from media_manager import find_media_file, load_state, save_state

logger = logging.getLogger(__name__)


class TriggerFileWatcher:
    """Watch for file-based triggers from StreamerBot"""

    def __init__(self, trigger_file_path):
        self.trigger_file_path = trigger_file_path
        self.last_modified = 0
        self.running = True

    def start_watching(self):
        """Start watching the trigger file in a background thread"""
        thread = Thread(target=self._watch_file, daemon=True)
        thread.start()
        logger.info("Started watching trigger file: %s", self.trigger_file_path)

    def _watch_file(self):
        """Watch for changes to the trigger file"""
        while self.running:
            try:
                if os.path.exists(self.trigger_file_path):
                    current_modified = os.path.getmtime(self.trigger_file_path)

                    if current_modified > self.last_modified:
                        self.last_modified = current_modified

                        with open(self.trigger_file_path, 'r') as f:
                            animation_name = f.read().strip()

                        if animation_name:
                            logger.info("File trigger received: %s", animation_name)
                            self._handle_trigger(animation_name)

                        os.remove(self.trigger_file_path)

            except Exception as e:
                logger.error("Error watching trigger file: %s", e)

            time.sleep(0.1)

    def _handle_trigger(self, animation_name):
        """Handle the animation trigger"""
        try:
            media_path, media_type = find_media_file(animation_name)
            if not media_path:
                logger.warning("Media file '%s' not found", animation_name)
                return

            state = load_state()
            state['current_animation'] = animation_name
            save_state(state)

            socketio.emit('animation_changed', {
                'current_animation': animation_name,
                'media_type': media_type,
                'message': f"Media changed to '{animation_name}' ({media_type}) via file trigger",
                'refresh_page': True
            })

            socketio.emit('page_refresh', {
                'reason': 'file_trigger',
                'new_media': animation_name,
                'media_type': media_type
            })

            logger.info("Successfully triggered animation: %s (%s)", animation_name, media_type)

        except Exception as e:
            logger.error("Error handling trigger: %s", e)

    def stop_watching(self):
        """Stop watching the trigger file"""
        self.running = False


class OBSSceneWatcher:
    """File watcher that monitors obs_current_scene.json and triggers animations based on mappings"""

    def __init__(self, scene_file_path, mappings_file_path):
        self.scene_file_path = Path(scene_file_path)
        self.mappings_file_path = Path(mappings_file_path)
        self.running = False
        self.watch_thread = None
        self.last_scene = None
        self.last_modified = 0

        logger.info("OBS Scene Watcher initialized:")
        logger.info("   Scene file: %s", self.scene_file_path)
        logger.info("   Mappings file: %s", self.mappings_file_path)

    def start_watching(self):
        """Start watching the OBS scene file for changes"""
        if self.running:
            logger.warning("OBS Scene Watcher is already running")
            return

        self.running = True
        self.watch_thread = Thread(target=self._watch_scene_file, daemon=True)
        self.watch_thread.start()
        logger.info("OBS Scene Watcher started successfully")

    def _watch_scene_file(self):
        """Watch the scene file for changes and trigger animations"""
        logger.debug("OBS Scene Watcher monitoring started...")

        while self.running:
            try:
                if self.scene_file_path.exists():
                    current_modified = self.scene_file_path.stat().st_mtime

                    if current_modified > self.last_modified:
                        self.last_modified = current_modified
                        logger.debug("[%s] Scene file change detected", datetime.now().strftime('%H:%M:%S.%f')[:-3])

                        try:
                            with open(self.scene_file_path, 'r', encoding='utf-8') as f:
                                scene_data = json.load(f)
                                current_scene = scene_data.get('current_scene')

                            if current_scene and current_scene != self.last_scene:
                                logger.info("Scene change detected: '%s' → '%s'", self.last_scene, current_scene)
                                self.last_scene = current_scene
                                self._handle_scene_change(current_scene)

                        except (json.JSONDecodeError, KeyError, Exception) as e:
                            logger.error("Error reading scene file: %s", e)

                time.sleep(0.1)

            except Exception as e:
                logger.error("Scene watcher error: %s", e)
                time.sleep(1)

    def _handle_scene_change(self, scene_name):
        """Handle a scene change by checking mappings and triggering animations"""
        try:
            logger.debug("Processing scene change: '%s'", scene_name)

            mappings = self._load_scene_mappings()
            if not mappings:
                logger.debug("No scene mappings configured")
                return

            animation_name = None
            for mapping in mappings:
                if mapping.get('sceneName') == scene_name:
                    animation_name = mapping.get('animation')
                    break

            if animation_name:
                logger.info("Found mapping: '%s' → '%s'", scene_name, animation_name)
                self._trigger_animation(animation_name, scene_name)
            else:
                logger.debug("No animation mapping found for scene '%s'", scene_name)

        except Exception as e:
            logger.error("Error handling scene change: %s", e)

    def _load_scene_mappings(self):
        """Load scene mappings from the mappings file"""
        try:
            if self.mappings_file_path.exists():
                with open(self.mappings_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        mappings = data
                    else:
                        mappings = data.get('mappings', [])
                    logger.debug("Loaded %d scene mappings", len(mappings))
                    return mappings
            else:
                logger.debug("Scene mappings file not found")
                return []
        except Exception as e:
            logger.error("Error loading scene mappings: %s", e)
            return []

    def _trigger_animation(self, animation_name, scene_name):
        """Trigger an animation by directly updating state and emitting SocketIO commands"""
        try:
            logger.info("Triggering animation '%s' for scene '%s'", animation_name, scene_name)

            media_path, media_type = find_media_file(animation_name)
            if not media_path:
                logger.warning("Animation file '%s' not found", animation_name)
                return

            state = load_state()
            state['current_animation'] = animation_name
            save_state(state)
            logger.debug("Updated backend state to: %s", animation_name)

            socketio.emit('animation_changed', {
                'current_animation': animation_name,
                'media_type': media_type,
                'message': f"Media changed to '{animation_name}' ({media_type})",
                'refresh_page': True
            })
            logger.debug("[AUTO-TRIGGER] Emitted 'animation_changed' for '%s' with refresh_page=True", animation_name)

            socketio.emit('page_refresh', {
                'reason': 'media_changed',
                'new_media': animation_name,
                'media_type': media_type
            })
            logger.debug("[AUTO-TRIGGER] Emitted 'page_refresh' for '%s'", animation_name)

            logger.info("Successfully auto-triggered animation: %s (%s) for scene: %s", animation_name, media_type, scene_name)

        except Exception as e:
            logger.error("Error triggering animation: %s", e)

    def stop_watching(self):
        """Stop watching the scene file"""
        self.running = False
        if self.watch_thread and self.watch_thread.is_alive():
            logger.info("Stopping OBS Scene Watcher...")
            self.watch_thread.join(timeout=2)
        logger.info("OBS Scene Watcher stopped")
