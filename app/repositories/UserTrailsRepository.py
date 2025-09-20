from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user_trails import UserTrails as UserTrailsORM
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM

def _current_user_id() -> Optional[int]:
    # TODO: troque pelo seu mecanismo de auth
    return 1

class UserTrailsRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_items_in_trail(self, trail_id: int) -> int:
        return (
            self.db.query(func.count(TrailItemsORM.id))
            .filter(TrailItemsORM.trail_id == trail_id)
            .scalar() or 0
        )

    def _done_items(self, user_id: int, trail_id: int) -> int:
        return (
            self.db.query(func.count(UserItemProgressORM.id))
            .join(TrailItemsORM, TrailItemsORM.id == UserItemProgressORM.trail_item_id)
            .join(LkProgressStatusORM, LkProgressStatusORM.id == UserItemProgressORM.status_id)
            .filter(
                UserItemProgressORM.user_id == user_id,
                TrailItemsORM.trail_id == trail_id,
                LkProgressStatusORM.code == "COMPLETED",
            )
            .scalar() or 0
        )

    def get_progress_for_current_user(self, trail_id: int) -> Optional[Dict[str, Any]]:
        user_id = _current_user_id()
        if not user_id:
            return None

        ut = (
            self.db.query(UserTrailsORM)
            .filter(UserTrailsORM.user_id == user_id, UserTrailsORM.trail_id == trail_id)
            .first()
        )

        total = self.count_items_in_trail(trail_id)
        done = self._done_items(user_id, trail_id)
        pct = round(100.0 * done / total, 2) if total > 0 else 0.0

        enrolledAt = ut.started_at.isoformat() if ut and ut.started_at else None
        nextAction = "Continue a Estudar" if done > 0 else "Começar"

        return {
            "done": done,
            "total": total,
            "computed_progress_percent": pct,
            "nextAction": nextAction,
            "enrolledAt": enrolledAt,
        }
