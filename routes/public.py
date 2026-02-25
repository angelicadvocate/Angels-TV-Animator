"""
Angels-TV-Animator: Public route blueprint.
Handles unauthenticated routes: index, trigger, animations, health, mobile, video serving.
"""

import json
import logging
import os
import shutil
import time
from flask import Blueprint, jsonify, request, send_from_directory, render_template

from config import ANIMATIONS_DIR, VIDEOS_DIR, DATA_DIR, STATE_FILE, __version__
from extensions import socketio, get_obs_client
from device_tracking import get_connected_devices_info
from media_manager import (
    load_state, save_state, find_media_file, serve_video,
    get_animation_files, get_video_files, get_all_media_files
)

public_bp = Blueprint('public', __name__)
logger = logging.getLogger(__name__)


@public_bp.route('/')
def index():
    """Serve the current media (animation or video)"""
    state = load_state()
    current_media = state.get('current_animation', 'anim1.html')

    media_path, media_type = find_media_file(current_media)

    if not media_path:
        all_media = get_all_media_files()
        if all_media:
            current_media = all_media[0]
            state['current_animation'] = current_media
            save_state(state)
            media_path, media_type = find_media_file(current_media)
        else:
            return "No media files available. Please add HTML or video files to the animations/ or videos/ directories.", 404

    if media_type == 'video':
        return serve_video(current_media)
    else:
        return send_from_directory(ANIMATIONS_DIR, current_media)


@public_bp.route('/videos/<filename>')
def serve_video_file(filename):
    """Serve video files from the videos directory"""
    return send_from_directory(VIDEOS_DIR, filename)


@public_bp.route('/mobile')
@public_bp.route('/control')
def mobile_control():
    """Serve mobile stream control interface"""
    return render_template('mobile_control.html')


