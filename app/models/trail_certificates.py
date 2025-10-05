# app/models/trail_certificates.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TrailCertificates(Base):
    __tablename__ = "trail_certificates"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "trail_id",
            name="uq_trail_certificates_user_trail",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    trail_id: Mapped[int] = mapped_column(
        ForeignKey("trails.id", ondelete="CASCADE"), nullable=False
    )
    certificate_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    credential_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
