# app/models/users.py
from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, Date, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.roles import RolesEnum  # RolesEnum(str, Enum): Admin/User/Manager

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.models.lookups import LkSex, LkRole


# ---- Enums ----
class Sex(str, Enum):
    Male = "M"
    Female = "F"
    Other = "O"
    NotSpecified = "N"

from app.core.settings import settings

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # idealmente passe a usar created_at_utc (TIMESTAMP sem TZ); se mantiver created_at, OK também.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # se quiser mapear created_at_utc também:
    # created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())

    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)

    # >>> NOVO: FKs para lookups
    sex_id: Mapped[int] = mapped_column(ForeignKey("lk_sex.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("lk_role.id"), nullable=False)

    # relações para fácil acesso ao code
    sex: Mapped[LkSex] = relationship()
    role: Mapped[LkRole] = relationship()

    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    social_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # seu modelo estava Optional mas nullable=False; alinhei para NOT NULL
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    profile_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # helpers para expor os códigos como antes (M/F/O/N e Admin/User/Manager)
    @property
    def sex_code(self) -> str:
        return self.sex.code if self.sex else "N"

    @property
    def role_code(self) -> str:
        return self.role.code if self.role else "User"

# --------- Pydantic Schemas ---------
from pydantic import BaseModel, EmailStr, field_validator


# app/models/users.py (mesmo arquivo, parte Pydantic)
from pydantic import BaseModel, EmailStr, field_validator

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name_for_certificate: str
    sex: Sex
    birthday: str
    role: RolesEnum = RolesEnum.User
    username: str
    social_name: Optional[str] = None
    remember: bool = False

    @field_validator("sex", mode="before")
    @classmethod
    def map_letters_to_enum(cls, v):
        if isinstance(v, str):
            mapping = {
                "M": Sex.Male, "F": Sex.Female, "O": Sex.Other, "N": Sex.NotSpecified,
                "Male": Sex.Male, "Female": Sex.Female, "Other": Sex.Other, "NotSpecified": Sex.NotSpecified,
            }
            return mapping.get(v, v)
        return v

class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

class UserOut(BaseModel):
    user_id: int
    email: EmailStr
    username: str
    profile_pic_url: Optional[str] = None
    banner_pic_url: Optional[str] = None
    role: RolesEnum
    sex: Sex

    @classmethod
    def from_orm_user(cls, u: "User") -> "UserOut":
        return cls(
            user_id=u.user_id,
            email=u.email,
            username=u.username,
            profile_pic_url=u.profile_pic_url,
            banner_pic_url=u.banner_pic_url,
            role=RolesEnum(u.role_code),     # <-- da lookup
            sex=Sex(u.sex_code),             # <-- da lookup
        )


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class UserOut(BaseModel):
    user_id: int
    email: EmailStr
    username: str
    profile_pic_url: Optional[str] = None
    banner_pic_url: Optional[str] = None
    role: RolesEnum
    sex: Sex

    @classmethod
    def from_orm_user(cls, u: "User") -> "UserOut":
        return cls(
            user_id=u.user_id,
            email=u.email,
            username=u.username,
            profile_pic_url=u.profile_pic_url,
            banner_pic_url=u.banner_pic_url,
            role=RolesEnum(u.role_code),     # <-- da lookup
            sex=Sex(u.sex_code),             # <-- da lookup
        )