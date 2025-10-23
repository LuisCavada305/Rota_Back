from __future__ import annotations

import base64
import io
from datetime import datetime
from functools import lru_cache

from flask import Blueprint, jsonify, abort, request
from pydantic import BaseModel

import segno

from app.core.db import get_db
from app.repositories.CertificatesRepository import CertificatesRepository
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.services.security import get_current_user


bp = Blueprint("certificates", __name__, url_prefix="/certificates")


def _format_datetime(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=None).isoformat()
    return dt.isoformat()


@lru_cache(maxsize=256)
def _cached_qr_data_uri(payload: str) -> str:
    qr = segno.make(payload, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=6)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _qr_data_uri(payload: str) -> str:
    return _cached_qr_data_uri(payload)


class CertificateResponse(BaseModel):
    trail_id: int
    trail_title: str
    student_name: str
    credential_id: str
    certificate_hash: str
    issued_at: str | None
    verification_url: str
    qr_code_data_uri: str


@bp.get("/<string:certificate_hash>")
def get_certificate(certificate_hash: str):
    db = get_db()
    repo = CertificatesRepository(db)
    row = repo.get_details_by_hash(certificate_hash)
    if not row:
        abort(404, description="Certificado não encontrado")

    cert, user, trail = row
    verify_base = request.args.get("verify_base") or request.url_root
    verify_base = verify_base.rstrip("/")
    verification_url = f"{verify_base}/certificados/?cert_hash={cert.certificate_hash}"

    payload = CertificateResponse(
        trail_id=trail.id,
        trail_title=trail.name,
        student_name=user.name_for_certificate,
        credential_id=cert.credential_id,
        certificate_hash=cert.certificate_hash,
        issued_at=_format_datetime(cert.issued_at),
        verification_url=verification_url,
        qr_code_data_uri=_qr_data_uri(verification_url),
    )
    return jsonify(payload.model_dump(mode="json"))


@bp.route("/me/trails/<int:trail_id>", methods=["GET", "OPTIONS"])
def get_certificate_for_my_trail(trail_id: int):
    user = get_current_user()
    db = get_db()
    cert_repo = CertificatesRepository(db)

    row = cert_repo.get_details_for_user_trail(user.user_id, trail_id)
    if not row:
        UserTrailsRepository(db).sync_user_trail_progress(user.user_id, trail_id)
        db.commit()
        row = cert_repo.get_details_for_user_trail(user.user_id, trail_id)
        if not row:
            abort(404, description="Certificado não encontrado para esta trilha")

    cert, user_model, trail = row

    verify_base = request.args.get("verify_base") or request.url_root
    verify_base = verify_base.rstrip("/")
    verification_url = f"{verify_base}/certificados/?cert_hash={cert.certificate_hash}"

    payload = CertificateResponse(
        trail_id=trail.id,
        trail_title=trail.name,
        student_name=user_model.name_for_certificate,
        credential_id=cert.credential_id,
        certificate_hash=cert.certificate_hash,
        issued_at=_format_datetime(cert.issued_at),
        verification_url=verification_url,
        qr_code_data_uri=_qr_data_uri(verification_url),
    )
    return jsonify(payload.model_dump(mode="json"))
