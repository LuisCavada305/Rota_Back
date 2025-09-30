from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .form_questions import FormQuestion
    from .form_answers import FormAnswer


class FormQuestionOption(Base):
    __tablename__ = "form_question_options"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("form_question.id", ondelete="CASCADE"), nullable=True
    )
    option_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_correct_yn: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped["FormQuestion"] = relationship(
        "FormQuestion", back_populates="options"
    )
    answers: Mapped[list["FormAnswer"]] = relationship(
        "FormAnswer", back_populates="selected_option"
    )

    def correct(self) -> Optional[bool]:
        if self.is_correct is not None:
            return self.is_correct
        if self.is_correct_yn is not None:
            return self.is_correct_yn.upper() == "Y"
        return None
