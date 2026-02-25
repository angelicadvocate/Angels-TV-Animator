"""
Angels-TV-Animator: Admin route blueprint.
Handles admin pages, user management API, file management API, thumbnails, and theme API.
"""

import json
import logging
import asyncio
import eventlet
import eventlet.tpool
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename

from config import (
    __version__, ANIMATIONS_DIR, VIDEOS_DIR, DATA_DIR,
    CONFIG_DIR, USERS_FILE, HTML_EXTENSIONS, VIDEO_EXTENSIONS,
    get_current_port
)
from extensions import app, get_obs_client
from auth_manager import (
    User, admin_required, api_admin_required,
    load_users_config, save_users_config, verify_password,
    get_user_theme as _get_user_theme_helper
)
from media_manager import (
    load_state, find_media_file,
    get_animation_files, get_video_files, get_all_media_files
)
from device_tracking import get_connected_devices_info
from thumbnail_service import get_thumbnail_service

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Import generate_password_hash for user creation
from werkzeug.security import generate_password_hash


@admin_bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle file uploads that exceed MAX_CONTENT_LENGTH"""
    from config import MAX_UPLOAD_SIZE_MB
    return jsonify({
        'error': f'File too large. Maximum upload size is {MAX_UPLOAD_SIZE_MB}MB.'
    }), 413


def _run_async(coro):
    """Run an async coroutine in a real OS thread via eventlet.tpool.
    
    eventlet monkey-patches asyncio and threading, so creating a new asyncio
    event loop inside a green thread fails with 'Cannot run the event loop
    while another loop is running'.  tpool.execute dispatches to a real
    native thread where asyncio works normally.
    """
    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return eventlet.tpool.execute(_worker)


# =============================================================================
# Admin Page Routes
# =============================================================================

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if current_user.is_authenticated:
        return redirect(url_for('admin.admin_dashboard'))

    error = None
    username = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            error = "Please enter both username and password."
        elif verify_password(username, password):
            user = User(username)
            login_user(user, remember=remember)

            try:
                users_data = load_users_config()
                if username in users_data.get('admin_users', {}):
                    users_data['admin_users'][username]['last_login'] = datetime.now().isoformat()
                    save_users_config(users_data)
            except Exception as e:
                logger.error("Error updating last login for %s: %s", username, e)

            if username == 'admin' and password == 'admin123':
                session['show_default_credentials_warning'] = True

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/admin'):
                return redirect(next_page)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            error = "Invalid username or password."

    return render_template('admin_login.html', error=error, username=username)


@admin_bp.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    logout_user()
    return redirect(url_for('public.index'))


@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    user_theme = _get_user_theme_helper(current_user.username)
    show_credentials_warning = session.pop('show_default_credentials_warning', False)

    return render_template('admin_dashboard.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         show_credentials_warning=show_credentials_warning,
                         app_version=__version__)


@admin_bp.route('/admin/manage')
@admin_required
def admin_manage_files():
    """File management page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_manage.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/users')
@admin_required
def admin_users():
    """User management page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_users.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/obs')
@admin_required
def admin_obs_management():
    """OBS WebSocket management page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_obs_management.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/instructions')
@admin_required
def admin_instructions():
    """Instructions and setup page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_instructions.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/instructions/getting-started')
@admin_required
def admin_instructions_getting_started():
    """Getting Started instructions page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_instructions_getting_started.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/instructions/obs-integration')
@admin_required
def admin_instructions_obs():
    """OBS Studio Integration instructions page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_instructions_obs.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/instructions/streamerbot-integration')
@admin_required
def admin_instructions_streamerbot():
    """StreamerBot Integration instructions page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_instructions_streamerbot.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


@admin_bp.route('/admin/instructions/troubleshooting')
@admin_required
def admin_instructions_troubleshooting():
    """Troubleshooting & FAQ instructions page"""
    user_theme = _get_user_theme_helper(current_user.username)
    return render_template('admin_instructions_troubleshooting.html',
                         user_theme=user_theme,
                         current_username=current_user.username,
                         app_version=__version__)


# =============================================================================
# User Management API
# =============================================================================

