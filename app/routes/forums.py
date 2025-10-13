from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import Blueprint, abort, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator, Field

from app.core.db import get_db
from app.repositories.ForumsRepository import ForumsRepository
from app.services.security import enforce_csrf, get_current_user
from app.services.sanitizer import sanitize_user_html


bp = Blueprint("forums", __name__, url_prefix="/forums")


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.isoformat()
    return dt.replace(tzinfo=None).isoformat()


def _parse_positive_int(value: str | None, default: int, *, minimum: int = 1) -> int:
    try:
        if value is None:
            return default
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


class ForumSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str] = None
    is_general: bool
    trail_id: Optional[int] = None
    trail_name: Optional[str] = None
    topics_count: int
    posts_count: int
    last_activity_at: Optional[str] = None

    @classmethod
    def from_stats(cls, stats):
        forum = stats.forum
        return cls(
            id=forum.id,
            slug=forum.slug,
            title=forum.title,
            description=forum.description,
            is_general=forum.is_general,
            trail_id=forum.trail_id,
            trail_name=stats.trail_name,
            topics_count=stats.topics_count,
            posts_count=stats.posts_count,
            last_activity_at=_isoformat(stats.last_activity_at),
        )


class ForumAuthor(BaseModel):
    user_id: int
    username: str
    profile_pic_url: Optional[str] = None

    @classmethod
    def from_user(cls, user):
        return cls(
            user_id=user.user_id,
            username=user.username,
            profile_pic_url=user.profile_pic_url,
        )


class TopicSummary(BaseModel):
    id: int
    forum_id: int
    title: str
    created_at: str
    updated_at: str
    author: Optional[ForumAuthor] = None
    posts_count: int
    last_post_at: Optional[str] = None

    @classmethod
    def from_stats(cls, stats):
        topic = stats.topic
        author = ForumAuthor.from_user(stats.author) if stats.author else None
        return cls(
            id=topic.id,
            forum_id=topic.forum_id,
            title=topic.title,
            created_at=_isoformat(topic.created_at) or "",
            updated_at=_isoformat(topic.updated_at) or "",
            author=author,
            posts_count=stats.posts_count,
            last_post_at=_isoformat(stats.last_post_at),
        )


class TopicDetail(BaseModel):
    id: int
    forum: ForumSummary
    title: str
    created_at: str
    updated_at: str
    author: Optional[ForumAuthor] = None
    posts_count: int
    last_post_at: Optional[str] = None

    @classmethod
    def from_stats(cls, topic_stats, forum_stats):
        topic = topic_stats.topic
        author = (
            ForumAuthor.from_user(topic_stats.author) if topic_stats.author else None
        )
        return cls(
            id=topic.id,
            forum=ForumSummary.from_stats(forum_stats),
            title=topic.title,
            created_at=_isoformat(topic.created_at) or "",
            updated_at=_isoformat(topic.updated_at) or "",
            author=author,
            posts_count=topic_stats.posts_count,
            last_post_at=_isoformat(topic_stats.last_post_at),
        )


class PostOut(BaseModel):
    id: int
    topic_id: int
    content: str
    created_at: str
    updated_at: str
    author: Optional[ForumAuthor] = None
    parent_post_id: Optional[int] = None
    replies: list["PostOut"] = Field(default_factory=list)

    @classmethod
    def from_row(cls, row):
        post = row.post
        author = ForumAuthor.from_user(row.author) if row.author else None
        replies = [cls.from_row(rep) for rep in row.replies]
        return cls(
            id=post.id,
            topic_id=post.topic_id,
            content=post.content,
            created_at=_isoformat(post.created_at) or "",
            updated_at=_isoformat(post.updated_at) or "",
            author=author,
            parent_post_id=post.parent_post_id,
            replies=replies,
        )

    @classmethod
    def from_model(cls, post, author):
        return cls(
            id=post.id,
            topic_id=post.topic_id,
            content=post.content,
            created_at=_isoformat(post.created_at) or "",
            updated_at=_isoformat(post.updated_at) or "",
            author=ForumAuthor.from_user(author) if author else None,
            parent_post_id=post.parent_post_id,
            replies=[],
        )


