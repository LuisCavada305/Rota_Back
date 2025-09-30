# app/models/user_item_progress.py
from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class UserItemProgress(Base):
    __tablename__ = "user_item_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE")
    )
    trail_item_id: Mapped[int] = mapped_column(
        ForeignKey("trail_items.id", ondelete="CASCADE")
    )
    status_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lk_progress_status.id")
    )
    progress_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_interaction: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_interaction_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    completed_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    last_passed_submission_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("form_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
