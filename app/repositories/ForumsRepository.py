from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.forums import (
    Forum as ForumORM,
    ForumTopic as ForumTopicORM,
    ForumPost as ForumPostORM,
    GENERAL_FORUM_SLUG,
    make_trail_forum_slug,
)
from app.models.trails import Trails as TrailsORM
from app.models.users import User as UserORM


@dataclass(slots=True)
class ForumStats:
    forum: ForumORM
    trail_name: Optional[str]
    topics_count: int
    posts_count: int
    last_activity_at: Optional[datetime]


@dataclass(slots=True)
class TopicStats:
    topic: ForumTopicORM
    author: Optional[UserORM]
    posts_count: int
    last_post_at: Optional[datetime]


@dataclass(slots=True)
class PostWithAuthor:
    post: ForumPostORM
    author: Optional[UserORM]
    replies: List["PostWithAuthor"]


class ForumsRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- bootstrap helpers -------------------------------------------------
    def ensure_general_forum(self) -> ForumORM:
        forum = self.db.query(ForumORM).filter(ForumORM.is_general.is_(True)).first()
        if forum:
            return forum

        forum = ForumORM(
            slug=GENERAL_FORUM_SLUG,
            title="Fórum Geral",
            description="Espaço para conversas gerais da comunidade ROTA.",
            is_general=True,
        )
        self.db.add(forum)
        self.db.flush()
        return forum

    def ensure_trail_forums(self) -> None:
        missing_trails = (
            self.db.query(TrailsORM)
            .outerjoin(ForumORM, ForumORM.trail_id == TrailsORM.id)
            .filter(ForumORM.id.is_(None))
            .all()
        )
        if not missing_trails:
            return

        for trail in missing_trails:
            forum = ForumORM(
                slug=make_trail_forum_slug(trail.id),
                title=trail.name,
                description=f"Discussões sobre {trail.name}",
                trail_id=trail.id,
                is_general=False,
            )
            self.db.add(forum)
        self.db.flush()

    def ensure_bootstrap(self) -> ForumORM:
        general = self.ensure_general_forum()
        self.ensure_trail_forums()
        return general

    # --- queries -----------------------------------------------------------
    def list_forums_with_stats(self) -> List[ForumStats]:
        self.ensure_bootstrap()

        topics_count_sq = (
            self.db.query(func.count(ForumTopicORM.id))
            .filter(ForumTopicORM.forum_id == ForumORM.id)
            .correlate(ForumORM)
            .scalar_subquery()
        )
        posts_count_sq = (
            self.db.query(func.count(ForumPostORM.id))
            .join(ForumTopicORM, ForumTopicORM.id == ForumPostORM.topic_id)
            .filter(ForumTopicORM.forum_id == ForumORM.id)
            .correlate(ForumORM)
            .scalar_subquery()
        )
        last_activity_sq = (
            self.db.query(func.max(ForumPostORM.created_at))
            .join(ForumTopicORM, ForumTopicORM.id == ForumPostORM.topic_id)
            .filter(ForumTopicORM.forum_id == ForumORM.id)
            .correlate(ForumORM)
            .scalar_subquery()
        )

        rows = (
            self.db.query(
                ForumORM,
                TrailsORM.name.label("trail_name"),
                topics_count_sq.label("topics_count"),
                posts_count_sq.label("posts_count"),
                last_activity_sq.label("last_activity_at"),
            )
            .outerjoin(TrailsORM, TrailsORM.id == ForumORM.trail_id)
            .order_by(ForumORM.is_general.desc(), ForumORM.title.asc())
            .all()
        )

        return [
            ForumStats(
                forum=row[0],
                trail_name=row[1],
                topics_count=row[2] or 0,
                posts_count=row[3] or 0,
                last_activity_at=row[4] or row[0].updated_at,
            )
            for row in rows
        ]

    def get_forum_with_stats(self, forum_id: int) -> Optional[ForumStats]:
        self.ensure_bootstrap()
        topics_count_sq = (
            self.db.query(func.count(ForumTopicORM.id))
            .filter(ForumTopicORM.forum_id == forum_id)
            .scalar_subquery()
        )
        posts_count_sq = (
            self.db.query(func.count(ForumPostORM.id))
            .join(ForumTopicORM, ForumTopicORM.id == ForumPostORM.topic_id)
            .filter(ForumTopicORM.forum_id == forum_id)
            .scalar_subquery()
        )
        last_activity_sq = (
            self.db.query(func.max(ForumPostORM.created_at))
            .join(ForumTopicORM, ForumTopicORM.id == ForumPostORM.topic_id)
            .filter(ForumTopicORM.forum_id == forum_id)
            .scalar_subquery()
        )

        row = (
            self.db.query(
                ForumORM,
                TrailsORM.name.label("trail_name"),
                topics_count_sq.label("topics_count"),
                posts_count_sq.label("posts_count"),
                last_activity_sq.label("last_activity_at"),
            )
            .outerjoin(TrailsORM, TrailsORM.id == ForumORM.trail_id)
            .filter(ForumORM.id == forum_id)
            .first()
        )
        if not row:
            return None
        forum, trail_name, topics_count, posts_count, last_activity = row
        return ForumStats(
            forum=forum,
            trail_name=trail_name,
            topics_count=topics_count or 0,
            posts_count=posts_count or 0,
            last_activity_at=last_activity or forum.updated_at,
        )

    def list_topics(
        self, forum_id: int, *, offset: int, limit: int
    ) -> Tuple[List[TopicStats], int]:
        posts_count_sq = (
            self.db.query(func.count(ForumPostORM.id))
            .filter(ForumPostORM.topic_id == ForumTopicORM.id)
            .correlate(ForumTopicORM)
            .scalar_subquery()
        )
        last_post_sq = (
            self.db.query(func.max(ForumPostORM.created_at))
            .filter(ForumPostORM.topic_id == ForumTopicORM.id)
            .correlate(ForumTopicORM)
            .scalar_subquery()
        )

        query = (
            self.db.query(
                ForumTopicORM,
                UserORM,
                posts_count_sq.label("posts_count"),
                last_post_sq.label("last_post_at"),
            )
            .outerjoin(UserORM, UserORM.user_id == ForumTopicORM.created_by_id)
            .filter(ForumTopicORM.forum_id == forum_id)
        )

        total = query.count()
        order_clause = func.coalesce(last_post_sq, ForumTopicORM.updated_at).desc()
        rows = (
            query.order_by(order_clause, ForumTopicORM.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        payload = [
            TopicStats(
                topic=row[0],
                author=row[1],
                posts_count=row[2] or 0,
                last_post_at=row[3] or row[0].updated_at,
            )
            for row in rows
        ]
        return payload, total

    def get_topic_with_forum(
        self, topic_id: int
    ) -> Optional[Tuple[ForumTopicORM, ForumStats]]:
        topic_row = (
            self.db.query(ForumTopicORM).filter(ForumTopicORM.id == topic_id).first()
        )
        if not topic_row:
            return None
        forum_stats = self.get_forum_with_stats(topic_row.forum_id)
        if not forum_stats:
            return None
        return topic_row, forum_stats

    def get_topic_stats(self, topic_id: int) -> Optional[TopicStats]:
        posts_count_sq = (
            self.db.query(func.count(ForumPostORM.id))
            .filter(ForumPostORM.topic_id == topic_id)
            .scalar_subquery()
        )
        last_post_sq = (
            self.db.query(func.max(ForumPostORM.created_at))
            .filter(ForumPostORM.topic_id == topic_id)
            .scalar_subquery()
        )

        row = (
            self.db.query(
                ForumTopicORM,
                UserORM,
                posts_count_sq.label("posts_count"),
                last_post_sq.label("last_post_at"),
            )
            .outerjoin(UserORM, UserORM.user_id == ForumTopicORM.created_by_id)
            .filter(ForumTopicORM.id == topic_id)
            .first()
        )
        if not row:
            return None
        topic, author, posts_count, last_post_at = row
        return TopicStats(
            topic=topic,
            author=author,
            posts_count=posts_count or 0,
            last_post_at=last_post_at or topic.updated_at,
        )

    def list_posts(
        self, topic_id: int, *, offset: int, limit: int
    ) -> Tuple[List[PostWithAuthor], int]:
        query = (
            self.db.query(ForumPostORM, UserORM)
            .outerjoin(UserORM, UserORM.user_id == ForumPostORM.author_id)
            .filter(ForumPostORM.topic_id == topic_id)
        )
        total = query.count()
        rows = (
            query.order_by(ForumPostORM.created_at.asc(), ForumPostORM.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        by_id: Dict[int, PostWithAuthor] = {}
        roots: List[PostWithAuthor] = []

        for post, author in rows:
            node = PostWithAuthor(post=post, author=author, replies=[])
            by_id[post.id] = node

        for post, _author in rows:
            node = by_id[post.id]
            if post.parent_post_id and post.parent_post_id in by_id:
                parent = by_id[post.parent_post_id]
                parent.replies.append(node)
            else:
                roots.append(node)

        return roots, total

    # --- mutations --------------------------------------------------------
    def create_topic(
        self, *, forum_id: int, title: str, content: str, author_id: Optional[int]
    ) -> ForumTopicORM:
        topic = ForumTopicORM(
            forum_id=forum_id,
            title=title,
            created_by_id=author_id,
        )
        self.db.add(topic)
        self.db.flush()

        post = ForumPostORM(
            topic_id=topic.id,
            author_id=author_id,
            content=content,
        )
        self.db.add(post)
        self.db.flush()

        now_expr = func.now()
        topic.updated_at = now_expr
        self.db.query(ForumORM).filter(ForumORM.id == forum_id).update(
            {ForumORM.updated_at: now_expr}, synchronize_session=False
        )
        return topic

    def create_post(
        self,
        *,
        topic_id: int,
        content: str,
        author_id: Optional[int],
        parent_post_id: Optional[int] = None,
    ) -> ForumPostORM:
        if parent_post_id is not None:
            parent = (
                self.db.query(ForumPostORM)
                .filter(
                    ForumPostORM.id == parent_post_id,
                    ForumPostORM.topic_id == topic_id,
                )
                .first()
            )
            if not parent:
                raise ValueError("parent_post_not_found")
        post = ForumPostORM(
            topic_id=topic_id,
            author_id=author_id,
            parent_post_id=parent_post_id,
            content=content,
        )
        self.db.add(post)
        self.db.flush()

        now_expr = func.now()
        forum_id = (
            self.db.query(ForumTopicORM.forum_id)
            .filter(ForumTopicORM.id == topic_id)
            .scalar()
        )
        self.db.query(ForumTopicORM).filter(ForumTopicORM.id == topic_id).update(
            {ForumTopicORM.updated_at: now_expr}, synchronize_session=False
        )
        if forum_id:
            self.db.query(ForumORM).filter(ForumORM.id == forum_id).update(
                {ForumORM.updated_at: now_expr}, synchronize_session=False
            )
        return post
