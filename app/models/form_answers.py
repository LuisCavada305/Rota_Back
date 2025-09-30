from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .form_submissions import FormSubmission
    from .form_questions import FormQuestion
    from .form_question_options import FormQuestionOption


class FormAnswer(Base):
    __tablename__ = "form_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submission_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("form_submissions.id", ondelete="CASCADE"), nullable=True
    )
    question_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("form_question.id", ondelete="CASCADE"), nullable=True
    )
    selected_option_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("form_question_options.id", ondelete="SET NULL"),
        nullable=True,
    )
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True
    )

    submission: Mapped["FormSubmission"] = relationship(
        "FormSubmission", back_populates="answers"
    )
    question: Mapped["FormQuestion"] = relationship(
        "FormQuestion", back_populates="answers"
    )
    selected_option: Mapped[Optional["FormQuestionOption"]] = relationship(
        "FormQuestionOption", back_populates="answers"
    )
