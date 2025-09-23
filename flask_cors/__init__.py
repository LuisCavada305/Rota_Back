def CORS(app, origins=None, supports_credentials=False):
    """Minimal stub of flask_cors.CORS used for testing purposes."""
    app.config.setdefault("CORS", {})
    app.config["CORS"].update(
        {
            "origins": origins,
            "supports_credentials": supports_credentials,
        }
    )
    return app
