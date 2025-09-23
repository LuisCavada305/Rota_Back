# app/routes/trail_items.py
from __future__ import annotations

from typing import Optional, Literal

from flask import Blueprint, jsonify, abort
from pydantic import BaseModel

from app.core.db import get_db
from app.models.trail_items import TrailItems as TrailItemsORM


bp = Blueprint("trail_items", __name__, url_prefix="/trails")


class TrailItemDetailOut(BaseModel):
    id: int
    trail_id: int
    section_id: Optional[int] = None
    title: str
    type: Literal["VIDEO", "DOC", "FORM"]
    youtubeId: str
    duration_seconds: Optional[int] = None
    required_percentage: int = 70
    description_html: str = ""
    prev_item_id: Optional[int] = None
    next_item_id: Optional[int] = None


def _extract_youtube_id(url: str) -> str:
    # aceita formatos: watch?v=, youtu.be/, /embed/, /shorts/
    import re

    if not url:
        return ""
    m = re.search(r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else ""


@bp.get("/<int:trail_id>/items/<int:item_id>")
def get_item_detail(trail_id: int, item_id: int):
    db = get_db()
    # 1) Carrega o item garantindo que pertence à trilha
    item = (
        db.query(TrailItemsORM)
        .filter(TrailItemsORM.id == item_id, TrailItemsORM.trail_id == trail_id)
        .first()
    )
    if not item:
        abort(404, description="Item não encontrado")

    # 2) Extrai youtubeId apenas se type == VIDEO
    url = item.url or ""
    item_type = item.type.code if item.type is not None else "DOC"
    youtube_id = _extract_youtube_id(url) if item_type == "VIDEO" else ""

    # 3) Calcula prev/next
    prev_id: Optional[int] = None
    next_id: Optional[int] = None

    # Se tiver seção: navega por section_id + order_index
    if item.section_id is not None:
        # PREV: menor order_index que o atual, ordem desc (tie-break por id)
        prev_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == item.section_id,
                TrailItemsORM.order_index < (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.desc(), TrailItemsORM.id.desc())
            .first()
        )
        if prev_row:
            prev_id = prev_row[0]

        # NEXT: maior order_index que o atual, ordem asc (tie-break por id)
        next_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == item.section_id,
                TrailItemsORM.order_index > (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.asc(), TrailItemsORM.id.asc())
            .first()
        )
        if next_row:
            next_id = next_row[0]
    else:
        # Sem seção (usa índice da trilha)
        prev_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id.is_(None),
                TrailItemsORM.order_index < (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.desc(), TrailItemsORM.id.desc())
            .first()
        )
        if prev_row:
            prev_id = prev_row[0]

        next_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id.is_(None),
                TrailItemsORM.order_index > (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.asc(), TrailItemsORM.id.asc())
            .first()
        )
        if next_row:
            next_id = next_row[0]

    data = TrailItemDetailOut(
        id=item.id,
        trail_id=item.trail_id,
        section_id=item.section_id,
        title=item.title or "",
        type=item_type,  # "VIDEO" | "DOC" | "FORM"
        youtubeId=youtube_id,
        duration_seconds=item.duration_seconds,
        required_percentage=70,  # seu schema não tem esse campo; mantendo padrão
        description_html="",  # idem
        prev_item_id=prev_id,
        next_item_id=next_id,
    ).model_dump(mode="json")
    return jsonify(data)
