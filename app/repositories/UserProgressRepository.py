from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM
from app.models.trail_items import TrailItems as TrailItemsORM

from app.models.lk_progress_status import LkProgressStatus
from app.repositories.UserTrailsRepository import UserTrailsRepository


class UserProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def _status_id(self, code: str) -> int:
        return (
            self.db.query(LkProgressStatus.id)
            .filter(LkProgressStatusORM.code == code)
            .scalar()
        )

    def upsert_item_progress(
        self,
        user_id: int,
        item_id: int,
        status_code: str,
        progress_value: int | None = None,
        *,
        last_passed_submission_id: Optional[int] = None,
    ):
        status_id = self._status_id(status_code)
        completed_status_id = self._status_id("COMPLETED")
        uip = (
            self.db.query(UserItemProgressORM)
            .filter(
                UserItemProgressORM.user_id == user_id,
                UserItemProgressORM.trail_item_id == item_id,
            )
            .first()
        )
        if not uip:
            uip = UserItemProgressORM(
                user_id=user_id,
                trail_item_id=item_id,
            )
            self.db.add(uip)

        if uip.status_id == completed_status_id and status_code != "COMPLETED":
            status_code = "COMPLETED"
            status_id = completed_status_id
        else:
            uip.status_id = status_id

        if progress_value is not None:
            prev_value = uip.progress_value or 0
            uip.progress_value = max(prev_value, max(0, progress_value))
        if last_passed_submission_id is not None:
            uip.last_passed_submission_id = last_passed_submission_id

        now_expr = func.now()
        uip.last_interaction = now_expr
        uip.last_interaction_utc = now_expr

        if status_code == "COMPLETED":
            uip.completed_at = now_expr
            uip.completed_at_utc = now_expr
        elif uip.status_id != completed_status_id:
            uip.completed_at = None
            uip.completed_at_utc = None

        self.db.flush()

        trail_id = (
            self.db.query(TrailItemsORM.trail_id)
            .filter(TrailItemsORM.id == item_id)
            .scalar()
        )
        if trail_id is not None:
            UserTrailsRepository(self.db).sync_user_trail_progress(user_id, trail_id)

        self.db.commit()
        return uip
