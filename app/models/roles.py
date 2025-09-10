from sqlalchemy import Enum, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from enum import Enum

class RolesEnum(str, Enum):
    Admin = "Admin"
    User = "User"
    Manager = "Manager"
