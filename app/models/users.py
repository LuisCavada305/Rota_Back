from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.lookups import LkRole, LkSex
from app.models.roles import RolesEnum


class Sex(str, Enum):
    Male = "M"
    Female = "F"
    Other = "O"
    NotSpecified = "N"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)
    sex_id: Mapped[int] = mapped_column(ForeignKey("lk_sex.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("lk_role.id"), nullable=False)
    sex: Mapped[LkSex] = relationship()
    role: Mapped[LkRole] = relationship()
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    social_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    profile_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    @property
    def sex_code(self) -> str:
        return self.sex.code if self.sex else Sex.NotSpecified.value

    @property
    def role_code(self) -> str:
        return self.role.code if self.role else RolesEnum.User.value


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
    def map_letters_to_enum(cls, value):
        if isinstance(value, Sex):
            return value
        if isinstance(value, str):
            mapping = {
                "M": Sex.Male,
                "F": Sex.Female,
                "O": Sex.Other,
                "N": Sex.NotSpecified,
                "Male": Sex.Male,
                "Female": Sex.Female,
                "Other": Sex.Other,
                "NotSpecified": Sex.NotSpecified,
            }
            return mapping.get(value, value)
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str


class UserOut(BaseModel):
    user_id: int
    email: EmailStr
    username: str
    profile_pic_url: Optional[str] = None
    banner_pic_url: Optional[str] = None
    role: RolesEnum
    sex: Sex

    @classmethod
    def from_orm_user(cls, user: User) -> UserOut:
        return cls(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            profile_pic_url=user.profile_pic_url,
            banner_pic_url=user.banner_pic_url,
            role=RolesEnum(user.role_code),
            sex=Sex(user.sex_code),
        )
