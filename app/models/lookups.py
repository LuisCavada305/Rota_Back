from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from app.models.base import Base


class LkSex(Base):
    __tablename__ = "lk_sex"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)


class LkRole(Base):
    __tablename__ = "lk_role"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
