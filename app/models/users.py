from sqlalchemy import Column, String, DateTime, func, Enum as SAEnum
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from enum import Enum
from .roles import RolesEnum
import uuid

def uuid4_str() -> str:
    return str(uuid.uuid4())

class Sex(str, Enum):
    Male = "M"
    Female = "F"
    Other = "O"
    NotSpecified = "N"  

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[Sex] = mapped_column(SAEnum
                                     (Sex, name="sex_type", 
                                            native_enum=True,
                                            validate_strings=True
                                            ), nullable=False, server_default=Sex.NotSpecified.value)
    birthday: Mapped[str | None] = mapped_column(DateTime, nullable=True)

from pydantic import BaseModel, EmailStr

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    name_for_certificate: str
    sex: Sex
    birthday: str
    role: RolesEnum = RolesEnum.User

class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None
    role: RolesEnum = RolesEnum.User
