from __future__ import annotations

from typing import List
from flask import Blueprint, jsonify, request, g
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import case, func

from app.core.db import get_db
from app.models.users import User
from app.models.trails import Trails as TrailsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_certificates import TrailCertificates as TrailCertificatesORM
from app.models.user_trails import UserTrails as UserTrailsORM
from app.models.lk_enrollment_status import LkEnrollmentStatus as LkEnrollmentStatusORM
from app.repositories.TrailsRepository import TrailsRepository
from app.services.security import enforce_csrf, require_roles
from app.routes import format_validation_error


bp = Blueprint("admin", __name__, url_prefix="/admin")


class AdminFormOptionIn(BaseModel):
    text: str = Field(..., min_length=1)
    is_correct: bool = False
    order_index: int | None = Field(default=None, ge=0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Preencha o texto da alternativa.")
        return cleaned


class AdminFormQuestionIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    required: bool = True
    points: float = Field(default=1.0, ge=0)
    order_index: int | None = Field(default=None, ge=0)
    options: List[AdminFormOptionIn] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe o enunciado da pergunta.")
        return cleaned

    @field_validator("type")
    @classmethod
    def normalize_question_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"ESSAY", "TRUE_OR_FALSE", "SINGLE_CHOICE"}
        if normalized not in allowed:
            raise ValueError("Tipo de pergunta inválido.")
        return normalized

    @model_validator(mode="after")
    def validate_options(self):
        if self.type == "ESSAY":
            self.options = []
        else:
            if not self.options:
                raise ValueError("Adicione alternativas para perguntas objetivas.")
            if not any(option.is_correct for option in self.options):
                raise ValueError("Marque pelo menos uma alternativa correta.")
            if self.type == "TRUE_OR_FALSE" and len(self.options) < 2:
                raise ValueError(
                    "Perguntas de verdadeiro ou falso precisam de duas alternativas."
                )
        return self


class AdminFormIn(BaseModel):
    title: str | None = None
    description: str | None = None
    min_score_to_pass: float = Field(default=70, ge=0)
    randomize_questions: bool | None = None
    questions: List[AdminFormQuestionIn] = Field(default_factory=list)

    @field_validator("title", "description")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def ensure_questions(self):
        if not self.questions:
            raise ValueError("O formulário precisa de pelo menos uma pergunta.")
        return self


class AdminTrailItemIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=32)
    url: str = Field(..., min_length=1)
    duration_seconds: int | None = Field(default=None, ge=0)
    requires_completion: bool = False
    order_index: int | None = Field(default=None, ge=0)
    form: AdminFormIn | None = None

    @field_validator("title", "type", "url")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Este campo é obrigatório.")
        return cleaned

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_form(self):
        if self.type == "FORM":
            if self.form is None:
                raise ValueError(
                    "Itens do tipo Formulário precisam de dados do formulário."
                )
        else:
            self.form = None
        return self


class AdminTrailSectionIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    order_index: int | None = Field(default=None, ge=0)
    items: List[AdminTrailItemIn] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Informe um título para a seção.")
        return cleaned


class AdminTrailCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    thumbnail_url: str = Field(..., min_length=1)
    description: str | None = None
    author: str | None = None
    sections: List[AdminTrailSectionIn] = Field(default_factory=list)

    @field_validator("name", "thumbnail_url")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Este campo é obrigatório.")
        return cleaned

    @field_validator("author")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


@bp.before_request
def ensure_admin():
    if request.method == "OPTIONS":
        return None
    g.current_admin = require_roles("Admin")


def _item_type_label(code: str) -> str:
    mapping = {
        "VIDEO": "Vídeo",
        "DOC": "Documento",
        "PDF": "PDF",
        "FORM": "Formulário",
    }
    return mapping.get(code, code.title())


def _question_type_label(code: str) -> str:
    mapping = {
        "ESSAY": "Dissertativa",
        "TRUE_OR_FALSE": "Verdadeiro ou falso",
        "SINGLE_CHOICE": "Múltipla escolha",
    }
    return mapping.get(code, code.replace("_", " ").title())


@bp.get("/trails")
def list_trails():
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_admin_trails()
    return jsonify(
        {
            "trails": [
                {
                    "id": row.id,
                    "name": row.name,
                    "author": row.author,
                    "created_date": (
                        row.created_date.isoformat() if row.created_date else None
                    ),
                }
                for row in rows
            ]
        }
    )


