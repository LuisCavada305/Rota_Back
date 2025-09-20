from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LkProgressStatus(Base):
    __tablename__ = "lk_progress_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )  # 'COMPLETED', etc.
