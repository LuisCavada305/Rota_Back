from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import Optional
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM

from app.models.lk_progress_status import LkProgressStatus


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
    ):
        status_id = self._status_id(status_code)
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

        uip.status_id = status_id
        if progress_value is not None:
            uip.progress_value = progress_value
        if status_code == "COMPLETED":
            uip.completed_at = func.now()

        self.db.commit()
        return uip
