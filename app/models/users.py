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

# ---- Enums ----
class Sex(str, Enum):
    Male = "M"
    Female = "F"
    Other = "O"
    NotSpecified = "N"

# Helper para ENUM compatível (Postgres/SQLite)
def db_enum(enum_cls, name: str, is_postgres: bool):
    if is_postgres:
        return PGEnum(
            enum_cls,
            name=name,
            values_callable=lambda E: [e.value for e in E],
            native_enum=True,
            validate_strings=True,
            create_type=False,  # deixe a migração criar
        )
    else:
        # SQLite: usa SAEnum sem tipo nativo
        return SAEnum(
            enum_cls,
            name=name,
            values_callable=lambda E: [e.value for e in E],
            native_enum=False,
            validate_strings=True,
        )

# Detecta se a URL é Postgres (ajuste conforme sua app)
from app.core.settings import settings
IS_PG = settings.database_url.startswith("postgres")

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email:   Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)

    sex: Mapped[Sex] = mapped_column(
        db_enum(Sex, "sex_type", IS_PG),
        nullable=False,
        server_default=Sex.NotSpecified.value,  # "N"
    )

    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    social_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

   
    username: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=False)

    role: Mapped[RolesEnum] = mapped_column(
        db_enum(RolesEnum, "roles_enum", IS_PG),
        nullable=False,
        server_default=RolesEnum.User.value,  # "User"
    )

    profile_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# --------- Pydantic Schemas ---------
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

    @field_validator("sex", mode="before")
    @classmethod
    def map_letters_to_enum(cls, v):
        if isinstance(v, str):
            mapping = {
                "M": Sex.Male, "F": Sex.Female, "O": Sex.Other, "N": Sex.NotSpecified,
                "Male": Sex.Male, "Female": Sex.Female, "Other": Sex.Other, "NotSpecified": Sex.NotSpecified,
            }
            if v in mapping:
                return mapping[v]
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
    role: RolesEnum = RolesEnum.User
