"""
Angels-TV-Animator: Raw WebSocket server for StreamerBot legacy integration.
Runs an asyncio-based websockets server in a separate thread.
"""

import json
import logging
import asyncio
import threading
import websockets

from config import __version__, WEBSOCKET_PORT
from extensions import socketio
from media_manager import (
    find_media_file, load_state, save_state,
    is_video_file, get_all_media_files
)
from device_tracking import connected_devices

logger = logging.getLogger(__name__)


class RawWebSocketServer:
    """Raw WebSocket server for StreamerBot compatibility."""

    def __init__(self, port=None):
        self.port = port or WEBSOCKET_PORT
        self.clients = set()
        self.server = None

    async def handle_client(self, websocket, path):
        """Handle incoming raw WebSocket connections from StreamerBot"""
        logger.info("Raw WebSocket client connected from %s", websocket.remote_address)
        self.clients.add(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug("Raw WebSocket message received: %s", data)

                    if data.get('action') == 'trigger_animation':
                        animation = data.get('animation')
                        instant = data.get('instant', True)
                        force_refresh = data.get('force_refresh', True)
                        source_name = data.get('source', 'streamerbot_websocket')

                        if animation:
                            media_path, media_type = find_media_file(animation)
                            if not media_path:
                                available_media = get_all_media_files()
                                error_response = {
                                    'status': 'error',
                                    'message': f'Animation file not found: {animation}',
                                    'available_media': available_media
                                }
                                await websocket.send(json.dumps(error_response))
                                continue

                            state = load_state()
                            old_animation = state.get('current_animation')
                            state['current_animation'] = animation
                            save_state(state)

                            media_type = "video" if is_video_file(animation) else "animation"

                            socketio.emit('animation_changed', {
                                'previous_animation': old_animation,
                                'current_animation': animation,
                                'media_type': media_type,
                                'message': f"Media changed to '{animation}' ({media_type}) via StreamerBot WebSocket",
                                'refresh_page': force_refresh,
                                'instant': instant,
                                'source': source_name
                            })

                            if force_refresh:
                                socketio.emit('page_refresh', {
                                    'animation': animation,
                                    'instant': instant,
                                    'source': source_name
                                })

                            response = {
                                'status': 'success',
                                'message': f'Animation changed to {animation}',
                                'animation': animation,
                                'instant': instant,
                                'force_refresh': force_refresh,
                                'media_type': media_type
                            }
                            await websocket.send(json.dumps(response))
                            logger.info("StreamerBot: Animation changed to %s", animation)
                        else:
                            error_response = {
                                'status': 'error',
                                'message': 'Missing animation parameter'
                            }
                            await websocket.send(json.dumps(error_response))

                    elif data.get('action') == 'get_status':
                        state = load_state()
                        status_response = {
                            'status': 'success',
                            'current_animation': state.get('current_animation'),
                            'connected_devices': len(connected_devices),
                            'server_version': __version__
                        }
                        await websocket.send(json.dumps(status_response))

                    else:
                        error_response = {
                            'status': 'error',
                            'message': f'Unknown action type: {data.get("action")}'
                        }
                        await websocket.send(json.dumps(error_response))

                except json.JSONDecodeError:
                    error_response = {
                        'status': 'error',
                        'message': 'Invalid JSON format'
                    }
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    error_response = {
                        'status': 'error',
                        'message': f'Server error: {str(e)}'
                    }
                    await websocket.send(json.dumps(error_response))
                    logger.error("Raw WebSocket error: %s", e)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Raw WebSocket client disconnected: %s", websocket.remote_address)
        except Exception as e:
            logger.error("Raw WebSocket handler error: %s", e)
        finally:
            self.clients.discard(websocket)

    def start_server(self):
        """Start the raw WebSocket server in a separate thread"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                start_server = websockets.serve(
                    self.handle_client,
                    "0.0.0.0",
                    self.port,
                    ping_interval=20,
                    ping_timeout=10
                )

                logger.info("Raw WebSocket server starting on port %d for StreamerBot...", self.port)
                loop.run_until_complete(start_server)
                loop.run_forever()
            except Exception as e:
                logger.error("Raw WebSocket server error: %s", e)

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread
