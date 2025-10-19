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
from app.models.lookups import LkSex, LkRole, LkColor


# ---- Enums ----
class Sex(str, Enum):
    ManCis = "MC"
    ManTrans = "MT"
    WomanCis = "WC"
    WomanTrans = "WT"
    Other = "OT"
    NotSpecified = "NS"

    @classmethod
    def _normalize(cls, value: str) -> str:
        return value.strip().replace(" ", "").replace("-", "").replace("_", "").upper()

    @classmethod
    def parse(cls, value) -> "Sex":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ValueError("Valor de sexo inválido.")
        key = cls._normalize(value)
        alias_map = {
            cls.ManCis.value: cls.ManCis,
            "M": cls.ManCis,
            "MALE": cls.ManCis,
            "MAN": cls.ManCis,
            "HOMEM": cls.ManCis,
            "MANCIS": cls.ManCis,
            "HOMEMCIS": cls.ManCis,
            cls.ManTrans.value: cls.ManTrans,
            "MT": cls.ManTrans,
            "MANT": cls.ManTrans,
            "HOMEMTRANS": cls.ManTrans,
            cls.WomanCis.value: cls.WomanCis,
            "F": cls.WomanCis,
            "FEMALE": cls.WomanCis,
            "WOMAN": cls.WomanCis,
            "MULHER": cls.WomanCis,
            "MULHERCIS": cls.WomanCis,
            "FEMININO": cls.WomanCis,
            cls.WomanTrans.value: cls.WomanTrans,
            "WT": cls.WomanTrans,
            "MULHERTRANS": cls.WomanTrans,
            "WOMANTRANS": cls.WomanTrans,
            cls.Other.value: cls.Other,
            "O": cls.Other,
            "OTHER": cls.Other,
            "OUTRO": cls.Other,
            "OUTRA": cls.Other,
            "OT": cls.Other,
            cls.NotSpecified.value: cls.NotSpecified,
            "N": cls.NotSpecified,
            "NS": cls.NotSpecified,
            "NAOESPECIFICADO": cls.NotSpecified,
            "NAOESPECIFICO": cls.NotSpecified,
            "NAOESPECIFICADA": cls.NotSpecified,
            "NOTSPECIFIED": cls.NotSpecified,
        }
        sex = alias_map.get(key)
        if sex is None:
            raise ValueError(f"Valor de sexo desconhecido: {value!r}")
        return sex

    @classmethod
    def from_db_code(cls, value: str | None) -> "Sex":
        if value is None:
            return cls.NotSpecified
        try:
            return cls.parse(value)
        except ValueError:
            return cls.NotSpecified


class SkinColor(str, Enum):
    White = "BR"
    Black = "PR"
    Brown = "PA"
    Yellow = "AM"
    Indigenous = "IN"
    Other = "OU"
    NotSpecified = "NS"


from app.core.settings import settings


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # idealmente passe a usar created_at_utc (TIMESTAMP sem TZ); se mantiver created_at, OK também.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # se quiser mapear created_at_utc também:
    # created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())

    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)

    # >>> NOVO: FKs para lookups
    sex_id: Mapped[int] = mapped_column(ForeignKey("lk_sex.id"), nullable=False)
    color_id: Mapped[int] = mapped_column(ForeignKey("lk_color.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("lk_role.id"), nullable=False)

    # relações para fácil acesso ao code
    sex: Mapped[LkSex] = relationship()
    color: Mapped[LkColor] = relationship()
    role: Mapped[LkRole] = relationship()

    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    social_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # seu modelo estava Optional mas nullable=False; alinhei para NOT NULL
    username: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )

    profile_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_pic_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # helpers para expor os códigos como antes (M/F/O/N e Admin/User/Manager)
    @property
    def sex_code(self) -> str:
        return self.sex.code if self.sex else Sex.NotSpecified.value

    @property
    def color_code(self) -> str:
        return self.color.code if self.color else "NS"

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
    color: SkinColor
    birthday: str
    role: RolesEnum = RolesEnum.User
    username: str
    social_name: Optional[str] = None
    remember: bool = False

    @field_validator("sex", mode="before")
    @classmethod
    def map_letters_to_enum(cls, v):
        if isinstance(v, Sex):
            return v
        if isinstance(v, str):
            try:
                return Sex.parse(v)
            except ValueError:
                raise ValueError("Sexo inválido")
        raise ValueError("Sexo inválido")

    @field_validator("color", mode="before")
    @classmethod
    def map_color_letters_to_enum(cls, v):
        if isinstance(v, str):
            mapping = {
                "BR": SkinColor.White,
                "PR": SkinColor.Black,
                "PA": SkinColor.Brown,
                "AM": SkinColor.Yellow,
                "IN": SkinColor.Indigenous,
                "OU": SkinColor.Other,
                "NS": SkinColor.NotSpecified,
                "White": SkinColor.White,
                "Black": SkinColor.Black,
                "Brown": SkinColor.Brown,
                "Yellow": SkinColor.Yellow,
                "Indigenous": SkinColor.Indigenous,
                "Other": SkinColor.Other,
                "NotSpecified": SkinColor.NotSpecified,
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
    color: SkinColor

    @classmethod
    def from_orm_user(cls, u: "User") -> "UserOut":
        return cls(
            user_id=u.user_id,
            email=u.email,
            username=u.username,
            profile_pic_url=u.profile_pic_url,
            banner_pic_url=u.banner_pic_url,
            role=RolesEnum(u.role_code),  # <-- da lookup
            sex=Sex.from_db_code(u.sex_code),  # <-- da lookup
            color=SkinColor(u.color_code),
        )


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str


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
    color: SkinColor

    @classmethod
    def from_orm_user(cls, u: "User") -> "UserOut":
        return cls(
            user_id=u.user_id,
            email=u.email,
            username=u.username,
            profile_pic_url=u.profile_pic_url,
            banner_pic_url=u.banner_pic_url,
            role=RolesEnum(u.role_code),  # <-- da lookup
            sex=Sex.from_db_code(u.sex_code),  # <-- da lookup
            color=SkinColor(u.color_code),
        )
