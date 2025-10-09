from flask import Flask, request
from flask_cors import CORS as FlaskCORS

from app.core.db import close_db
from app.routes.auth import bp as auth_bp
from app.routes.me import bp as me_bp
from app.routes.trail_items import bp as trail_items_bp
from app.routes.trails import bp as trails_bp
from app.routes.certificates import bp as certificates_bp
from app.routes.user_trails import bp as user_trails_bp
from app.routes.forums import bp as forums_bp
from app.services.forum_bootstrap import ensure_forum_tables

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
]


def create_app() -> Flask:
    app = Flask(__name__)

    ensure_forum_tables()

    # Use SEMPRE o Flask-CORS real
    FlaskCORS(
        app,
        origins=ALLOWED_ORIGINS,
        supports_credentials=True,
        expose_headers=["X-CSRF-Token", "X-CSRFToken"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "X-CSRFToken",
            "X-Requested-With",
        ],
    )

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = ",".join(
                [
                    "Content-Type",
                    "X-CSRF-Token",
                    "X-CSRFToken",
                    "X-Requested-With",
                ]
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET,POST,PUT,DELETE,OPTIONS"
            )
        return response

    @app.route("/certificates/me/trails/<int:trail_id>", methods=["OPTIONS"])
    def certificates_preflight(trail_id: int):
        from flask import make_response

        response = make_response("", 204)
        return add_cors_headers(response)

    app.register_blueprint(trail_items_bp)
    app.register_blueprint(trails_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(me_bp)
    app.register_blueprint(user_trails_bp)
    app.register_blueprint(certificates_bp)
    app.register_blueprint(forums_bp)

    app.teardown_appcontext(close_db)
    return app


app = create_app()
