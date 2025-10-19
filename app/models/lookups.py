from sqlalchemy.orm import Mapped, mapped_column
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


class LkColor(Base):
    __tablename__ = "lk_color"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