@admin_bp.route('/admin/api/users', methods=['GET'])
@admin_required
def api_get_users():
    """API endpoint to get list of users"""
    try:
        users_data = load_users_config()
        admin_users = users_data.get('admin_users', {})

        user_list = []
        for username, user_info in admin_users.items():
            user_list.append({
                'username': username,
                'created_at': user_info.get('created_at'),
                'last_login': user_info.get('last_login'),
                'permissions': user_info.get('permissions', [])
            })

        return jsonify({
            'success': True,
            'users': user_list,
            'current_user': current_user.username
        })

    except Exception as e:
        logger.error("Error getting users: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/users', methods=['POST'])
@admin_required
def api_add_user():
    """API endpoint to add new user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400

        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters long'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters long'}), 400

        users_data = load_users_config()
        admin_users = users_data.get('admin_users', {})

        if username in admin_users:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400

        admin_users[username] = {
            'password': generate_password_hash(password),
            'created_at': datetime.now().isoformat(),
            'permissions': ['read', 'write', 'delete', 'upload'],
            'theme': 'dark'
        }

        users_data['admin_users'] = admin_users

        if save_users_config(users_data):
            return jsonify({'success': True, 'message': f'User {username} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save user data'}), 500

    except Exception as e:
        logger.error("Error adding user: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/users', methods=['DELETE'])
@admin_required
def api_delete_user():
    """API endpoint to delete user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400

        if username == current_user.username:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400

        users_data = load_users_config()
        admin_users = users_data.get('admin_users', {})

        if username not in admin_users:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if len(admin_users) <= 1:
            return jsonify({'success': False, 'error': 'Cannot delete the last remaining user'}), 400

        del admin_users[username]
        users_data['admin_users'] = admin_users

        if save_users_config(users_data):
            return jsonify({'success': True, 'message': f'User {username} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save user data'}), 500

    except Exception as e:
        logger.error("Error deleting user: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/change-password', methods=['POST'])
@admin_required
def api_change_password():
    """API endpoint to change current user's password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'success': False, 'error': 'Current and new passwords are required'}), 400

        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'New password must be at least 6 characters long'}), 400

        if not verify_password(current_user.username, current_password):
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400

        users_data = load_users_config()
        admin_users = users_data.get('admin_users', {})

        if current_user.username not in admin_users:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        admin_users[current_user.username]['password'] = generate_password_hash(new_password)
        users_data['admin_users'] = admin_users

        if save_users_config(users_data):
            return jsonify({'success': True, 'message': 'Password changed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save password change'}), 500

    except Exception as e:
        logger.error("Error changing password: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# Admin Status & Files API
# =============================================================================

@admin_bp.route('/admin/api/status')
@api_admin_required
def admin_status():
    """API endpoint for admin dashboard status"""
    try:
        state = load_state()
        current_media = state.get('current_animation')
        media_path, media_type = find_media_file(current_media) if current_media else (None, None)

        devices_info = get_connected_devices_info()

        obs_client = get_obs_client()
        obs_connected = obs_client.connected if obs_client else False

        return jsonify({
            'status': 'running',
            'current_media': current_media,
            'media_type': media_type,
            'animations_count': len(get_animation_files()),
            'videos_count': len(get_video_files()),
            'total_media_count': len(get_all_media_files()),
            'connected_clients': devices_info['tv_count'],
            'tv_devices': devices_info['tv_devices'],
            'admin_count': devices_info['admin_count'],
            'streamerbot_devices': devices_info['streamerbot_devices'],
            'streamerbot_count': devices_info['streamerbot_count'],
            'total_connections': devices_info['total_count'],
            'available_animations': get_animation_files(),
            'available_videos': get_video_files(),
            'available_media': get_all_media_files(),
            'obs_connected': obs_connected
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/files')
@api_admin_required
def admin_list_files():
    """API endpoint to list all files with metadata"""
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

        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# File Upload / Delete / Thumbnails
# =============================================================================

@admin_bp.route('/admin/api/upload', methods=['POST'])
@admin_required
def admin_upload_file():
    """Handle file uploads for animations and videos"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
        file_ext = Path(filename).suffix.lower()

        if file_ext in HTML_EXTENSIONS:
            destination_dir = ANIMATIONS_DIR
            file_type = 'animation'
        elif file_ext in VIDEO_EXTENSIONS:
            destination_dir = VIDEOS_DIR
            file_type = 'video'
        else:
            return jsonify({
                'error': f'Unsupported file type: {file_ext}',
                'supported_types': list(HTML_EXTENSIONS | VIDEO_EXTENSIONS)
            }), 400

        destination_dir.mkdir(exist_ok=True)

        file_path = destination_dir / filename
        file.save(str(file_path))

        # Generate thumbnail in a real OS thread (eventlet.tpool)
        try:
            thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")
            try:
                success, thumbnail_name = _run_async(
                    thumbnail_service.generate_thumbnail(filename, file_path)
                )
                if success:
                    app.logger.info(f"Generated thumbnail for uploaded file: {filename}")
                else:
                    app.logger.warning(f"Failed to generate thumbnail for uploaded file: {filename}")
            except Exception as e:
                app.logger.error(f"Thumbnail generation error for {filename}: {str(e)}")

        except Exception as e:
            app.logger.warning(f"Could not start thumbnail generation for {filename}: {str(e)}")

        return jsonify({
            'success': True,
            'filename': filename,
            'file_type': file_type,
            'size': file_path.stat().st_size,
            'message': f'File {filename} uploaded successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/delete/<file_type>/<filename>', methods=['DELETE'])
@admin_required
def admin_delete_file(file_type, filename):
    """Delete a file (animation or video)"""
    try:
        if file_type == 'animation':
            file_path = ANIMATIONS_DIR / filename
        elif file_type == 'video':
            file_path = VIDEOS_DIR / filename
        else:
            return jsonify({'error': 'Invalid file type'}), 400

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        state = load_state()
        current_media = state.get('current_animation')
        if current_media == filename:
            return jsonify({'error': 'Cannot delete currently active media'}), 400

        file_path.unlink()

        try:
            thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")
            thumbnail_path = thumbnail_service.get_thumbnail_path(filename)
            if thumbnail_path.exists():
                thumbnail_path.unlink()
                app.logger.info(f"Deleted thumbnail for: {filename}")
        except Exception as e:
            app.logger.warning(f"Could not delete thumbnail for {filename}: {str(e)}")

        return jsonify({
            'success': True,
            'message': f'File {filename} deleted successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/thumbnail/<filename>')
@admin_required
def admin_thumbnail(filename):
    """Generate or serve thumbnails for files"""
    try:
        thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")

        thumbnail_path = thumbnail_service.serve_thumbnail(filename)
        if thumbnail_path:
            return send_from_directory(
                str(thumbnail_path.parent),
                thumbnail_path.name,
                mimetype='image/png'
            )

        file_ext = filename.lower().split('.')[-1]

        if file_ext in ['html', 'htm']:
            html_path = Path(ANIMATIONS_DIR) / filename
            if html_path.exists():
                try:
                    success, thumbnail_name = _run_async(
                        thumbnail_service.generate_thumbnail(filename, html_path)
                    )
                    if success:
                        thumbnail_path = thumbnail_service.serve_thumbnail(filename)
                        if thumbnail_path:
                            return send_from_directory(
                                str(thumbnail_path.parent),
                                thumbnail_path.name,
                                mimetype='image/png'
                            )
                except Exception as e:
                    app.logger.warning(f"Failed to generate HTML thumbnail for {filename}: {str(e)}")

        elif file_ext in ['mp4', 'webm', 'mov', 'avi', 'mkv']:
            video_path = Path(VIDEOS_DIR) / filename
            if video_path.exists():
                try:
                    success, thumbnail_name = _run_async(
                        thumbnail_service.generate_thumbnail(filename, video_path)
                    )
                    if success:
                        thumbnail_path = thumbnail_service.serve_thumbnail(filename)
                        if thumbnail_path:
                            return send_from_directory(
                                str(thumbnail_path.parent),
                                thumbnail_path.name,
                                mimetype='image/png'
                            )
                except Exception as e:
                    app.logger.warning(f"Failed to generate video thumbnail for {filename}: {str(e)}")

        # Fallback SVG placeholders
        if file_ext in ['html', 'htm']:
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="320" height="180" xmlns="http://www.w3.org/2000/svg">
  <rect width="320" height="180" fill="#2c3e50"/>
  <text x="160" y="95" text-anchor="middle" fill="white" font-family="Arial" font-size="16">{filename[:25]}{'...' if len(filename) > 25 else ''}</text>
  <text x="160" y="115" text-anchor="middle" fill="#bdc3c7" font-family="Arial" font-size="12">HTML Animation</text>
</svg>'''
            return svg_content, 200, {'Content-Type': 'image/svg+xml'}
        else:
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="320" height="180" xmlns="http://www.w3.org/2000/svg">
  <rect width="320" height="180" fill="#34495e"/>
  <polygon points="140,70 140,110 180,90" fill="white"/>
  <text x="160" y="135" text-anchor="middle" fill="white" font-family="Arial" font-size="14">{filename[:25]}{'...' if len(filename) > 25 else ''}</text>
  <text x="160" y="155" text-anchor="middle" fill="#bdc3c7" font-family="Arial" font-size="10">Video File</text>
</svg>'''
            return svg_content, 200, {'Content-Type': 'image/svg+xml'}

    except Exception as e:
        app.logger.error(f"Thumbnail generation error for {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/thumbnails/generate', methods=['POST'])
@admin_required
def admin_generate_thumbnails():
    """Generate thumbnails for all files"""
    try:
        thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")

        def generate_all_thumbnails():
            try:
                results = _run_async(
                    thumbnail_service.generate_all_thumbnails(
                        Path(ANIMATIONS_DIR),
                        Path(VIDEOS_DIR)
                    )
                )
                app.logger.info(f"Thumbnail generation complete: {results}")

                cleaned_count = thumbnail_service.cleanup_orphaned_thumbnails(
                    Path(ANIMATIONS_DIR),
                    Path(VIDEOS_DIR)
                )
                results['orphaned_cleaned'] = cleaned_count
                return results
            except Exception as e:
                app.logger.error(f"Bulk thumbnail generation failed: {str(e)}")
                return {'error': str(e)}

        eventlet.spawn_n(generate_all_thumbnails)

        return jsonify({
            'success': True,
            'message': 'Thumbnail generation started in background'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/thumbnails/status', methods=['GET'])
@admin_required
def admin_thumbnails_status():
    """Get thumbnail generation status"""
    try:
        thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")

        thumbnail_count = len(list(thumbnail_service.thumbnails_dir.glob('*.png')))

        html_files = list(Path(ANIMATIONS_DIR).glob('*.html')) if Path(ANIMATIONS_DIR).exists() else []
        video_extensions = ['*.mp4', '*.webm', '*.mov', '*.avi', '*.mkv']
        video_files = []

        if Path(VIDEOS_DIR).exists():
            for pattern in video_extensions:
                video_files.extend(list(Path(VIDEOS_DIR).glob(pattern)))

        total_files = len(html_files) + len(video_files)

        files_with_thumbnails = 0
        for html_file in html_files:
            if thumbnail_service.thumbnail_exists(html_file.name, html_file):
                files_with_thumbnails += 1

        for video_file in video_files:
            if thumbnail_service.thumbnail_exists(video_file.name, video_file):
                files_with_thumbnails += 1

        return jsonify({
            'total_files': total_files,
            'html_files': len(html_files),
            'video_files': len(video_files),
            'thumbnail_count': thumbnail_count,
            'files_with_thumbnails': files_with_thumbnails,
            'completion_percentage': round((files_with_thumbnails / total_files * 100) if total_files > 0 else 100, 1)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/thumbnails/debug', methods=['GET'])
@admin_required
def admin_thumbnails_debug():
    """Debug endpoint to list actual thumbnail files"""
    try:
        thumbnail_service = get_thumbnail_service(f"http://localhost:{get_current_port()}")

        thumbnail_files = list(thumbnail_service.thumbnails_dir.glob('*.png'))

        debug_info = {
            'thumbnails_directory': str(thumbnail_service.thumbnails_dir),
            'directory_exists': thumbnail_service.thumbnails_dir.exists(),
            'thumbnail_files': [
                {
                    'filename': f.name,
                    'size_bytes': f.stat().st_size if f.exists() else 0,
                    'modified': f.stat().st_mtime if f.exists() else 0
                } for f in thumbnail_files
            ],
            'total_thumbnails': len(thumbnail_files)
        }

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Theme API
# =============================================================================

@admin_bp.route('/admin/api/theme', methods=['GET'])
@admin_required
def get_user_theme():
    """Get current user's theme preference"""
    try:
        users_data = load_users_config()
        user_data = users_data.get('admin_users', {}).get(current_user.username, {})
        theme = user_data.get('theme', 'dark')
        return jsonify({'theme': theme})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/theme', methods=['POST'])
@admin_required
def save_user_theme():
    """Save current user's theme preference"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        theme = data.get('theme', 'dark')
        logger.debug("Saving theme '%s' for user '%s'", theme, current_user.username)

        if theme not in ['light', 'dark']:
            return jsonify({'error': 'Invalid theme. Must be "light" or "dark"'}), 400

        users_data = load_users_config()

        if current_user.username in users_data.get('admin_users', {}):
            users_data['admin_users'][current_user.username]['theme'] = theme

            try:
                with open(USERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(users_data, f, indent=4, ensure_ascii=False)
                return jsonify({'success': True, 'theme': theme})
            except Exception as write_error:
                return jsonify({'error': f'Failed to save theme: {write_error}'}), 500
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Debug
# =============================================================================

@admin_bp.route('/admin/api/debug/user')
@admin_required
def debug_user_data():
    """Debug endpoint to check current user data"""
    try:
        users_data = load_users_config()
        user_data = users_data.get('admin_users', {}).get(current_user.username, {})
        return jsonify({
            'username': current_user.username,
            'user_data': user_data,
            'theme': user_data.get('theme', 'NOT_SET')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
