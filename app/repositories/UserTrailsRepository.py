from typing import Optional, Dict, Any, List, Iterable
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case

from app.models.user_trails import UserTrails as UserTrailsORM
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM
from app.models.lk_enrollment_status import LkEnrollmentStatus as LkEnrollmentStatusORM

from app.services.security import get_current_user_id


class UserTrailsRepository:
    def __init__(self, db: Session):
        self.db = db

    def _progress_status_id(self, code: str) -> Optional[int]:
        return (
            self.db.query(LkProgressStatusORM.id)
            .filter(LkProgressStatusORM.code == code)
            .scalar()
        )

    def _enrollment_status_id(self, code: str) -> Optional[int]:
        return (
            self.db.query(LkEnrollmentStatusORM.id)
            .filter(LkEnrollmentStatusORM.code == code)
            .scalar()
        )

    def count_items_in_trail(self, trail_id: int) -> int:
        return (
            self.db.query(func.count(TrailItemsORM.id))
            .filter(TrailItemsORM.trail_id == trail_id)
            .scalar()
            or 0
        )

    def get_progress_for_current_user(self, trail_id: int) -> Optional[Dict[str, Any]]:
        user_id = get_current_user_id()
        if not user_id:
            return None
        self.ensure_enrollment(user_id, trail_id)
        return self.get_progress_for_user(user_id, trail_id)

    def get_progress_for_user(
        self, user_id: int, trail_id: int
    ) -> Optional[Dict[str, Any]]:
        progress_map = self.get_progress_map_for_user(
            user_id, [trail_id], sync=True
        )
        return progress_map.get(trail_id)

    def ensure_enrollment(self, user_id: int, trail_id: int):
        ut = (
            self.db.query(UserTrailsORM)
            .filter(
                UserTrailsORM.user_id == user_id, UserTrailsORM.trail_id == trail_id
            )
            .first()
        )
        if not ut:
            status_id = self._enrollment_status_id("ENROLLED")
            ut = UserTrailsORM(
                user_id=user_id,
                trail_id=trail_id,
                started_at=func.now(),
                status_id=status_id,
                progress_percent=0,
            )
            self.db.add(ut)
            self.db.commit()
        return ut

    def _done_items(self, user_id: int, trail_id: int) -> int:
        return (
            self.db.query(func.count(UserItemProgressORM.id))
            .join(TrailItemsORM, TrailItemsORM.id == UserItemProgressORM.trail_item_id)
            .join(
                LkProgressStatusORM,
                LkProgressStatusORM.id == UserItemProgressORM.status_id,
            )
            .filter(
                UserItemProgressORM.user_id == user_id,
                TrailItemsORM.trail_id == trail_id,
                LkProgressStatusORM.code == "COMPLETED",
            )
            .scalar()
            or 0
        )

    def sync_user_trail_progress(self, user_id: int, trail_id: int):
        ut = (
            self.db.query(UserTrailsORM)
            .filter(
                UserTrailsORM.user_id == user_id, UserTrailsORM.trail_id == trail_id
            )
            .first()
        )
        if not ut:
            return

        total = self.count_items_in_trail(trail_id)
        done = self._done_items(user_id, trail_id)
        pct = round(100.0 * done / total, 2) if total > 0 else 0.0

        ut.progress_percent = pct

        completed_status_id = self._enrollment_status_id("COMPLETED")
        in_progress_status_id = self._enrollment_status_id("IN_PROGRESS")
        enrolled_status_id = self._enrollment_status_id("ENROLLED")

        if total > 0 and done >= total:
            if completed_status_id:
                ut.status_id = completed_status_id
            ut.completed_at = func.now()
            ut.completed_at_utc = None
        elif done > 0:
            if in_progress_status_id:
                ut.status_id = in_progress_status_id
            ut.completed_at = None
            ut.completed_at_utc = None
        else:
            if enrolled_status_id:
                ut.status_id = enrolled_status_id
            ut.completed_at = None
            ut.completed_at_utc = None

        self.db.flush()

    def _count_items_for_trails(self, trail_ids: Iterable[int]) -> Dict[int, int]:
        ids = list({int(tid) for tid in trail_ids})
        if not ids:
            return {}
        rows = (
            self.db.query(
                TrailItemsORM.trail_id,
                func.count(TrailItemsORM.id).label("total"),
            )
            .filter(TrailItemsORM.trail_id.in_(ids))
            .group_by(TrailItemsORM.trail_id)
            .all()
        )
        return {trail_id: total for trail_id, total in rows}

    def _done_items_for_trails(
        self, user_id: int, trail_ids: Iterable[int]
    ) -> Dict[int, int]:
        ids = list({int(tid) for tid in trail_ids})
        if not ids:
            return {}
        completed_status_id = self._progress_status_id("COMPLETED")
        if not completed_status_id:
            return {}

        rows = (
            self.db.query(
                TrailItemsORM.trail_id,
                func.count(UserItemProgressORM.id).label("done"),
            )
            .join(
                UserItemProgressORM,
                (UserItemProgressORM.trail_item_id == TrailItemsORM.id)
                & (UserItemProgressORM.user_id == user_id),
            )
            .filter(
                TrailItemsORM.trail_id.in_(ids),
                UserItemProgressORM.status_id == completed_status_id,
            )
            .group_by(TrailItemsORM.trail_id)
            .all()
        )
        return {trail_id: done for trail_id, done in rows}

    def get_progress_map_for_user(
        self, user_id: int, trail_ids: Iterable[int], *, sync: bool = False
    ) -> Dict[int, Dict[str, Any]]:
        ids = list({int(tid) for tid in trail_ids})
        if not ids:
            return {}

        if sync:
            for trail_id in ids:
                self.sync_user_trail_progress(user_id, trail_id)

        totals = self._count_items_for_trails(ids)
        done_map = self._done_items_for_trails(user_id, ids)

        progress_rows = (
            self.db.query(
                UserTrailsORM.trail_id,
                UserTrailsORM.progress_percent,
                UserTrailsORM.started_at,
                UserTrailsORM.completed_at,
                LkEnrollmentStatusORM.code.label("status_code"),
            )
            .outerjoin(
                LkEnrollmentStatusORM,
                LkEnrollmentStatusORM.id == UserTrailsORM.status_id,
            )
            .filter(
                UserTrailsORM.user_id == user_id,
                UserTrailsORM.trail_id.in_(ids),
            )
            .all()
        )

        row_map = {row.trail_id: row for row in progress_rows}
        progress_map: Dict[int, Dict[str, Any]] = {}

        for trail_id in ids:
            total = int(totals.get(trail_id, 0))
            done = int(done_map.get(trail_id, 0))
            row = row_map.get(trail_id)

            if total > 0:
                done = min(done, total)

            if row and row.progress_percent is not None:
                pct = float(row.progress_percent)
            elif total > 0:
                pct = round(100.0 * done / total, 2)
            else:
                pct = 0.0

            if total > 0 and done >= total:
                next_action = "Revisar"
            elif done > 0:
                next_action = "Continuar"
            else:
                next_action = "Começar"

            progress_map[trail_id] = {
                "done": done,
                "total": total,
                "computed_progress_percent": pct,
                "nextAction": next_action,
                "enrolledAt": (
                    row.started_at.isoformat()
                    if row and row.started_at
                    else None
                ),
                "status": row.status_code if row else None,
                "completed_at": (
                    row.completed_at.isoformat()
                    if row and row.completed_at
                    else None
                ),
            }

        return progress_map

    def find_blocking_item(
        self, user_id: int, trail_id: int, target_item_id: int
    ) -> Optional[Dict[str, Any]]:
        section_alias = aliased(TrailSectionsORM)
        rows = (
            self.db.query(
                TrailItemsORM.id.label("item_id"),
                TrailItemsORM.title.label("title"),
                TrailItemsORM.requires_completion,
                TrailItemsORM.requires_completion_yn,
                LkProgressStatusORM.code.label("status_code"),
            )
            .outerjoin(
                UserItemProgressORM,
                (UserItemProgressORM.trail_item_id == TrailItemsORM.id)
                & (UserItemProgressORM.user_id == user_id),
            )
            .outerjoin(
                LkProgressStatusORM,
                LkProgressStatusORM.id == UserItemProgressORM.status_id,
            )
            .outerjoin(section_alias, section_alias.id == TrailItemsORM.section_id)
            .filter(TrailItemsORM.trail_id == trail_id)
            .order_by(
                case((TrailItemsORM.section_id.is_(None), 0), else_=1),
                section_alias.order_index.asc().nullsfirst(),
                TrailItemsORM.order_index.asc().nullsfirst(),
                TrailItemsORM.id.asc(),
            )
            .all()
        )

        blocker: Optional[Dict[str, Any]] = None

        def _requires_completion(row) -> bool:
            if getattr(row, "requires_completion", None) is not None:
                return bool(row.requires_completion)
            flag = getattr(row, "requires_completion_yn", None)
            if flag is not None:
                return str(flag).upper() == "S"
            return False

        for row in rows:
            if row.item_id == target_item_id:
                return blocker

            if not _requires_completion(row):
                continue

            status_code = row.status_code or ""
            if status_code == "COMPLETED":
                if blocker and blocker.get("id") == row.item_id:
                    blocker = None
                continue

            if blocker is None:
                blocker = {
                    "id": row.item_id,
                    "title": row.title or "",
                }

        return blocker

    def get_items_progress(self, user_id: int, trail_id: int) -> List[Dict[str, Any]]:
        section_alias = aliased(TrailSectionsORM)
        rows = (
            self.db.query(
                TrailItemsORM.id.label("item_id"),
                LkProgressStatusORM.code.label("status"),
                UserItemProgressORM.progress_value,
                UserItemProgressORM.completed_at,
            )
            .outerjoin(
                UserItemProgressORM,
                (UserItemProgressORM.trail_item_id == TrailItemsORM.id)
                & (UserItemProgressORM.user_id == user_id),
            )
            .outerjoin(
                LkProgressStatusORM,
                LkProgressStatusORM.id == UserItemProgressORM.status_id,
            )
            .outerjoin(section_alias, section_alias.id == TrailItemsORM.section_id)
            .filter(TrailItemsORM.trail_id == trail_id)
            .order_by(
                case((TrailItemsORM.section_id.is_(None), 0), else_=1),
                section_alias.order_index.asc().nullsfirst(),
                TrailItemsORM.order_index,
                TrailItemsORM.id,
            )
            .all()
        )

        return [
            {
                "item_id": row.item_id,
                "status": row.status,
                "progress_value": row.progress_value,
                "completed_at": (
                    row.completed_at.isoformat() if row.completed_at else None
                ),
            }
            for row in rows
        ]

    def get_sections_progress(
        self, user_id: int, trail_id: int
    ) -> List[Dict[str, Any]]:
        subquery = (
            self.db.query(
                TrailItemsORM.section_id.label("section_id"),
                func.count(TrailItemsORM.id).label("total"),
                func.sum(
                    case(
                        (LkProgressStatusORM.code == "COMPLETED", 1),
                        else_=0,
                    )
                ).label("done"),
            )
            .outerjoin(
                UserItemProgressORM,
                (UserItemProgressORM.trail_item_id == TrailItemsORM.id)
                & (UserItemProgressORM.user_id == user_id),
            )
            .outerjoin(
                LkProgressStatusORM,
                LkProgressStatusORM.id == UserItemProgressORM.status_id,
            )
            .filter(
                TrailItemsORM.trail_id == trail_id, TrailItemsORM.section_id.isnot(None)
            )
            .group_by(TrailItemsORM.section_id)
            .subquery()
        )

        rows = (
            self.db.query(
                TrailSectionsORM.id,
                TrailSectionsORM.title,
                subquery.c.total,
                subquery.c.done,
            )
            .outerjoin(subquery, subquery.c.section_id == TrailSectionsORM.id)
            .filter(TrailSectionsORM.trail_id == trail_id)
            .order_by(TrailSectionsORM.order_index, TrailSectionsORM.id)
            .all()
        )

        return [
            {
                "section_id": row.id,
                "title": row.title,
                "total": row.total or 0,
                "done": row.done or 0,
                "percent": (
                    float(round(100.0 * (row.done or 0) / row.total, 2))
                    if row.total
                    else 0.0
                ),
            }
            for row in rows
        ]

    def get_first_trail_item_id(self, trail_id: int) -> Optional[int]:
        section_alias = aliased(TrailSectionsORM)
        row = (
            self.db.query(TrailItemsORM.id)
            .outerjoin(section_alias, section_alias.id == TrailItemsORM.section_id)
            .filter(TrailItemsORM.trail_id == trail_id)
            .order_by(
                case((TrailItemsORM.section_id.is_(None), 0), else_=1),
                section_alias.order_index.asc().nullsfirst(),
                TrailItemsORM.order_index.asc(),
                TrailItemsORM.id.asc(),
            )
            .first()
        )
        return row[0] if row else None
