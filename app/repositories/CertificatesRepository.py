from __future__ import annotations

import secrets
from typing import Dict, Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.trail_certificates import TrailCertificates as TrailCertificatesORM
from app.models.users import User as UserORM
from app.models.trails import Trails as TrailsORM


class CertificatesRepository:
    def __init__(self, db: Session):
        self.db = db

    def _generate_token(self, length: int = 16) -> str:
        # Returns a lower-case hex string with the requested number of characters.
        return secrets.token_hex(length // 2)

    def _ensure_unique_token(self) -> str:
        while True:
            candidate = self._generate_token(16)
            exists = (
                self.db.query(TrailCertificatesORM.id)
                .filter(TrailCertificatesORM.certificate_hash == candidate)
                .first()
            )
            if not exists:
                return candidate

    def ensure_certificate(self, user_id: int, trail_id: int) -> TrailCertificatesORM:
        cert = (
            self.db.query(TrailCertificatesORM)
            .filter(
                TrailCertificatesORM.user_id == user_id,
                TrailCertificatesORM.trail_id == trail_id,
            )
            .first()
        )
        if cert:
            return cert

        token = self._ensure_unique_token()
        now_expr = func.now()
        cert = TrailCertificatesORM(
            user_id=user_id,
            trail_id=trail_id,
            certificate_hash=token,
            credential_id=token,
            issued_at=now_expr,
            issued_at_utc=now_expr,
        )
        self.db.add(cert)
        self.db.flush()
        return cert

    def get_for_user_trails(
        self, user_id: int, trail_ids: Iterable[int]
    ) -> Dict[int, TrailCertificatesORM]:
        ids = list({int(tid) for tid in trail_ids})
        if not ids:
            return {}
        rows = (
            self.db.query(TrailCertificatesORM)
            .filter(
                TrailCertificatesORM.user_id == user_id,
                TrailCertificatesORM.trail_id.in_(ids),
            )
            .all()
        )
        return {row.trail_id: row for row in rows}

    def get_for_user_trail(
        self, user_id: int, trail_id: int
    ) -> Optional[TrailCertificatesORM]:
        return (
            self.db.query(TrailCertificatesORM)
            .filter(
                TrailCertificatesORM.user_id == user_id,
                TrailCertificatesORM.trail_id == trail_id,
            )
            .first()
        )

    def get_by_hash(self, certificate_hash: str) -> Optional[TrailCertificatesORM]:
        cleaned = (certificate_hash or "").strip().lower()
        if not cleaned:
            return None
        return (
            self.db.query(TrailCertificatesORM)
            .filter(TrailCertificatesORM.certificate_hash == cleaned)
            .first()
        )

    def get_details_by_hash(
        self, certificate_hash: str
    ) -> Optional[tuple[TrailCertificatesORM, UserORM, TrailsORM]]:
        cleaned = (certificate_hash or "").strip().lower()
        if not cleaned:
            return None
        return (
            self.db.query(TrailCertificatesORM, UserORM, TrailsORM)
            .join(UserORM, UserORM.user_id == TrailCertificatesORM.user_id)
            .join(TrailsORM, TrailsORM.id == TrailCertificatesORM.trail_id)
            .filter(TrailCertificatesORM.certificate_hash == cleaned)
            .first()
        )

    def get_details_for_user_trail(
        self, user_id: int, trail_id: int
    ) -> Optional[tuple[TrailCertificatesORM, UserORM, TrailsORM]]:
        return (
            self.db.query(TrailCertificatesORM, UserORM, TrailsORM)
            .join(UserORM, UserORM.user_id == TrailCertificatesORM.user_id)
            .join(TrailsORM, TrailsORM.id == TrailCertificatesORM.trail_id)
            .filter(
                TrailCertificatesORM.user_id == user_id,
                TrailCertificatesORM.trail_id == trail_id,
            )
            .first()
        )
