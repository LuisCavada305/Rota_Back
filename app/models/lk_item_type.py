from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LkItemType(Base):
    __tablename__ = "lk_item_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True
    )  # 'VIDEO' | 'DOC' | 'FORM'
