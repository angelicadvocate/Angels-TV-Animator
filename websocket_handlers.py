"""
Angels-TV-Animator: SocketIO event handlers.
All @socketio.on() handlers for real-time WebSocket communication.
"""

import logging
import time
from flask import request
from flask_socketio import emit

from extensions import socketio
from media_manager import (
    load_state, save_state, find_media_file,
    get_animation_files, get_video_files, get_all_media_files,
    is_video_file
)
from device_tracking import (
    connected_devices, admin_sessions,
    get_connected_devices_info
)

logger = logging.getLogger(__name__)


@socketio.on('connect')
def handle_connect():
    """Handle client WebSocket connection"""
    session_id = request.sid
    user_agent = request.headers.get('User-Agent', 'Unknown')

    referrer = request.headers.get('Referer', '')
    device_type = 'admin' if '/admin' in referrer else 'tv'

    connected_devices[session_id] = {
        'type': device_type,
        'user_agent': user_agent,
        'connected_at': time.time()
    }

    if device_type == 'admin':
        admin_sessions.add(session_id)

    logger.info("Client connected: %s (type: %s)", session_id, device_type)

    socketio.emit('devices_updated', get_connected_devices_info(), room=None)

    emit('status', {
        'message': 'Connected to Angels-TV-Animator server',
        'current_animation': load_state().get('current_animation'),
        'available_animations': get_animation_files()
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client WebSocket disconnection"""
    session_id = request.sid
    device_info = connected_devices.pop(session_id, {})
    admin_sessions.discard(session_id)

    device_type = device_info.get('type', 'unknown')
    logger.info("Client disconnected: %s (type: %s)", session_id, device_type)

    socketio.emit('devices_updated', get_connected_devices_info(), room=None)


@socketio.on('register_admin')
def handle_register_admin():
    """Register a client as admin dashboard"""
    session_id = request.sid
    if session_id in connected_devices:
        connected_devices[session_id]['type'] = 'admin'
        admin_sessions.add(session_id)
        logger.debug("Client %s registered as admin dashboard", session_id)

        socketio.emit('devices_updated', get_connected_devices_info(), room=None)


@socketio.on('trigger_animation')
def handle_trigger_animation(data):
    """Handle animation trigger via WebSocket"""
    try:
        animation = data.get('animation')
        if not animation:
            emit('error', {'message': 'Missing animation field'})
            return

        media_path, media_type = find_media_file(animation)
        if not media_path:
            available_media = get_all_media_files()
            emit('error', {
                'message': f"Media file '{animation}' not found",
                'available_media': available_media
            })
            return

        state = load_state()
        old_animation = state.get('current_animation')
        state['current_animation'] = animation
        save_state(state)

        socketio.emit('animation_changed', {
            'previous_animation': old_animation,
            'current_animation': animation,
            'media_type': media_type,
            'message': f"Media changed to '{animation}' ({media_type})",
            'refresh_page': True
        }, broadcast=True)

        socketio.emit('page_refresh', {
            'reason': 'media_changed',
            'new_media': animation,
            'media_type': media_type
        }, broadcast=True)

        logger.info("Animation changed from '%s' to '%s' via WebSocket", old_animation, animation)

    except Exception as e:
        emit('error', {'message': str(e)})
        logger.error("WebSocket error: %s", e)


@socketio.on('get_status')
def handle_get_status():
    """Get current server status via WebSocket"""
    state = load_state()
    current_media = state.get('current_animation')
    media_path, media_type = find_media_file(current_media) if current_media else (None, None)

    emit('status', {
        'current_animation': current_media,
        'current_media': current_media,
        'media_type': media_type,
        'available_animations': get_animation_files(),
        'available_videos': get_video_files(),
        'available_media': get_all_media_files(),
        'animations_count': len(get_animation_files()),
        'videos_count': len(get_video_files()),
        'total_media_count': len(get_all_media_files())
    })


@socketio.on('scene_change')
def handle_scene_change(data):
    """Handle OBS scene change event"""
    try:
        scene_name = data.get('scene_name', '').lower()
        animation_mapping = data.get('animation_mapping', {})

        if animation_mapping and scene_name in animation_mapping:
            animation = animation_mapping[scene_name]
        else:
            default_mapping = {
                'gaming': 'anim1.html',
                'chatting': 'anim2.html',
                'brb': 'anim3.html',
                'be right back': 'anim3.html',
                'starting soon': 'anim1.html',
                'ending soon': 'anim2.html'
            }
            animation = default_mapping.get(scene_name)

        if animation:
            handle_trigger_animation({'animation': animation})
        else:
            emit('info', {
                'message': f"No animation mapping for scene '{data.get('scene_name')}'"
            })

    except Exception as e:
        emit('error', {'message': f"Scene change error: {str(e)}"})
        logger.error("Scene change error: %s", e)


@socketio.on('streamerbot_event')
def handle_streamerbot_event(data):
    """Handle StreamerBot events"""
    try:
        event_type = data.get('event_type')
        event_data = data.get('data', {})

        logger.info("StreamerBot event received: %s", event_type)

        if event_type == 'scene_change':
            handle_scene_change(event_data)
        elif event_type == 'trigger_animation':
            handle_trigger_animation(event_data)
        elif event_type == 'custom_animation':
            animation = event_data.get('animation')
            if animation:
                handle_trigger_animation({'animation': animation})
        else:
            emit('info', {'message': f"Unhandled StreamerBot event: {event_type}"})

    except Exception as e:
        emit('error', {'message': f"StreamerBot event error: {str(e)}"})
        logger.error("StreamerBot event error: %s", e)


@socketio.on('video_control')
def handle_video_control(data):
    """Handle video playback control commands"""
    try:
        action = data.get('action')
        value = data.get('value')

        if not action:
            emit('error', {'message': 'Missing action for video control'})
            return

        state = load_state()
        current_media = state.get('current_animation')
        if current_media and not is_video_file(current_media):
            emit('error', {'message': 'Current media is not a video file'})
            return

        socketio.emit('video_control', {
            'action': action,
            'value': value,
            'message': f"Video control: {action}"
        }, broadcast=True)

        logger.debug("Video control: %s %s", action, f'({value})' if value is not None else '')

    except Exception as e:
        emit('error', {'message': f"Video control error: {str(e)}"})
        logger.error("Video control error: %s", e)


@socketio.on('video_seek')
def handle_video_seek(data):
    """Handle video seek commands"""
    try:
        seek_time = data.get('time', 0)

        socketio.emit('video_control', {
            'action': 'seek',
            'value': seek_time,
            'message': f"Video seek to {seek_time}s"
        }, broadcast=True)

        logger.debug("Video seek to %ss", seek_time)

    except Exception as e:
        emit('error', {'message': f"Video seek error: {str(e)}"})
        logger.error("Video seek error: %s", e)


@socketio.on('video_volume')
def handle_video_volume(data):
    """Handle video volume control"""
    try:
        volume = data.get('volume', 0.5)
        volume = max(0, min(1, float(volume)))

        socketio.emit('video_control', {
            'action': 'volume',
            'value': volume,
            'message': f"Video volume set to {int(volume * 100)}%"
        }, broadcast=True)

        logger.debug("Video volume set to %d%%", int(volume * 100))

    except Exception as e:
        emit('error', {'message': f"Video volume error: {str(e)}"})
        logger.error("Video volume error: %s", e)