class CreateTopicIn(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("O título é obrigatório")
        return cleaned

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        cleaned = sanitize_user_html(value or "")
        if not cleaned:
            raise ValueError("A mensagem é obrigatória")
        return cleaned


class CreatePostIn(BaseModel):
    content: str
    parent_post_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        cleaned = sanitize_user_html(value or "")
        if not cleaned:
            raise ValueError("A mensagem é obrigatória")
        return cleaned


PostOut.model_rebuild()


def _pagination_payload(page: int, page_size: int, total: int) -> dict:
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {"page": page, "page_size": page_size, "total": total, "pages": pages}


@bp.get("/")
def list_forums():
    db = get_db()
    repo = ForumsRepository(db)
    stats = repo.list_forums_with_stats()
    payload = [ForumSummary.from_stats(item).model_dump(mode="json") for item in stats]
    db.commit()
    return jsonify({"forums": payload})


@bp.get("/<int:forum_id>")
def get_forum(forum_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    stats = repo.get_forum_with_stats(forum_id)
    if not stats:
        abort(404, description="Fórum não encontrado")
    db.commit()
    return jsonify(ForumSummary.from_stats(stats).model_dump(mode="json"))


@bp.get("/<int:forum_id>/topics")
def list_topics(forum_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    forum_stats = repo.get_forum_with_stats(forum_id)
    if not forum_stats:
        abort(404, description="Fórum não encontrado")

    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = min(_parse_positive_int(request.args.get("page_size"), 20), 100)
    offset = (page - 1) * page_size

    rows, total = repo.list_topics(forum_id, offset=offset, limit=page_size)
    payload = [TopicSummary.from_stats(row).model_dump(mode="json") for row in rows]
    db.commit()
    return jsonify(
        {
            "forum": ForumSummary.from_stats(forum_stats).model_dump(mode="json"),
            "topics": payload,
            "pagination": _pagination_payload(page, page_size, total),
        }
    )


@bp.post("/<int:forum_id>/topics")
def create_topic(forum_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    stats = repo.get_forum_with_stats(forum_id)
    if not stats:
        abort(404, description="Fórum não encontrado")

    try:
        payload = CreateTopicIn.model_validate_json(request.data or b"{}")
    except ValidationError as err:
        return jsonify({"detail": "Dados inválidos", "errors": err.errors()}), 400

    enforce_csrf()
    user = get_current_user()
    topic = repo.create_topic(
        forum_id=forum_id,
        title=payload.title,
        content=payload.content,
        author_id=user.user_id,
    )
    topic_stats = repo.get_topic_stats(topic.id)
    forum_stats = repo.get_forum_with_stats(forum_id)
    if not topic_stats or not forum_stats:
        db.rollback()
        abort(500, description="Erro ao preparar resposta do fórum")
    db.commit()
    return (
        jsonify(
            {
                "topic": TopicSummary.from_stats(topic_stats).model_dump(mode="json"),
                "forum": ForumSummary.from_stats(forum_stats).model_dump(mode="json"),
            }
        ),
        201,
    )


@bp.get("/topics/<int:topic_id>")
def get_topic(topic_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    result = repo.get_topic_with_forum(topic_id)
    if not result:
        abort(404, description="Tópico não encontrado")
    topic, forum_stats = result
    topic_stats = repo.get_topic_stats(topic_id)
    if not topic_stats:
        abort(404, description="Tópico não encontrado")
    db.commit()
    return jsonify(
        TopicDetail.from_stats(topic_stats, forum_stats).model_dump(mode="json")
    )


@bp.get("/topics/<int:topic_id>/posts")
def list_posts(topic_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    topic_result = repo.get_topic_with_forum(topic_id)
    if not topic_result:
        abort(404, description="Tópico não encontrado")
    topic, forum_stats = topic_result
    topic_stats = repo.get_topic_stats(topic_id)
    if not topic_stats:
        abort(404, description="Tópico não encontrado")

    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = min(_parse_positive_int(request.args.get("page_size"), 20), 100)
    offset = (page - 1) * page_size

    rows, total = repo.list_posts(topic_id, offset=offset, limit=page_size)
    payload = [PostOut.from_row(row).model_dump(mode="json") for row in rows]
    db.commit()
    return jsonify(
        {
            "topic": TopicDetail.from_stats(topic_stats, forum_stats).model_dump(
                mode="json"
            ),
            "posts": payload,
            "pagination": _pagination_payload(page, page_size, total),
        }
    )


@bp.post("/topics/<int:topic_id>/posts")
def create_post(topic_id: int):
    db = get_db()
    repo = ForumsRepository(db)
    topic_result = repo.get_topic_with_forum(topic_id)
    if not topic_result:
        abort(404, description="Tópico não encontrado")

    try:
        payload = CreatePostIn.model_validate_json(request.data or b"{}")
    except ValidationError as err:
        return jsonify({"detail": "Dados inválidos", "errors": err.errors()}), 400

    enforce_csrf()
    user = get_current_user()
    try:
        post = repo.create_post(
            topic_id=topic_id,
            content=payload.content,
            author_id=user.user_id,
            parent_post_id=payload.parent_post_id,
        )
    except ValueError as exc:
        if str(exc) == "parent_post_not_found":
            abort(400, description="Postagem resposta inválida")
        raise
    topic_stats = repo.get_topic_stats(topic_id)
    if not topic_stats:
        db.rollback()
        abort(500, description="Erro ao atualizar tópico")
    forum_stats = repo.get_forum_with_stats(topic_stats.topic.forum_id)
    if not forum_stats:
        db.rollback()
        abort(500, description="Erro ao atualizar fórum")
    db.commit()
    return (
        jsonify(
            {
                "post": PostOut.from_model(post, user).model_dump(mode="json"),
                "topic": TopicDetail.from_stats(topic_stats, forum_stats).model_dump(
                    mode="json"
                ),
                "forum": ForumSummary.from_stats(forum_stats).model_dump(mode="json"),
            }
        ),
        201,
    )
