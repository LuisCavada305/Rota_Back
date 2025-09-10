from sqlalchemy import Enum, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from enum import Enum

class Roles(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

class RolesEnum(str, Enum):
    Admin = "0"
    User = "1"
