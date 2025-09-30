from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .trail_items import TrailItems
    from .form_questions import FormQuestion
    from .form_submissions import FormSubmission


class Form(Base):
    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trail_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("trail_items.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(
        "description", Text, nullable=True
    )
    min_score_to_pass: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("70.00")
    )
    randomize_questions: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    randomize_questions_yn: Mapped[Optional[str]] = mapped_column(
        "randomize_questions_yn", String(1), nullable=True
    )

    trail_item: Mapped["TrailItems"] = relationship(
        "TrailItems", back_populates="form", uselist=False
    )
    questions: Mapped[List["FormQuestion"]] = relationship(
        "FormQuestion", back_populates="form", order_by="FormQuestion.order_index"
    )
    submissions: Mapped[List["FormSubmission"]] = relationship(
        "FormSubmission", back_populates="form"
    )

    def randomize_enabled(self) -> Optional[bool]:
        if self.randomize_questions is not None:
            return self.randomize_questions
        if self.randomize_questions_yn is not None:
            return self.randomize_questions_yn.upper() == "S"
        return None
