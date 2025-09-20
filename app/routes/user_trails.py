from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.UserTrailsRepository import UserTrailsRepository

router = APIRouter(prefix="/user-trails", tags=["user-trails"])


class ProgressOut(BaseModel):
    done: int
    total: int
    computed_progress_percent: Optional[float] = None
    nextAction: Optional[str] = None
    enrolledAt: Optional[str] = None


@router.get("/{trail_id}/progress", response_model=ProgressOut)
def get_progress(trail_id: int, db: Session = Depends(get_db)):
    repo = UserTrailsRepository(db)
    data = repo.get_progress_for_current_user(trail_id)
    if not data:
        total = repo.count_items_in_trail(trail_id)
        return ProgressOut(
            done=0, total=total, computed_progress_percent=0.0, nextAction="Começar"
        )
    return ProgressOut(**data)
