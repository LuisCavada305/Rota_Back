from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .lk_question_type import LkQuestionType

if TYPE_CHECKING:
    from .forms import Form
    from .form_question_options import FormQuestionOption
    from .form_answers import FormAnswer
    from .lk_question_type import LkQuestionType


class FormQuestion(Base):
    __tablename__ = "form_question"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    form_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("forms.id", ondelete="CASCADE"), nullable=True
    )
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("lk_question_type.id"), nullable=True
    )
    required: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    required_yn: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1.00"))

    form: Mapped["Form"] = relationship("Form", back_populates="questions")
    options: Mapped[List["FormQuestionOption"]] = relationship(
        "FormQuestionOption",
        back_populates="question",
        order_by="FormQuestionOption.order_index",
    )
    question_type: Mapped[Optional[LkQuestionType]] = relationship("LkQuestionType")
    answers: Mapped[List["FormAnswer"]] = relationship(
        "FormAnswer", back_populates="question"
    )

    def is_required(self) -> bool:
        if self.required is not None:
            return self.required
        if self.required_yn is not None:
            return self.required_yn.upper() == "Y"
        return False
