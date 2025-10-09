from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    insert,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .trails import Trails

GENERAL_FORUM_SLUG = "forum-geral"

if TYPE_CHECKING:  # pragma: no cover - hints only
    from .trails import Trails
    from .users import User


class Forum(Base):
    __tablename__ = "forums"
    __table_args__ = (UniqueConstraint("trail_id", name="uq_forums_trail_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_general: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trail_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trails.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trail: Mapped[Optional["Trails"]] = relationship(back_populates="forums")
    topics: Mapped[List["ForumTopic"]] = relationship(
        back_populates="forum", cascade="all, delete-orphan"
    )


class ForumTopic(Base):
    __tablename__ = "forum_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forum_id: Mapped[int] = mapped_column(
        ForeignKey("forums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    forum: Mapped["Forum"] = relationship(back_populates="topics")
    created_by: Mapped[Optional["User"]] = relationship()
    posts: Mapped[List["ForumPost"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
        order_by="ForumPost.created_at",
    )


class ForumPost(Base):
    __tablename__ = "forum_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("forum_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    parent_post_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    topic: Mapped["ForumTopic"] = relationship(back_populates="posts")
    author: Mapped[Optional["User"]] = relationship()
    parent_post: Mapped[Optional["ForumPost"]] = relationship(
        remote_side="ForumPost.id", back_populates="replies"
    )
    replies: Mapped[List["ForumPost"]] = relationship(
        back_populates="parent_post", cascade="all, delete-orphan"
    )


def make_trail_forum_slug(trail_id: int) -> str:
    return f"trilha-{trail_id}"


@event.listens_for(Trails, "after_insert", propagate=True)
def create_forum_for_trail(
    mapper, connection, trail
) -> None:  # pragma: no cover - small glue
    table = Forum.__table__
    slug_value = make_trail_forum_slug(trail.id)
    stmt = insert(table).values(
        slug=slug_value,
        title=trail.name,
        description=f"Discussões sobre {trail.name}",
        trail_id=trail.id,
        is_general=False,
    )

    dialect = connection.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(table)
            .values(
                slug=slug_value,
                title=trail.name,
                description=f"Discussões sobre {trail.name}",
                trail_id=trail.id,
                is_general=False,
            )
            .on_conflict_do_nothing(index_elements=["trail_id"])
        )
    elif dialect == "sqlite":
        stmt = stmt.prefix_with("OR IGNORE")

    connection.execute(stmt)