@public_bp.route('/trigger', methods=['POST'])
def trigger():
    """Update the current media via JSON payload"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        media_file = data.get('animation')
        if not media_file:
            return jsonify({"error": "Missing 'animation' field in payload"}), 400

        media_path, media_type = find_media_file(media_file)
        if not media_path:
            available_media = get_all_media_files()
            return jsonify({
                "error": f"Media file '{media_file}' not found",
                "available_media": available_media,
                "available_animations": get_animation_files(),
                "available_videos": get_video_files()
            }), 404

        state = load_state()
        state['current_animation'] = media_file
        save_state(state)

        socketio.emit('animation_changed', {
            'current_animation': media_file,
            'media_type': media_type,
            'message': f"Media changed to '{media_file}' ({media_type})",
            'refresh_page': True
        })
        logger.debug("[TRIGGER] Emitted 'animation_changed' for '%s' with refresh_page=True", media_file)

        socketio.emit('page_refresh', {
            'reason': 'media_changed',
            'new_media': media_file,
            'media_type': media_type
        })
        logger.debug("[TRIGGER] Emitted 'page_refresh' for '%s'", media_file)

        return jsonify({
            "success": True,
            "current_animation": media_file,
            "media_type": media_type,
            "message": f"Media updated to '{media_file}' ({media_type})"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@public_bp.route('/trigger', methods=['GET'])
def trigger_get():
    """Update the current media via GET with URL parameters"""
    try:
        media_file = request.args.get('animation')
        if not media_file:
            return jsonify({"error": "Missing 'animation' parameter"}), 400

        media_path, media_type = find_media_file(media_file)
        if not media_path:
            available_media = get_all_media_files()
            return jsonify({
                "error": f"Media file '{media_file}' not found",
                "available_media": available_media,
                "available_animations": get_animation_files(),
                "available_videos": get_video_files()
            }), 404

        state = load_state()
        state['current_animation'] = media_file
        save_state(state)

        socketio.emit('animation_changed', {
            'current_animation': media_file,
            'media_type': media_type,
            'message': f"Media changed to '{media_file}' ({media_type}) via GET trigger",
            'refresh_page': True
        })

        socketio.emit('page_refresh', {
            'reason': 'get_trigger',
            'new_media': media_file,
            'media_type': media_type
        })

        return jsonify({
            "success": True,
            "current_animation": media_file,
            "media_type": media_type,
            "message": f"Media updated to '{media_file}' ({media_type}) via GET"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@public_bp.route('/animations', methods=['GET'])
def list_animations():
    """List all available media files"""
    animations = get_animation_files()
    videos = get_video_files()
    all_media = get_all_media_files()
    state = load_state()
    current_media = state.get('current_animation', None)

    return jsonify({
        "animations": animations,
        "videos": videos,
        "all_media": all_media,
        "current_animation": current_media,
        "current_media": current_media,
        "count": len(all_media),
        "animation_count": len(animations),
        "video_count": len(videos)
    }), 200


@public_bp.route('/stop', methods=['POST'])
def stop_animations():
    """Stop all animations and clear current media"""
    try:
        state = load_state()
        state['current_animation'] = None

        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

        socketio.emit('animation_stopped', {
            'message': 'All animations stopped',
            'timestamp': time.time()
        })

        return jsonify({
            "success": True,
            "message": "All animations stopped"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@public_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint — comprehensive server status overview."""

    # --- Media counts ---
    animations = get_animation_files()
    videos = get_video_files()

    # --- Current state ---
    state = load_state()
    current_media = state.get('current_animation', None)

    # --- Connected devices ---
    devices = get_connected_devices_info()

    # --- OBS connection status ---
    obs_client = get_obs_client()
    if obs_client:
        obs_status = {
            "configured": True,
            "connected": getattr(obs_client, 'connected', False),
        }
    else:
        obs_status = {
            "configured": False,
            "connected": False,
        }

    # --- Disk usage for data directory ---
    try:
        disk = shutil.disk_usage(str(DATA_DIR))
        disk_info = {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent_used": round((disk.used / disk.total) * 100, 1),
        }
    except Exception:
        disk_info = None

    # --- Uptime (process start time) ---
    try:
        pid = os.getpid()
        # Works on Linux/Docker; gracefully degrades elsewhere
        proc_stat = f"/proc/{pid}/stat"
        if os.path.exists(proc_stat):
            boot_time = os.stat(proc_stat).st_mtime
            uptime_seconds = int(time.time() - boot_time)
        else:
            uptime_seconds = None
    except Exception:
        uptime_seconds = None

    return jsonify({
        "status": "healthy",
        "version": __version__,
        "media": {
            "animations_available": len(animations),
            "videos_available": len(videos),
            "total_media_available": len(animations) + len(videos),
            "currently_playing": current_media,
        },
        "connections": {
            "tv_clients": devices.get('tv_count', 0),
            "admin_clients": devices.get('admin_count', 0),
            "streamerbot_clients": devices.get('streamerbot_count', 0),
            "total_clients": devices.get('total_count', 0),
        },
        "obs": obs_status,
        "disk": disk_info,
        "uptime_seconds": uptime_seconds,
    }), 200


@public_bp.route('/api/files')
def list_files():
    """Public API endpoint to list all files for mobile interface"""
    try:
        files = []

        for filename in get_animation_files():
            file_path = ANIMATIONS_DIR / filename
            files.append({
                'name': filename,
                'type': 'animation',
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'url': f'/animations/{filename}',
                'thumbnail': f'/admin/api/thumbnail/{filename}'
            })

        for filename in get_video_files():
            file_path = VIDEOS_DIR / filename
            files.append({
                'name': filename,
                'type': 'video',
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'url': f'/videos/{filename}',
                'thumbnail': f'/admin/api/thumbnail/{filename}'
            })

        state = load_state()
        current_animation = state.get('current_animation', None)

        return jsonify({
            'files': files,
            'current_animation': current_animation
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
