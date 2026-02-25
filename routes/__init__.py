"""
Angels-TV-Animator: Route blueprints package.
"""

from routes.public import public_bp
from routes.admin import admin_bp
from routes.obs_api import obs_api_bp


def register_routes(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(obs_api_bp)
