# app/routes/trail_items.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Literal, Optional, Tuple
from urllib.parse import urlparse
import os

from flask import Blueprint, abort, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.form_answers import FormAnswer as FormAnswerORM
from app.models.form_question_options import (
    FormQuestionOption as FormQuestionOptionORM,
)
from app.models.form_questions import FormQuestion as FormQuestionORM
from app.models.form_submissions import FormSubmission as FormSubmissionORM
from app.models.forms import Form as FormORM
from app.models.trail_items import TrailItems as TrailItemsORM
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.repositories.UserProgressRepository import UserProgressRepository
from app.services.security import enforce_csrf, get_current_user
from app.routes import format_validation_error


bp = Blueprint("trail_items", __name__, url_prefix="/trails")


QuestionKind = Literal["ESSAY", "TRUE_OR_FALSE", "SINGLE_CHOICE", "UNKNOWN"]
ResourceKind = Literal["PDF", "IMAGE", "OTHER"]


class FormOptionOut(BaseModel):
    id: int
    text: str
    order_index: int


class FormQuestionOut(BaseModel):
    id: int
    prompt: str
    type: QuestionKind
    required: bool
    order_index: int
    points: float
    options: list[FormOptionOut] = []


class FormOut(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    min_score_to_pass: float
    randomize_questions: Optional[bool] = None
    questions: list[FormQuestionOut]


class TrailItemDetailOut(BaseModel):
    id: int
    trail_id: int
    section_id: Optional[int] = None
    title: str
    type: Literal["VIDEO", "DOC", "FORM"]
    youtubeId: str
    duration_seconds: Optional[int] = None
    required_percentage: int = 70
    description_html: str = ""
    prev_item_id: Optional[int] = None
    next_item_id: Optional[int] = None
    form: Optional[FormOut] = None
    requires_completion: bool = False
    resource_url: Optional[str] = None
    resource_kind: Optional[ResourceKind] = None


class FormAnswerIn(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None

    @field_validator("answer_text")
    @classmethod
    def strip_answer(cls, value: Optional[str]):
        if value is None:
            return value
        return value.strip()


class FormSubmissionIn(BaseModel):
    answers: list[FormAnswerIn]
    duration_seconds: Optional[int] = None


class FormSubmissionAnswerOut(BaseModel):
    question_id: int
    is_correct: Optional[bool]
    points_awarded: Optional[float]


class FormSubmissionOut(BaseModel):
    submission_id: int
    score: float
    score_points: float
    max_points: float
    max_score: float
    passed: Optional[bool]
    requires_manual_review: bool
    answers: list[FormSubmissionAnswerOut]


def _extract_youtube_id(url: str) -> str:
    # aceita formatos: watch?v=, youtu.be/, /embed/, /shorts/
    import re

    if not url:
        return ""
    m = re.search(r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else ""


def _question_type_code(question: FormQuestionORM) -> QuestionKind:
    code = question.question_type.code if question.question_type else None
    if code in {"ESSAY", "TRUE_OR_FALSE", "SINGLE_CHOICE"}:
        return code  # type: ignore[return-value]
    return "UNKNOWN"


def _option_is_correct(option: FormQuestionOptionORM) -> Optional[bool]:
    if option.is_correct is not None:
        return option.is_correct
    if option.is_correct_yn is not None:
        return option.is_correct_yn.upper() == "Y"
    return None


def _classify_resource(url: str) -> Tuple[Optional[str], Optional[ResourceKind]]:
    cleaned = (url or "").strip()
    if not cleaned:
        return None, None

    parsed = urlparse(cleaned)
    path = parsed.path or ""
    _, ext = os.path.splitext(path.lower())

    if ext == ".pdf":
        return cleaned, "PDF"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}:
        return cleaned, "IMAGE"
    return cleaned, "OTHER"


def _question_is_required(question: FormQuestionORM) -> bool:
    if question.required is not None:
        return bool(question.required)
    if question.required_yn is not None:
        return question.required_yn.upper() == "Y"
    return False


def _form_randomize(form: FormORM) -> Optional[bool]:
    if form.randomize_questions is not None:
        return bool(form.randomize_questions)
    if form.randomize_questions_yn is not None:
        return form.randomize_questions_yn.upper() == "S"
    return None


def _load_item(db, trail_id: int, item_id: int) -> TrailItemsORM:
    item = (
        db.query(TrailItemsORM)
        .options(selectinload(TrailItemsORM.type))
        .filter(TrailItemsORM.id == item_id, TrailItemsORM.trail_id == trail_id)
        .first()
    )
    if not item:
        abort(404, description="Item não encontrado")
    return item


def _load_form(db, trail_item_id: int) -> FormORM:
    form = (
        db.query(FormORM)
        .options(
            selectinload(FormORM.questions).selectinload(FormQuestionORM.options),
            selectinload(FormORM.questions).selectinload(FormQuestionORM.question_type),
        )
        .filter(FormORM.trail_item_id == trail_item_id)
        .first()
    )
    if not form:
        abort(404, description="Formulário não encontrado para este item")
    return form


def _compute_prev_next(db, item: TrailItemsORM) -> tuple[Optional[int], Optional[int]]:
    trail_id = item.trail_id
    prev_id: Optional[int] = None
    next_id: Optional[int] = None

    if item.section_id is not None:
        prev_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == item.section_id,
                TrailItemsORM.order_index < (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.desc(), TrailItemsORM.id.desc())
            .first()
        )
        if prev_row:
            prev_id = prev_row[0]

        next_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id == item.section_id,
                TrailItemsORM.order_index > (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.asc(), TrailItemsORM.id.asc())
            .first()
        )
        if next_row:
            next_id = next_row[0]
    else:
        prev_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id.is_(None),
                TrailItemsORM.order_index < (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.desc(), TrailItemsORM.id.desc())
            .first()
        )
        if prev_row:
            prev_id = prev_row[0]

        next_row = (
            db.query(TrailItemsORM.id)
            .filter(
                TrailItemsORM.trail_id == trail_id,
                TrailItemsORM.section_id.is_(None),
                TrailItemsORM.order_index > (item.order_index or 0),
            )
            .order_by(TrailItemsORM.order_index.asc(), TrailItemsORM.id.asc())
            .first()
        )
        if next_row:
            next_id = next_row[0]

    return prev_id, next_id


