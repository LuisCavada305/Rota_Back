from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .trail_sections import TrailSections
    from .trail_included_items import TrailIncludedItems
    from .trail_requirements import TrailRequirements
    from .trail_target_audience import TrailTargetAudience
    from .forums import Forum


class Trails(Base):
    __tablename__ = "trails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thumbnail_url: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    review: Mapped[Optional[float]] = mapped_column(
        Numeric(asdecimal=False), nullable=True
    )
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    sections: Mapped[List["TrailSections"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan"
    )
    included_items: Mapped[List["TrailIncludedItems"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan"
    )
    requirements: Mapped[List["TrailRequirements"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan"
    )
    target_audience: Mapped[List["TrailTargetAudience"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan"
    )
    forums: Mapped[List["Forum"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan"
    )
