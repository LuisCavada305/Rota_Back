from typing import List
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.trails import Trails as TrailsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_included_items import TrailIncludedItems as TrailIncludedItemsORM
from app.models.trail_requirements import TrailRequirements as TrailRequirementsORM
from app.models.trail_target_audience import TrailTargetAudience as TrailTargetAudienceORM
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

    def list_all(self) -> List[TrailsORM]:
        return self.db.query(TrailsORM).order_by(TrailsORM.name).all()

    def get_trail(self, trail_id: int) -> TrailsORM | None:
        return (
            self.db.query(TrailsORM)
            .filter(TrailsORM.id == trail_id)
            .first()
        )

    def list_sections(self, trail_id: int) -> List[TrailSectionsORM]:
        return (
            self.db.query(TrailSectionsORM)
            .filter(TrailSectionsORM.trail_id == trail_id)
            .order_by(TrailSectionsORM.order_index, TrailSectionsORM.id)
            .all()
        )

    def list_section_items(self, trail_id: int, section_id: int) -> List[TrailItemsORM]:
        return (
            self.db.query(TrailItemsORM)
            .options(joinedload(TrailItemsORM.item_type))
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == section_id,
            )
            .order_by(TrailItemsORM.order_index, TrailItemsORM.id)
            .all()
        )

    def list_sections_with_items(self, trail_id: int) -> List[TrailSectionsORM]:
        # carrega items e o tipo do item
        return (
            self.db.query(TrailSectionsORM)
            .options(
                selectinload(TrailSectionsORM.items).joinedload(TrailItemsORM.item_type)
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