def _build_locked_response(blocked_item: dict):
    title = (blocked_item.get("title") or "").strip()
    return (
        jsonify(
            {
                "detail": "Conclua o item obrigatório antes de prosseguir.",
                "reason": "item_locked",
                "blocked_item": {
                    "id": blocked_item.get("id"),
                    "title": title,
                },
            }
        ),
        423,
    )


@bp.get("/<int:trail_id>/items/<int:item_id>")
def get_item_detail(trail_id: int, item_id: int):
    db = get_db()
    user = get_current_user()
    item = _load_item(db, trail_id, item_id)

    user_trail_repo = UserTrailsRepository(db)
    blocker = user_trail_repo.find_blocking_item(user.user_id, trail_id, item_id)
    if blocker:
        return _build_locked_response(blocker)

    item_type = item.type.code if item.type is not None else "DOC"
    youtube_id = _extract_youtube_id(item.url or "") if item_type == "VIDEO" else ""
    prev_id, next_id = _compute_prev_next(db, item)

    description_html = ""
    resource_url: Optional[str] = None
    resource_kind: Optional[ResourceKind] = None
    form_payload: Optional[FormOut] = None

    if item_type == "FORM":
        form = _load_form(db, item.id)
        questions_out: list[FormQuestionOut] = []
        for question in sorted(form.questions, key=lambda q: (q.order_index, q.id)):
            q_type = _question_type_code(question)
            options_out: list[FormOptionOut] = []
            for option in sorted(question.options, key=lambda o: (o.order_index, o.id)):
                option_text = option.option_text or ""
                options_out.append(
                    FormOptionOut(
                        id=option.id,
                        text=option_text,
                        order_index=option.order_index or 0,
                    )
                )

            questions_out.append(
                FormQuestionOut(
                    id=question.id,
                    prompt=question.prompt or "",
                    type=q_type,
                    required=_question_is_required(question),
                    order_index=question.order_index or 0,
                    points=float(question.points or Decimal("0")),
                    options=options_out,
                )
            )

        form_payload = FormOut(
            id=form.id,
            title=form.title,
            description=form.description,
            min_score_to_pass=float(form.min_score_to_pass or Decimal("0")),
            randomize_questions=_form_randomize(form),
            questions=questions_out,
        )
        description_html = form.description or ""
    elif item_type == "DOC":
        resource_url, resource_kind = _classify_resource(item.url or "")

    data = TrailItemDetailOut(
        id=item.id,
        trail_id=item.trail_id,
        section_id=item.section_id,
        title=item.title or "",
        type=item_type,
        youtubeId=youtube_id,
        duration_seconds=item.duration_seconds,
        required_percentage=70,
        description_html=description_html,
        prev_item_id=prev_id,
        next_item_id=next_id,
        form=form_payload,
        requires_completion=item.completion_required(),
        resource_url=resource_url,
        resource_kind=resource_kind,
    ).model_dump(mode="json")
    return jsonify(data)


