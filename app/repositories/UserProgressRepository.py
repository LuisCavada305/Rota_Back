from sqlalchemy.orm import Session
from sqlalchemy import text
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
        sanitized_progress = (
            max(0, progress_value) if progress_value is not None else None
        )
        progress_update_flag = sanitized_progress is not None
        last_passed_update_flag = last_passed_submission_id is not None

        sanitized_progress = (
            max(0, progress_value) if progress_value is not None else None
        )

        now_sql = text("SELECT now(), now()")
        now_result = self.db.execute(now_sql).one()
        current_now = now_result[0]
        current_now_utc = now_result[1]

        update_sql = text(
            """
            UPDATE user_item_progress
            SET
                status_id = CASE
                    WHEN user_item_progress.status_id = :completed_status_id
                        THEN user_item_progress.status_id
                    ELSE :status_id
                END,
                progress_value = CASE
                    WHEN :update_progress
                        THEN GREATEST(
                            COALESCE(user_item_progress.progress_value, 0),
                            :sanitized_progress_value
                        )
                    ELSE user_item_progress.progress_value
                END,
                last_passed_submission_id = CASE
                    WHEN :update_last_passed
                        THEN :last_passed_submission_id
                    ELSE user_item_progress.last_passed_submission_id
                END,
                last_interaction = :current_now,
                last_interaction_utc = :current_now_utc,
                completed_at = CASE
                    WHEN user_item_progress.status_id = :completed_status_id
                        THEN user_item_progress.completed_at
                    WHEN :status_id = :completed_status_id
                        THEN :current_now
                    ELSE NULL
                END,
                completed_at_utc = CASE
                    WHEN user_item_progress.status_id = :completed_status_id
                        THEN user_item_progress.completed_at_utc
                    WHEN :status_id = :completed_status_id
                        THEN :current_now_utc
                    ELSE NULL
                END
            WHERE user_item_progress.user_id = :user_id
              AND user_item_progress.trail_item_id = :trail_item_id
            RETURNING id
            """
        )

        update_params = {
            "user_id": user_id,
            "trail_item_id": item_id,
            "status_id": status_id,
            "completed_status_id": completed_status_id,
            "update_progress": sanitized_progress is not None,
            "sanitized_progress_value": (
                sanitized_progress if sanitized_progress is not None else 0
            ),
            "update_last_passed": last_passed_submission_id is not None,
            "last_passed_submission_id": last_passed_submission_id,
            "current_now": current_now,
            "current_now_utc": current_now_utc,
        }

        result = self.db.execute(update_sql, update_params)
        uip_id = result.scalar_one_or_none()

        if uip_id is None:
            insert_sql = text(
                """
                INSERT INTO user_item_progress (
                    user_id,
                    trail_item_id,
                    status_id,
                    progress_value,
                    last_interaction,
                    completed_at,
                    last_interaction_utc,
                    completed_at_utc,
                    last_passed_submission_id
                )
                VALUES (
                    :user_id,
                    :trail_item_id,
                    :status_id,
                    :insert_progress_value,
                    :current_now,
                    CASE WHEN :status_id = :completed_status_id THEN :current_now ELSE NULL END,
                    :current_now_utc,
                    CASE WHEN :status_id = :completed_status_id THEN :current_now_utc ELSE NULL END,
                    :insert_last_passed_submission_id
                )
                ON CONFLICT (user_id, trail_item_id) DO NOTHING
                RETURNING id
                """
            )

            insert_params = {
                "user_id": user_id,
                "trail_item_id": item_id,
                "status_id": status_id,
                "completed_status_id": completed_status_id,
                "insert_progress_value": (
                    sanitized_progress if sanitized_progress is not None else None
                ),
                "insert_last_passed_submission_id": last_passed_submission_id,
                "current_now": current_now,
                "current_now_utc": current_now_utc,
            }

            insert_result = self.db.execute(insert_sql, insert_params)
            uip_id = insert_result.scalar_one_or_none()

            if uip_id is None:
                result = self.db.execute(update_sql, update_params)
                uip_id = result.scalar_one()

        uip = self.db.get(UserItemProgressORM, uip_id)

        trail_id = (
            self.db.query(TrailItemsORM.trail_id)
            .filter(TrailItemsORM.id == item_id)
            .scalar()
        )
        if trail_id is not None:
            UserTrailsRepository(self.db).sync_user_trail_progress(user_id, trail_id)

        self.db.commit()
        return uip
