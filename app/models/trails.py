from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Trails(Base):
    __tablename__ = "trails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    review: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_date: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requirements: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    target_audience: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    included_items: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
