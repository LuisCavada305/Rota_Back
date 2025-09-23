from flask import Flask, request
from flask_cors import CORS as FlaskCORS

from app.core.db import close_db
from app.routes.auth import bp as auth_bp
from app.routes.me import bp as me_bp
from app.routes.trail_items import bp as trail_items_bp
from app.routes.trails import bp as trails_bp
from app.routes.user_trails import bp as user_trails_bp

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
]


def create_app() -> Flask:
    app = Flask(__name__)

    # Use SEMPRE o Flask-CORS real
    FlaskCORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

    app.register_blueprint(trail_items_bp)
    app.register_blueprint(trails_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(me_bp)
    app.register_blueprint(user_trails_bp)

    app.teardown_appcontext(close_db)
    return app


app = create_app()
