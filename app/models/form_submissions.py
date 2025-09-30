from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .forms import Form
    from .users import User
    from .form_answers import FormAnswer


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    form_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("forms.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    form: Mapped["Form"] = relationship("Form", back_populates="submissions")
    user: Mapped[Optional["User"]] = relationship("User")
    answers: Mapped[List["FormAnswer"]] = relationship(
        "FormAnswer", back_populates="submission", cascade="all, delete-orphan"
    )
