"""
Angels-TV-Animator: Authentication and user management module.
Handles user model, password verification, user CRUD, and auth decorators.
"""

import json
import logging
from datetime import datetime
from functools import wraps
from flask import request, redirect, url_for, jsonify
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from config import USERS_FILE, CONFIG_DIR
from extensions import login_manager

logger = logging.getLogger(__name__)


# =============================================================================
# User Model
# =============================================================================

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(username):
    """Load user for Flask-Login"""
    users_data = load_users_config()
    if username in users_data.get('admin_users', {}):
        return User(username)
    return None


# =============================================================================
# User Config I/O
# =============================================================================

def load_users_config():
    """Load users configuration from file"""
    try:
        if USERS_FILE.exists():
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading users config: %s", e)
    
    # Default config if file doesn't exist - use hashed password
    return {
        "admin_users": {
            "admin": {
                "password": generate_password_hash("admin123"),
                "created_at": datetime.now().isoformat(),
                "permissions": ["read", "write", "delete", "upload"]
            }
        }
    }


def save_users_config(users_data):
    """Save users configuration to file"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("Error saving users config: %s", e)
        return False


# =============================================================================
# Password Verification
# =============================================================================

def verify_password(username, password):
    """Verify user password - supports both hashed and plain text (for migration)"""
    users_data = load_users_config()
    admin_users = users_data.get('admin_users', {})
    
    if username in admin_users:
        stored_password = admin_users[username]['password']
        
        # Check if password is hashed (starts with pbkdf2:sha256: or similar)
        if stored_password.startswith(('pbkdf2:', 'scrypt:', 'bcrypt:')):
            return check_password_hash(stored_password, password)
        else:
            # Plain text password - check and migrate to hashed
            if stored_password == password:
                logger.warning("Migrating plain text password to hashed for user: %s", username)
                admin_users[username]['password'] = generate_password_hash(password)
                users_data['admin_users'] = admin_users
                save_users_config(users_data)
                return True
            return False
    
    return False


# =============================================================================
# Auth Decorators
# =============================================================================

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def api_admin_required(f):
    """Decorator to require admin authentication for API routes - returns JSON errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required', 'authenticated': False}), 401
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Theme Helper
# =============================================================================

def get_user_theme(username):
    """Get a user's theme preference"""
    try:
        users_data = load_users_config()
        user_data = users_data.get('admin_users', {}).get(username, {})
        return user_data.get('theme', 'dark')
    except Exception:
        return 'dark'
