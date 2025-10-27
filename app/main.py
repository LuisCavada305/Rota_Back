from flask import Flask, request
from flask_cors import CORS as FlaskCORS

from app.core.db import close_db
from app.core.settings import settings
from app.routes.auth import bp as auth_bp
from app.routes.me import bp as me_bp
from app.routes.trail_items import bp as trail_items_bp
from app.routes.trails import bp as trails_bp
from app.routes.certificates import bp as certificates_bp
from app.routes.user_trails import bp as user_trails_bp
from app.routes.forums import bp as forums_bp
from app.routes.admin import bp as admin_bp
from app.services.forum_bootstrap import ensure_forum_tables


def create_app() -> Flask:
    app = Flask(__name__)

    ensure_forum_tables()

    allowed_origins = settings.cors_allowed_origins_list() or [settings.API_ORIGIN]

    # Use SEMPRE o Flask-CORS real
    FlaskCORS(
        app,
        origins=allowed_origins,
        supports_credentials=True,
        expose_headers=settings.cors_expose_headers_list(),
        allow_headers=settings.cors_allow_headers_list(),
    )

    if settings.is_production:
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_SAMESITE="None",
        )

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin in settings.cors_origin_set:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = (
                settings.cors_allow_headers_string()
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET,POST,PUT,DELETE,OPTIONS,PATCH"
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
    app.register_blueprint(admin_bp)

    app.teardown_appcontext(close_db)

    @app.route("/healthz", methods=["GET", "HEAD"])
    def healthz():
        return ("", 200)

    return app


app = create_app()
