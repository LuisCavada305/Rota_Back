from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .trail_sections import TrailSections
    from .lk_item_type import LkItemType


class TrailItems(Base):
    __tablename__ = "trail_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    trail_id: Mapped[int] = mapped_column(
        ForeignKey("trails.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trail_sections.id", ondelete="SET NULL")
    )
    item_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lk_item_type.id"), nullable=True
    )

    section: Mapped[Optional["TrailSections"]] = relationship(back_populates="items")
    type: Mapped[Optional["LkItemType"]] = relationship()
