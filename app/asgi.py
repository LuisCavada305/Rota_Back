"""ASGI wrapper so the Flask app can run under Uvicorn."""

from uvicorn.middleware.wsgi import WSGIMiddleware

from app.main import create_app


def build_app():
    """Return the Flask application wrapped as ASGI."""
    flask_app = create_app()
    return WSGIMiddleware(flask_app)


app = build_app()
