from __future__ import annotations

from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .trails import Trails  # só para lint/type-check, não roda em runtime
    from .trail_items import TrailItems


class TrailSections(Base):
    __tablename__ = "trail_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trail_id: Mapped[int] = mapped_column(
        ForeignKey("trails.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    trail: Mapped["Trails"] = relationship(back_populates="sections")
    items: Mapped[List["TrailItems"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
