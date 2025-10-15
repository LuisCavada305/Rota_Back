import pytest

from app.core.settings import Settings


def test_rejects_short_jwt_secret():
    with pytest.raises(ValueError):
        Settings(JWT_SECRET="short")


def test_accepts_csv_cors_list():
    cfg = Settings(
        JWT_SECRET="x" * 16,
        cors_allowed_origins="https://a.example, https://b.example",
    )
    assert cfg.cors_allowed_origins == [
        "https://a.example",
        "https://b.example",
    ]


def test_production_requires_hardening():
    with pytest.raises(ValueError):
        Settings(JWT_SECRET="y" * 16, ENV="prod", CSRF_SECRET=None)


def test_production_allows_custom_credentials():
    cfg = Settings(
        JWT_SECRET="z" * 16,
        ENV="prod",
        CSRF_SECRET="w" * 32,
        db_pass="not-default",
        db_user="not-default",
    )
    assert cfg.is_production is True
    assert cfg.db_pass == "not-default"