@bp.post("/<int:trail_id>/items/<int:item_id>/form-submissions")
def submit_form(trail_id: int, item_id: int):
    db = get_db()
    payload_raw = request.get_json(silent=True) or {}
    try:
        payload = FormSubmissionIn.model_validate(payload_raw)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    enforce_csrf()
    user = get_current_user()

    item = _load_item(db, trail_id, item_id)
    item_type = item.type.code if item.type is not None else "DOC"
    if item_type != "FORM":
        abort(400, description="Este item não é um formulário")

    user_trail_repo = UserTrailsRepository(db)
    blocker = user_trail_repo.find_blocking_item(user.user_id, trail_id, item_id)
    if blocker:
        return _build_locked_response(blocker)

    form = _load_form(db, item.id)

    # garante matrícula
    user_trail_repo.ensure_enrollment(user.user_id, trail_id)

    question_map: Dict[int, FormQuestionORM] = {
        question.id: question
        for question in sorted(form.questions, key=lambda q: (q.order_index, q.id))
    }

    provided_answers = {answer.question_id: answer for answer in payload.answers}

    invalid_questions = [
        answer.question_id
        for answer in payload.answers
        if answer.question_id not in question_map
    ]
    if invalid_questions:
        return (
            jsonify(
                {
                    "detail": "Uma ou mais questões informadas são inválidas para este formulário",
                    "invalid_questions": invalid_questions,
                }
            ),
            422,
        )

    missing_required = [
        q.id
        for q in question_map.values()
        if _question_is_required(q)
        and (
            q.id not in provided_answers or not _has_response(provided_answers[q.id], q)
        )
    ]
    if missing_required:
        return (
            jsonify(
                {
                    "detail": "Responda todas as questões obrigatórias",
                    "missing_questions": missing_required,
                }
            ),
            422,
        )

    auto_total_points = Decimal("0")
    auto_scored_points = Decimal("0")
    requires_manual_review = False
    answer_outputs: list[FormSubmissionAnswerOut] = []
    answer_entities: list[FormAnswerORM] = []

    for question in question_map.values():
        q_type = _question_type_code(question)
        answer_in = provided_answers.get(question.id)

        if q_type == "ESSAY":
            response_text = (
                answer_in.answer_text.strip()
                if answer_in and answer_in.answer_text
                else None
            )
            if _question_is_required(question) or response_text:
                requires_manual_review = True
            answer_entities.append(
                FormAnswerORM(
                    question_id=question.id,
                    answer_text=response_text,
                    is_correct=None,
                    points_awarded=None,
                )
            )
            answer_outputs.append(
                FormSubmissionAnswerOut(
                    question_id=question.id,
                    is_correct=None,
                    points_awarded=None,
                )
            )
            continue

        # perguntas objetivas
        points_value = question.points if question.points is not None else Decimal("0")
        auto_total_points += points_value
        selected_option_id = answer_in.selected_option_id if answer_in else None

        selected_option: Optional[FormQuestionOptionORM] = None
        if selected_option_id is not None:
            selected_option = next(
                (opt for opt in question.options if opt.id == selected_option_id),
                None,
            )
            if not selected_option:
                return (
                    jsonify(
                        {
                            "detail": f"Opção inválida para a questão {question.id}",
                            "question_id": question.id,
                        }
                    ),
                    422,
                )

        is_correct = False
        points_awarded: Decimal | None = Decimal("0")
        if selected_option is not None:
            option_correct = _option_is_correct(selected_option)
            is_correct = option_correct is True
            if option_correct is True:
                auto_scored_points += points_value
                points_awarded = points_value
        else:
            is_correct = False

        answer_entities.append(
            FormAnswerORM(
                question_id=question.id,
                selected_option_id=selected_option.id if selected_option else None,
                is_correct=is_correct,
                points_awarded=points_awarded,
            )
        )
        answer_outputs.append(
            FormSubmissionAnswerOut(
                question_id=question.id,
                is_correct=is_correct,
                points_awarded=(
                    float(points_awarded) if points_awarded is not None else None
                ),
            )
        )

    max_points = float(auto_total_points) if auto_total_points > 0 else 0.0
    score_points = float(auto_scored_points)
    score_percent = (
        float((auto_scored_points / auto_total_points) * Decimal(100))
        if auto_total_points > 0
        else 0.0
    )

    min_score = float(form.min_score_to_pass or Decimal("0"))
    passed: Optional[bool]
    if requires_manual_review:
        passed = None
    else:
        passed = score_percent >= min_score

    submission = FormSubmissionORM(
        form_id=form.id,
        user_id=user.user_id,
        submitted_at=datetime.now(timezone.utc),
        score=Decimal(str(round(score_percent, 2))),
        passed=passed,
        duration_seconds=payload.duration_seconds,
    )
    submission.answers = answer_entities
    db.add(submission)
    db.flush()
    db.commit()

    if passed is True:
        UserProgressRepository(db).upsert_item_progress(
            user.user_id,
            item.id,
            "COMPLETED",
            last_passed_submission_id=submission.id,
        )

    response_body = FormSubmissionOut(
        submission_id=submission.id,
        score=round(score_percent, 2),
        score_points=round(score_points, 2),
        max_points=round(max_points, 2),
        max_score=100.0 if auto_total_points > 0 else 0.0,
        passed=passed,
        requires_manual_review=requires_manual_review,
        answers=answer_outputs,
    )
    return jsonify(response_body.model_dump(mode="json"))


def _has_response(answer: FormAnswerIn, question: FormQuestionORM) -> bool:
    q_type = _question_type_code(question)
    if q_type == "ESSAY":
        return bool(answer.answer_text and answer.answer_text.strip())
    return answer.selected_option_id is not None
