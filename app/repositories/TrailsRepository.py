from datetime import date
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.trails import Trails as TrailsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_included_items import TrailIncludedItems as TrailIncludedItemsORM
from app.models.trail_requirements import TrailRequirements as TrailRequirementsORM
from app.models.trail_target_audience import (
    TrailTargetAudience as TrailTargetAudienceORM,
)
from app.models.lk_item_type import LkItemType as LkItemTypeORM


class TrailsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_showcase(self, limit: int = 6) -> List[TrailsORM]:
        return (
            self.db.query(TrailsORM)
            .order_by(TrailsORM.created_date.desc().nullslast())
            .limit(limit)
            .all()
        )

    def list_all(self, offset: int, limit: int) -> Tuple[List[TrailsORM], int]:
        query = self.db.query(TrailsORM)
        total = query.count()
        items = query.order_by(TrailsORM.name).offset(offset).limit(limit).all()
        return items, total

    def get_trail(self, trail_id: int) -> TrailsORM | None:
        return self.db.query(TrailsORM).filter(TrailsORM.id == trail_id).first()

    def list_sections(
        self, trail_id: int, offset: int, limit: int
    ) -> Tuple[List[TrailSectionsORM], int]:
        query = self.db.query(TrailSectionsORM).filter(
            TrailSectionsORM.trail_id == trail_id
        )
        total = query.count()
        items = (
            query.order_by(TrailSectionsORM.order_index, TrailSectionsORM.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def list_section_items(
        self, trail_id: int, section_id: int, *, offset: int, limit: int
    ) -> Tuple[List[TrailItemsORM], int]:
        query = (
            self.db.query(TrailItemsORM)
            .options(joinedload(TrailItemsORM.type))
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == section_id,
            )
        )
        total = query.count()
        items = (
            query.order_by(TrailItemsORM.order_index, TrailItemsORM.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def list_sections_with_items(self, trail_id: int) -> List[TrailSectionsORM]:
        # carrega items e o tipo do item
        return (
            self.db.query(TrailSectionsORM)
            .options(
                selectinload(TrailSectionsORM.items).joinedload(TrailItemsORM.type)
            )
            .filter(TrailSectionsORM.trail_id == trail_id)
            .order_by(TrailSectionsORM.order_index, TrailSectionsORM.id)
            .all()
        )

    def list_included_items(self, trail_id: int) -> List[TrailIncludedItemsORM]:
        return (
            self.db.query(TrailIncludedItemsORM)
            .filter(TrailIncludedItemsORM.trail_id == trail_id)
            .order_by(TrailIncludedItemsORM.ord, TrailIncludedItemsORM.id)
            .all()
        )

    def list_requirements(self, trail_id: int) -> List[TrailRequirementsORM]:
        return (
            self.db.query(TrailRequirementsORM)
            .filter(TrailRequirementsORM.trail_id == trail_id)
            .order_by(TrailRequirementsORM.ord, TrailRequirementsORM.id)
            .all()
        )

    def list_audience(self, trail_id: int) -> List[TrailTargetAudienceORM]:
        return (
            self.db.query(TrailTargetAudienceORM)
            .filter(TrailTargetAudienceORM.trail_id == trail_id)
            .order_by(TrailTargetAudienceORM.ord, TrailTargetAudienceORM.id)
            .all()
        )

    def list_item_types(self) -> List[LkItemTypeORM]:
        return self.db.query(LkItemTypeORM).order_by(LkItemTypeORM.code).all()

    def create_trail(
        self,
        *,
        name: str,
        thumbnail_url: str,
        description: str | None,
        author: str | None,
        created_by: int | None,
        sections: list[dict],
    ) -> TrailsORM:
        trail = TrailsORM(
            name=name,
            thumbnail_url=thumbnail_url,
            description=description,
            author=author,
            created_by=created_by,
            created_date=date.today(),
        )
        self.db.add(trail)
        self.db.flush()

        item_type_map = {row.code.upper(): row.id for row in self.list_item_types()}

        for index, section_payload in enumerate(sections):
            section_order = section_payload.get("order_index")
            section = TrailSectionsORM(
                trail_id=trail.id,
                title=section_payload["title"],
                order_index=section_order if section_order is not None else index,
            )
            self.db.add(section)
            self.db.flush()

            items_payload = section_payload.get("items") or []
            for item_index, item_payload in enumerate(items_payload):
                type_code = (item_payload.get("type") or "").upper()
                if type_code not in item_type_map:
                    raise ValueError(f"Tipo de item '{type_code}' não cadastrado.")
                item_order = item_payload.get("order_index")
                duration_value = item_payload.get("duration_seconds")
                if isinstance(duration_value, str):
                    duration_value = duration_value.strip()
                    duration_value = int(duration_value) if duration_value else None
                item = TrailItemsORM(
                    trail_id=trail.id,
                    section_id=section.id,
                    title=item_payload.get("title"),
                    url=item_payload.get("url"),
                    duration_seconds=duration_value,
                    order_index=item_order if item_order is not None else item_index,
                    item_type_id=item_type_map[type_code],
                    legacy_type=type_code,
                    requires_completion=bool(item_payload.get("requires_completion")),
                )
                self.db.add(item)

        self.db.commit()
        self.db.refresh(trail)
        return trail