@bp.get("/trails/<int:trail_id>")
def get_trail(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    payload = repo.get_trail_builder_payload(trail_id)
    if not payload:
        return jsonify({"detail": "Rota não encontrada."}), 404
    return jsonify({"trail": payload})


@bp.get("/dashboard")
def dashboard():
    db = get_db()

    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_trails = db.query(func.count(TrailsORM.id)).scalar() or 0
    total_enrollments = db.query(func.count(UserTrailsORM.id)).scalar() or 0
    total_certificates = db.query(func.count(TrailCertificatesORM.id)).scalar() or 0

    enrollment_rows = (
        db.query(LkEnrollmentStatusORM.code, func.count(UserTrailsORM.id))
        .join(UserTrailsORM, UserTrailsORM.status_id == LkEnrollmentStatusORM.id)
        .group_by(LkEnrollmentStatusORM.code)
        .all()
    )
    enrollment_by_status = {
        (code or "UNKNOWN"): int(count or 0) for code, count in enrollment_rows
    }
    unknown_enrollments = (
        db.query(func.count(UserTrailsORM.id))
        .filter(UserTrailsORM.status_id.is_(None))
        .scalar()
        or 0
    )
    if unknown_enrollments:
        enrollment_by_status["UNDEFINED"] = int(unknown_enrollments)

    section_counts = {
        trail_id: count
        for trail_id, count in db.query(
            TrailSectionsORM.trail_id, func.count(TrailSectionsORM.id)
        )
        .group_by(TrailSectionsORM.trail_id)
        .all()
    }
    item_counts = {
        trail_id: count
        for trail_id, count in db.query(
            TrailItemsORM.trail_id, func.count(TrailItemsORM.id)
        )
        .group_by(TrailItemsORM.trail_id)
        .all()
    }

    recent_trails = (
        db.query(TrailsORM)
        .order_by(TrailsORM.created_date.desc().nullslast(), TrailsORM.id.desc())
        .limit(5)
        .all()
    )
    recent_trails_payload = [
        {
            "id": trail.id,
            "name": trail.name,
            "created_date": (
                trail.created_date.isoformat() if trail.created_date else None
            ),
            "sections": int(section_counts.get(trail.id, 0)),
            "items": int(item_counts.get(trail.id, 0)),
        }
        for trail in recent_trails
    ]

    recent_certificates = (
        db.query(
            TrailCertificatesORM.id,
            TrailCertificatesORM.issued_at,
            User.name_for_certificate,
            User.username,
            TrailsORM.name.label("trail_name"),
        )
        .join(User, User.user_id == TrailCertificatesORM.user_id)
        .join(TrailsORM, TrailsORM.id == TrailCertificatesORM.trail_id)
        .order_by(TrailCertificatesORM.issued_at.desc())
        .limit(5)
        .all()
    )
    recent_certificates_payload = [
        {
            "id": cert.id,
            "issued_at": cert.issued_at.isoformat(),
            "user": cert.name_for_certificate or cert.username,
            "trail": cert.trail_name,
        }
        for cert in recent_certificates
    ]

    top_trails = (
        db.query(
            TrailsORM.id,
            TrailsORM.name,
            func.count(UserTrailsORM.id).label("enrollments"),
            func.coalesce(
                func.sum(
                    case(
                        (LkEnrollmentStatusORM.code == "COMPLETED", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("completed"),
        )
        .outerjoin(UserTrailsORM, UserTrailsORM.trail_id == TrailsORM.id)
        .outerjoin(
            LkEnrollmentStatusORM, UserTrailsORM.status_id == LkEnrollmentStatusORM.id
        )
        .group_by(TrailsORM.id, TrailsORM.name)
        .order_by(func.count(UserTrailsORM.id).desc(), TrailsORM.name)
        .limit(5)
        .all()
    )
    top_trails_payload = [
        {
            "id": row.id,
            "name": row.name,
            "enrollments": int(row.enrollments or 0),
            "completed": int(row.completed or 0),
        }
        for row in top_trails
    ]

    return jsonify(
        {
            "summary": {
                "total_users": int(total_users),
                "total_trails": int(total_trails),
                "total_enrollments": int(total_enrollments),
                "total_certificates": int(total_certificates),
            },
            "enrollment_by_status": enrollment_by_status,
            "recent_trails": recent_trails_payload,
            "recent_certificates": recent_certificates_payload,
            "top_trails": top_trails_payload,
        }
    )


@bp.get("/trails/item-types")
def list_item_types():
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_item_types()
    return jsonify(
        {
            "item_types": [
                {"code": row.code, "label": _item_type_label(row.code)} for row in rows
            ]
        }
    )


@bp.get("/forms/question-types")
def list_question_types():
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_question_types()
    return jsonify(
        {
            "question_types": [
                {"code": row.code, "label": _question_type_label(row.code)}
                for row in rows
            ]
        }
    )


@bp.post("/trails")
def create_trail():
    data = request.get_json(silent=True) or {}
    try:
        payload = AdminTrailCreateIn.model_validate(data)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    enforce_csrf()

    db = get_db()
    repo = TrailsRepository(db)
    admin = g.current_admin

    sections_payload = [
        section.model_dump(mode="python") for section in payload.sections
    ]

    try:
        trail = repo.create_trail(
            name=payload.name,
            thumbnail_url=payload.thumbnail_url,
            description=payload.description,
            author=payload.author,
            created_by=getattr(admin, "user_id", None),
            sections=sections_payload,
        )
    except ValueError as exc:
        db.rollback()
        return jsonify({"detail": str(exc)}), 400
    except Exception:
        db.rollback()
        raise

    return (
        jsonify(
            {
                "trail": {
                    "id": trail.id,
                    "name": trail.name,
                }
            }
        ),
        201,
    )


@bp.put("/trails/<int:trail_id>")
def update_trail(trail_id: int):
    data = request.get_json(silent=True) or {}
    try:
        payload = AdminTrailCreateIn.model_validate(data)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    enforce_csrf()

    db = get_db()
    repo = TrailsRepository(db)
    sections_payload = [
        section.model_dump(mode="python") for section in payload.sections
    ]

    try:
        trail = repo.update_trail(
            trail_id=trail_id,
            name=payload.name,
            thumbnail_url=payload.thumbnail_url,
            description=payload.description,
            author=payload.author,
            sections=sections_payload,
        )
    except LookupError:
        db.rollback()
        return jsonify({"detail": "Rota não encontrada."}), 404
    except ValueError as exc:
        db.rollback()
        return jsonify({"detail": str(exc)}), 400
    except Exception:
        db.rollback()
        raise

    return jsonify({"trail": {"id": trail.id, "name": trail.name}})
