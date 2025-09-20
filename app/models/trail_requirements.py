from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class TrailRequirements(Base):
    __tablename__ = "trail_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trail_id: Mapped[int] = mapped_column(
        ForeignKey("trails.id", ondelete="CASCADE"), nullable=False
    )
    text_val: Mapped[str] = mapped_column(String(500), nullable=False)
    ord: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    trail = relationship("Trails", back_populates="requirements")
