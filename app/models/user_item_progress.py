# app/models/user_item_progress.py
from typing import Optional
from sqlalchemy import Integer, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from datetime import datetime


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
    completed_at: Mapped[Optional["datetime"]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
