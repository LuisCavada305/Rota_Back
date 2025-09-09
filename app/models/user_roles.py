from sqlalchemy import Enum, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from enum import Enum 

class UserRoles(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(String, nullable=False, is_primary_key=True)
    role_id: Mapped[str] = mapped_column(String, nullable=False, is_primary_key=True)


