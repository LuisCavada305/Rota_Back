from sqlalchemy import Column, String, DateTime, func, Enum as SAEnum
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from enum import Enum
from app.models.roles import RolesEnum
import uuid
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

def uuid4_str() -> str:
    return str(uuid.uuid4())

class Sex(str, Enum):  
    Male = "M"
    Female = "F"
    Other = "O"
    NotSpecified = "N"

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    name_for_certificate: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[Sex] = mapped_column(
        PGEnum(
            Sex,
            name="sex_type",
            values_callable=lambda E: [e.value for e in E],  # <-- força usar 'M','F','O','N'
            native_enum=True,
            validate_strings=True,
            create_type=False,  # tipo já existe no PG
        ),
        nullable=False,
        server_default=Sex.NotSpecified.value,  # "N"
    )
    birthday: Mapped[str | None] = mapped_column(DateTime, nullable=True)



class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    name_for_certificate: str
    sex: Sex
    birthday: str
    role: RolesEnum = RolesEnum.User

    @field_validator("sex", mode="before")
    @classmethod
    def map_letters_to_enum(cls, v):
        if isinstance(v, str):
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
            if v in mapping:
                return mapping[v]
        return v
    
class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    role: RolesEnum = RolesEnum.User


