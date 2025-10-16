from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from sqlalchemy.types import UserDefinedType

if TYPE_CHECKING:
    from .trail_sections import TrailSections
    from .lk_item_type import LkItemType
    from .forms import Form


class ItemTypeEnum(UserDefinedType):
    def get_col_spec(self, **_kw):
        return "item_type"

    def bind_processor(self, dialect):
        def process(value):
            return value

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value

        return process


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
    legacy_type: Mapped[str] = mapped_column("type", ItemTypeEnum(), nullable=False)

    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trail_sections.id", ondelete="SET NULL")
    )
    item_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lk_item_type.id"), nullable=True
    )
    requires_completion: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    requires_completion_yn: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )

    section: Mapped[Optional["TrailSections"]] = relationship(back_populates="items")
    type: Mapped[Optional["LkItemType"]] = relationship()
    form: Mapped[Optional["Form"]] = relationship(
        "Form", back_populates="trail_item", uselist=False
    )

    def completion_required(self) -> bool:
        if self.requires_completion is not None:
            return bool(self.requires_completion)
        if self.requires_completion_yn is not None:
            return self.requires_completion_yn.upper() == "S"
        return False
