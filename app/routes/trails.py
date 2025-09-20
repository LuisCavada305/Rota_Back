from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.TrailsRepository import TrailsRepository

import jwt
from app.core.settings import settings
from app.models.users import User
from app.models.trail_items import TrailItems as TrailItemsORM
from app.repositories.UserTrailsRepository import UserTrailsRepository
from typing import Literal
from app.routes.me import get_current_user_id
from app.services.security import get_current_user

from app.repositories.UserProgressRepository import UserProgressRepository

router = APIRouter(prefix="/trails", tags=["trails"])

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


# ===== Endpoints existentes =====


@router.get("/showcase", response_model=Dict[str, List[TrailOut]])
def get_trails_showcase(db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    trails = repo.list_showcase()
    return {
        "trails": [TrailOut.model_validate(t, from_attributes=True) for t in trails]
    }


@router.get("/", response_model=Dict[str, List[TrailOut]])
def get_trails(db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    trails = repo.list_all()
    return {
        "trails": [TrailOut.model_validate(t, from_attributes=True) for t in trails]
    }


# ===== Novos =====


@router.get("/{trail_id}", response_model=TrailOut)
def get_trail(trail_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    t = repo.get_trail(trail_id)
    if not t:
        raise HTTPException(404, "Trail not found")
    return TrailOut.model_validate(t, from_attributes=True)


@router.get("/{trail_id}/sections", response_model=List[SectionOut])
def get_sections(trail_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    secs = repo.list_sections(trail_id)
    return [SectionOut.model_validate(s, from_attributes=True) for s in secs]


@router.get("/{trail_id}/sections/{section_id}/items", response_model=List[ItemOut])
def get_section_items(trail_id: int, section_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    items = repo.list_section_items(trail_id, section_id)
    return [
        ItemOut(
            id=i.id,
            title=i.title or "",
            duration_seconds=i.duration_seconds,
            order_index=i.order_index,
            type=(i.item_type.code if i.item_type else None),
        )
        for i in items
    ]


@router.get("/{trail_id}/sections-with-items", response_model=List[SectionWithItemsOut])
def get_sections_with_items(trail_id: int, db: Session = Depends(get_db)):
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
                        type=(i.item_type.code if i.item_type else None),
                    )
                    for i in s.items
                ],
            )
        )
    return out


@router.get("/{trail_id}/included-items", response_model=List[TextValOut])
def get_included_items(trail_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    rows = repo.list_included_items(trail_id)
    return [TextValOut(text_val=r.text_val) for r in rows]


@router.get("/{trail_id}/requirements", response_model=List[TextValOut])
def get_requirements(trail_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    rows = repo.list_requirements(trail_id)
    return [TextValOut(text_val=r.text_val) for r in rows]


@router.get("/{trail_id}/audience", response_model=List[TextValOut])
def get_audience(trail_id: int, db: Session = Depends(get_db)):
    repo = TrailsRepository(db)
    rows = repo.list_audience(trail_id)
    return [TextValOut(text_val=r.text_val) for r in rows]


# opcional (placeholder)
@router.get("/{trail_id}/learn", response_model=List[TextValOut])
def get_learn(trail_id: int):
    return []


# PUT /trails/{trail_id}/items/{item_id}/progress
class ItemProgressIn(BaseModel):
    status: Literal["IN_PROGRESS", "COMPLETED"]
    progress_value: int | None = None  # % ou segundos, escolha um padrão


@router.put("/trails/{trail_id}/items/{item_id}/progress")
def set_item_progress(
    trail_id: int,
    item_id: int,
    body: ItemProgressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # valida item ↔ trilha
    item = db.query(TrailItemsORM).filter_by(id=item_id, trail_id=trail_id).first()
    if not item:
        raise HTTPException(404, "Item não encontrado na trilha")

    UserTrailsRepository(db).ensure_enrollment(user.id, trail_id)
    UserProgressRepository(db).upsert_item_progress(
        user.id, item_id, body.status, body.progress_value
    )
    return {"ok": True}
