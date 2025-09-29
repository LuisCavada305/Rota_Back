from __future__ import annotations

from typing import List, Optional, Literal

from flask import Blueprint, jsonify, abort, request
from pydantic import BaseModel, ValidationError

from app.core.db import get_db
from app.models.trail_items import TrailItems as TrailItemsORM
from app.repositories.TrailsRepository import TrailsRepository
from app.repositories.UserProgressRepository import UserProgressRepository
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.services.security import get_current_user, enforce_csrf


bp = Blueprint("trails", __name__, url_prefix="/trails")

# ===== Schemas =====


class TrailOut(BaseModel):
    id: int
    name: str
    thumbnail_url: str
    author: Optional[str] = None
    review: Optional[float] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ItemOut(BaseModel):
    id: int
    title: str
    duration_seconds: Optional[int] = None
    order_index: Optional[int] = 0
    type: Optional[str] = None

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    id: int
    title: str
    order_index: Optional[int] = 0

    class Config:
        from_attributes = True


class SectionWithItemsOut(SectionOut):
    items: List[ItemOut]


class TextValOut(BaseModel):
    text_val: str


def _parse_positive_int(value: str | None, default: int, *, minimum: int = 1) -> int:
    try:
        if value is None:
            return default
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def _build_pagination_metadata(page: int, page_size: int, total: int) -> dict:
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }


@bp.get("/showcase")
def get_trails_showcase():
    db = get_db()
    repo = TrailsRepository(db)
    trails = repo.list_showcase()
    data = [
        TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
        for t in trails
    ]
    return jsonify({"trails": data})


@bp.get("/")
def get_trails():
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 10)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    trails, total = repo.list_all(offset=offset, limit=page_size)
    data = [
        TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
        for t in trails
    ]
    return jsonify({
        "trails": data,
        "pagination": _build_pagination_metadata(page, page_size, total),
    })


@bp.get("/<int:trail_id>")
def get_trail(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    t = repo.get_trail(trail_id)
    if not t:
        abort(404, description="Trail not found")
    data = TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
    return jsonify(data)


@bp.get("/<int:trail_id>/sections")
def get_sections(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 20)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    secs, total = repo.list_sections(trail_id, offset=offset, limit=page_size)
    data = [
        SectionOut.model_validate(s, from_attributes=True).model_dump(mode="json")
        for s in secs
    ]
    return jsonify({
        "sections": data,
        "pagination": _build_pagination_metadata(page, page_size, total),
    })


@bp.get("/<int:trail_id>/sections/<int:section_id>/items")
def get_section_items(trail_id: int, section_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 25)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    items, total = repo.list_section_items(
        trail_id, section_id, offset=offset, limit=page_size
    )
    data = [
        ItemOut(
            id=i.id,
            title=i.title or "",
            duration_seconds=i.duration_seconds,
            order_index=i.order_index,
            type=(i.type.code if i.type else None),
        ).model_dump(mode="json")
        for i in items
    ]
    return jsonify(
        {
            "items": data,
            "pagination": _build_pagination_metadata(page, page_size, total),
        }
    )


@bp.get("/<int:trail_id>/sections-with-items")
def get_sections_with_items(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    secs = repo.list_sections_with_items(trail_id)
    out: List[SectionWithItemsOut] = []
    for s in secs:
        out.append(
            SectionWithItemsOut(
                id=s.id,
                title=s.title,
                order_index=s.order_index,
                items=[
                    ItemOut(
                        id=i.id,
                        title=i.title or "",
                        duration_seconds=i.duration_seconds,
                        order_index=i.order_index,
                        type=(i.type.code if i.type else None),
                    )
                    for i in s.items
                ],
            )
        )
    data = [section.model_dump(mode="json") for section in out]
    return jsonify(data)


@bp.get("/<int:trail_id>/included-items")
def get_included_items(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_included_items(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/requirements")
def get_requirements(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_requirements(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/audience")
def get_audience(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_audience(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/learn")
def get_learn(trail_id: int):
    _ = trail_id
    return jsonify([])


class ItemProgressIn(BaseModel):
    status: Literal["IN_PROGRESS", "COMPLETED"]
    progress_value: int | None = None  # % ou segundos, escolha um padrão


@bp.put("/<int:trail_id>/items/<int:item_id>/progress")
def set_item_progress(trail_id: int, item_id: int):
    data = request.get_json(silent=True) or {}
    try:
        body = ItemProgressIn.model_validate(data)
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

    enforce_csrf()
    user = get_current_user()
    db = get_db()

    item = db.query(TrailItemsORM).filter_by(id=item_id, trail_id=trail_id).first()
    if not item:
        abort(404, description="Item não encontrado na trilha")

    UserTrailsRepository(db).ensure_enrollment(user.user_id, trail_id)
    UserProgressRepository(db).upsert_item_progress(
        user.user_id, item_id, body.status, body.progress_value
    )
    return jsonify({"ok": True})
