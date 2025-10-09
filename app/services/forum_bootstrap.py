"""Helpers to ensure forum infrastructure exists before serving requests."""

from __future__ import annotations

from app.core.db import engine
from app.models.base import Base
from app.models.forums import Forum, ForumTopic, ForumPost


def ensure_forum_tables() -> None:
    """Create forum-related tables if they do not exist yet."""

    Base.metadata.create_all(
        bind=engine,
        tables=[Forum.__table__, ForumTopic.__table__, ForumPost.__table__],
    )
