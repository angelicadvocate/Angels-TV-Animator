"""
Angels-TV-Animator: Connected device tracking module.
Manages Socket.IO client tracking and device info aggregation.
"""

import logging
import time

logger = logging.getLogger(__name__)


# Shared mutable state for connected devices
connected_devices = {}  # {session_id: {'type': 'tv'|'admin', 'user_agent': str, 'connected_at': timestamp}}
admin_sessions = set()  # Track admin dashboard sessions

# Reference to RawWebSocketServer — set by app.py at startup
_raw_websocket_server = None


def set_raw_websocket_server(server):
    """Set the raw WebSocket server reference for device tracking."""
    global _raw_websocket_server
    _raw_websocket_server = server


def get_connected_devices_info():
    """Get information about all connected devices across all transports."""
    tv_devices = []
    admin_count = 0
    streamerbot_devices = []
    
    for session_id, device_info in connected_devices.items():
        if device_info['type'] == 'tv':
            tv_devices.append({
                'id': session_id,
                'type': 'tv',
                'user_agent': device_info['user_agent'],
                'connected_at': device_info['connected_at']
            })
        elif device_info['type'] == 'admin':
            admin_count += 1
    
    # Get StreamerBot raw WebSocket connections
    if _raw_websocket_server and _raw_websocket_server.clients:
        for client in _raw_websocket_server.clients:
            try:
                streamerbot_devices.append({
                    'id': f"streamerbot_{client.remote_address[0]}:{client.remote_address[1]}",
                    'type': 'streamerbot',
                    'remote_address': client.remote_address,
                    'connected': True
                })
            except Exception as e:
                logger.error("Error getting StreamerBot client info: %s", e)
    
    streamerbot_count = len(streamerbot_devices)
    
    return {
        'tv_devices': tv_devices,
        'tv_count': len(tv_devices),
        'admin_count': admin_count,
        'streamerbot_devices': streamerbot_devices,
        'streamerbot_count': streamerbot_count,
        'total_count': len(connected_devices) + streamerbot_count
    }


def get_tv_devices_count():
    """Get count of connected TV devices (excluding admin)"""
    return len([d for d in connected_devices.values() if d['type'] == 'tv'])
