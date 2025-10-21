# app/models/user_trails.py
from typing import Optional
from datetime import datetime
from sqlalchemy import (
    Integer,
    BigInteger,
    ForeignKey,
    DateTime,
    Numeric,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class UserTrails(Base):
    __tablename__ = "user_trails"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE")
    )
    trail_id: Mapped[int] = mapped_column(ForeignKey("trails.id", ondelete="CASCADE"))
    status_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lk_enrollment_status.id"), nullable=True
    )
    progress_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    completed_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    review_rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
