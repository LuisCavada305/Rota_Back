# app/models/user_trails.py
from typing import Optional
from sqlalchemy import Integer, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from datetime import datetime


class UserTrails(Base):
    __tablename__ = "user_trails"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE")
    )
    trail_id: Mapped[int] = mapped_column(ForeignKey("trails.id", ondelete="CASCADE"))
    started_at: Mapped[Optional["datetime"]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
