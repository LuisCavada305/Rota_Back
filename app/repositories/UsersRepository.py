# app/repositories/UsersRepository.py
from __future__ import annotations
from typing import Optional, Tuple

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.users import User
from app.models.lookups import LkRole, LkSex
from app.models.roles import RolesEnum
from app.models.users import Sex  # seu Enum de API (M/F/O/N)


class UsersRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Helpers de lookup (code -> id) ----------
    def _sex_id(self, sex: Sex) -> int:
        sid = self.db.scalars(select(LkSex.id).where(LkSex.code == sex.value)).first()
        if sid is None:
            raise ValueError(f"lk_sex não possui code '{sex.value}'")
        return sid

    def _role_id(self, role: RolesEnum) -> int:
        rid = self.db.scalars(
            select(LkRole.id).where(LkRole.code == role.value)
        ).first()
        if rid is None:
            raise ValueError(f"lk_role não possui code '{role.value}'")
        return rid

    def resolve_ids(self, sex: Sex, role: RolesEnum) -> Tuple[int, int]:
        return self._sex_id(sex), self._role_id(role)

    # ---------- Queries (com relações carregadas) ----------
    def GetUserByEmail(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .options(selectinload(User.sex), selectinload(User.role))
            .filter(User.email == email)
            .first()
        )

    def GetUserByUsername(self, username: str) -> Optional[User]:
        return (
            self.db.query(User)
            .options(selectinload(User.sex), selectinload(User.role))
            .filter(User.username == username)
            .first()
        )

    def GetUserById(self, user_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .options(selectinload(User.sex), selectinload(User.role))
            .filter(User.user_id == user_id)
            .first()
        )

    def ExistsEmail(self, email: str) -> bool:
        return (
            self.db.query(User.user_id).filter(User.email == email).first() is not None
        )

    def ExistsUsername(self, username: str) -> bool:
        return (
            self.db.query(User.user_id).filter(User.username == username).first()
            is not None
        )

    # ---------- Criação / Atualização ----------
    def CreateUser(
        self,
        *,
        email: str,
        password_hash: str,
        name_for_certificate: str,
        username: str,
        sex: Sex,
        role: RolesEnum,
        birthday=None,
        social_name: Optional[str] = None,
        profile_pic_url: Optional[str] = None,
        banner_pic_url: Optional[str] = None,
    ) -> User:
        sex_id, role_id = self.resolve_ids(sex, role)
        user = User(
            email=email,
            password_hash=password_hash,
            name_for_certificate=name_for_certificate,
            username=username,
            social_name=social_name,
            sex_id=sex_id,  # << usa IDs
            role_id=role_id,  # << usa IDs
            birthday=birthday,
            profile_pic_url=profile_pic_url,
            banner_pic_url=banner_pic_url,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        # garante relações carregadas para serialização imediata
        self.db.refresh(user, attribute_names=["sex", "role"])
        return user

    def UpdateUserRole(self, user: User, new_role: RolesEnum) -> User:
        user.role_id = self._role_id(new_role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(user, attribute_names=["role"])
        return user

    def UpdateUserSex(self, user: User, new_sex: Sex) -> User:
        user.sex_id = self._sex_id(new_sex)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(user, attribute_names=["sex"])
        return user
