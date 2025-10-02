from __future__ import annotations

"""Performance benchmarks for API endpoints and database queries."""

from datetime import date, datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import Callable, Iterable

import pytest
from sqlalchemy import event, func, select

from app.models.forms import Form as FormORM
from app.models.form_question_options import FormQuestionOption as FormQuestionOptionORM
from app.models.form_questions import FormQuestion as FormQuestionORM
from app.models.form_submissions import FormSubmission as FormSubmissionORM
from app.models.lk_enrollment_status import LkEnrollmentStatus as LkEnrollmentStatusORM
from app.models.lk_item_type import LkItemType as LkItemTypeORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM
from app.models.lk_question_type import LkQuestionType as LkQuestionTypeORM
from app.models.trail_included_items import (
    TrailIncludedItems as TrailIncludedItemsORM,
)
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_requirements import TrailRequirements as TrailRequirementsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.trail_target_audience import (
    TrailTargetAudience as TrailTargetAudienceORM,
)
from app.models.trails import Trails as TrailsORM
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.user_trails import UserTrails as UserTrailsORM
from app.models.users import Sex, User
from app.models.form_answers import FormAnswer as FormAnswerORM
from app.models.roles import RolesEnum
from app.repositories.TrailsRepository import TrailsRepository
from app.repositories.UserProgressRepository import UserProgressRepository
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.repositories.UsersRepository import UsersRepository
from app.services import security
from app.services.security import hash_password


_SQLITE_PK_LISTENERS_REGISTERED = False
_SQLITE_PK_COUNTERS: dict[type, int] = {}


BenchmarkFn = Callable[[int], None]


def _ensure_lookup(session, model, code: str):
    existing = session.query(model).filter_by(code=code).first()
    if existing:
        return existing
    instance = model(code=code)
    session.add(instance)
    session.flush()
    return instance


@pytest.fixture
def performance_data(db_session):
    """Populate the database with a representative dataset for benchmarks."""

    global _SQLITE_PK_LISTENERS_REGISTERED

    if (
        db_session.bind
        and db_session.bind.dialect.name == "sqlite"
        and not _SQLITE_PK_LISTENERS_REGISTERED
    ):
        def _sqlite_assign_pk(mapper, connection, target):
            if getattr(target, "id", None):
                return
            model_cls = mapper.class_
            next_id = _SQLITE_PK_COUNTERS.get(model_cls)
            if next_id is None:
                table = mapper.local_table
                current = connection.execute(select(func.max(table.c.id))).scalar()
                next_id = (current or 0) + 1
            target.id = next_id
            _SQLITE_PK_COUNTERS[model_cls] = next_id + 1

        for model in (
            FormSubmissionORM,
            FormAnswerORM,
            UserItemProgressORM,
            UserTrailsORM,
        ):
            event.listen(model, "before_insert", _sqlite_assign_pk, propagate=True)
        _SQLITE_PK_LISTENERS_REGISTERED = True

    item_types = {
        code: _ensure_lookup(db_session, LkItemTypeORM, code)
        for code in ("DOC", "VIDEO", "FORM")
    }
    enrollment_statuses = {
        code: _ensure_lookup(db_session, LkEnrollmentStatusORM, code)
        for code in ("ENROLLED", "IN_PROGRESS", "COMPLETED")
    }
    progress_statuses = {
        code: _ensure_lookup(db_session, LkProgressStatusORM, code)
        for code in ("NOT_STARTED", "IN_PROGRESS", "COMPLETED")
    }
    question_types = {
        code: _ensure_lookup(db_session, LkQuestionTypeORM, code)
        for code in ("ESSAY", "TRUE_OR_FALSE", "SINGLE_CHOICE")
    }

    trail = TrailsORM(
        thumbnail_url="https://example.com/thumb.png",
        name="Performance Trail",
        author="Benchmark Bot",
        description="Trail used for performance measurements.",
        created_date=date.today(),
    )
    db_session.add(trail)
    db_session.flush()

    section_intro = TrailSectionsORM(
        trail_id=trail.id, title="Introdução", order_index=1
    )
    section_quiz = TrailSectionsORM(trail_id=trail.id, title="Quiz", order_index=2)
    db_session.add_all([section_intro, section_quiz])
    db_session.flush()

    doc_item = TrailItemsORM(
        url="https://example.com/doc",
        order_index=1,
        trail_id=trail.id,
        section_id=section_intro.id,
        title="Documento inicial",
        item_type_id=item_types["DOC"].id,
        requires_completion=True,
    )
    video_item = TrailItemsORM(
        url="https://youtu.be/dQw4w9WgXcQ",
        order_index=2,
        trail_id=trail.id,
        section_id=section_intro.id,
        title="Vídeo motivacional",
        item_type_id=item_types["VIDEO"].id,
        duration_seconds=120,
        requires_completion=True,
    )
    form_item = TrailItemsORM(
        url="https://example.com/form",
        order_index=1,
        trail_id=trail.id,
        section_id=section_quiz.id,
        title="Quiz final",
        item_type_id=item_types["FORM"].id,
        requires_completion=False,
    )
    db_session.add_all([doc_item, video_item, form_item])
    db_session.flush()

    next_form_id = (db_session.query(func.max(FormORM.id)).scalar() or 0) + 1
    form = FormORM(
        id=next_form_id,
        trail_item_id=form_item.id,
        title="Quiz Final",
        description="Avaliação dos conhecimentos",
        min_score_to_pass=Decimal("70.00"),
    )
    db_session.add(form)
    db_session.flush()

    next_question_id = (
        db_session.query(func.max(FormQuestionORM.id)).scalar() or 0
    ) + 1
    question = FormQuestionORM(
        id=next_question_id,
        form_id=form.id,
        prompt="Quanto é 2 + 2?",
        question_type_id=question_types["SINGLE_CHOICE"].id,
        required=True,
        order_index=1,
        points=Decimal("10.00"),
    )
    db_session.add(question)
    db_session.flush()

    next_option_id = (
        db_session.query(func.max(FormQuestionOptionORM.id)).scalar() or 0
    ) + 1
    option_correct = FormQuestionOptionORM(
        id=next_option_id,
        question_id=question.id,
        option_text="4",
        is_correct=True,
        order_index=1,
    )
    option_wrong = FormQuestionOptionORM(
        id=next_option_id + 1,
        question_id=question.id,
        option_text="5",
        is_correct=False,
        order_index=2,
    )
    db_session.add_all([option_correct, option_wrong])
    db_session.flush()

    included = TrailIncludedItemsORM(
        trail_id=trail.id, text_val="Acesso vitalício", ord=1
    )
    requirement = TrailRequirementsORM(
        trail_id=trail.id, text_val="Conhecimentos básicos de Python", ord=1
    )
    audience = TrailTargetAudienceORM(
        trail_id=trail.id, text_val="Profissionais de tecnologia", ord=1
    )
    db_session.add_all([included, requirement, audience])

    db_session.flush()

    users_repo = UsersRepository(db_session)
    plain_password = "PerfPass123!"
    user = users_repo.CreateUser(
        email="perf-user@example.com",
        password_hash=hash_password(plain_password),
        name_for_certificate="Usuário Performance",
        username="perfuser",
        sex=Sex.Male,
        role=RolesEnum.User,
        birthday="1990-01-01",
    )

    enrollment = UserTrailsORM(
        user_id=user.user_id,
        trail_id=trail.id,
        status_id=enrollment_statuses["ENROLLED"].id,
        progress_percent=0,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(enrollment)
    db_session.flush()

    now = datetime.now(timezone.utc)
    progress_doc = UserItemProgressORM(
        user_id=user.user_id,
        trail_item_id=doc_item.id,
        status_id=progress_statuses["COMPLETED"].id,
        progress_value=100,
        completed_at=now,
        last_interaction=now,
        last_interaction_utc=now,
        completed_at_utc=now,
    )
    progress_video = UserItemProgressORM(
        user_id=user.user_id,
        trail_item_id=video_item.id,
        status_id=progress_statuses["COMPLETED"].id,
        progress_value=video_item.duration_seconds,
        completed_at=now,
        last_interaction=now,
        last_interaction_utc=now,
        completed_at_utc=now,
    )
    db_session.add_all([progress_doc, progress_video])
    db_session.flush()

    UserTrailsRepository(db_session).sync_user_trail_progress(user.user_id, trail.id)
    db_session.refresh(user)

    return {
        "user": user,
        "password": plain_password,
        "trail": trail,
        "sections": {
            "intro": section_intro,
            "quiz": section_quiz,
        },
        "items": {
            "doc": doc_item,
            "video": video_item,
            "form": form_item,
        },
        "form": form,
        "question": question,
        "options": {
            "correct": option_correct,
            "wrong": option_wrong,
        },
    }


@pytest.fixture
def authenticated_user(monkeypatch, performance_data):
    user: User = performance_data["user"]

    monkeypatch.setattr(security, "get_current_user", lambda: user)
    monkeypatch.setattr(
        security, "get_current_user_id", lambda req=None: str(user.user_id)
    )
    monkeypatch.setattr(security, "enforce_csrf", lambda request_obj=None: None)

    from app.routes import me as me_routes
    from app.routes import trails as trails_routes
    from app.routes import user_trails as user_trails_routes
    from app.routes import trail_items as trail_items_routes
    from app.repositories import UserTrailsRepository as user_trails_module

    monkeypatch.setattr(
        me_routes, "get_current_user_id", lambda req=None: str(user.user_id)
    )
    monkeypatch.setattr(trails_routes, "enforce_csrf", lambda request_obj=None: None)
    monkeypatch.setattr(trail_items_routes, "get_current_user", lambda: user)
    monkeypatch.setattr(trail_items_routes, "enforce_csrf", lambda request_obj=None: None)
    monkeypatch.setattr(user_trails_routes, "get_current_user", lambda: user)
    monkeypatch.setattr(
        user_trails_routes, "get_current_user_id", lambda req=None: str(user.user_id)
    )
    monkeypatch.setattr(user_trails_routes, "enforce_csrf", lambda request_obj=None: None)
    monkeypatch.setattr(
        user_trails_module, "get_current_user_id", lambda req=None: str(user.user_id)
    )

    return user


def _run_benchmarks(cases: Iterable[tuple[str, int, BenchmarkFn]]):
    results = []
    for label, iterations, fn in cases:
        start = perf_counter()
        for i in range(iterations):
            fn(i)
        elapsed = perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000 if iterations else 0.0
        rps = (iterations / elapsed) if elapsed > 0 else float("inf")
        results.append((label, iterations, elapsed, rps, avg_ms))
    return results


def _print_results(header: str, results: list[tuple[str, int, float, float, float]]):
    print(f"\n{header}")
    for label, iterations, elapsed, rps, avg_ms in results:
        print(
            f"- {label}: {iterations} iterações em {elapsed:.4f}s | "
            f"RPS≈{rps:.2f} | tempo médio≈{avg_ms:.2f} ms"
        )


@pytest.mark.performance
def test_performance_endpoints(
    client, db_session, performance_data, authenticated_user
):
    trail = performance_data["trail"]
    items = performance_data["items"]
    question = performance_data["question"]
    options = performance_data["options"]
    user = performance_data["user"]
    password = performance_data["password"]

    def get_json(path: str, expected_status: int = 200):
        response = client.get(path)
        assert response.status_code == expected_status
        return response

    def post_json(path: str, payload: dict, expected_status: int = 200):
        response = client.post(path, json=payload)
        assert response.status_code == expected_status
        return response

    def put_json(path: str, payload: dict, expected_status: int = 200):
        response = client.put(path, json=payload)
        assert response.status_code == expected_status
        return response

    endpoint_cases: list[tuple[str, int, BenchmarkFn]] = [
        ("GET /trails/showcase", 5, lambda _: get_json("/trails/showcase")),
        ("GET /trails", 5, lambda _: get_json("/trails/?page=1&page_size=10")),
        (
            "GET /trails/<id>",
            5,
            lambda _: get_json(f"/trails/{trail.id}"),
        ),
        (
            "GET /trails/<id>/sections",
            5,
            lambda _: get_json(f"/trails/{trail.id}/sections"),
        ),
        (
            "GET /trails/<id>/sections/<section_id>/items",
            5,
            lambda _: get_json(
                f"/trails/{trail.id}/sections/{performance_data['sections']['intro'].id}/items"
            ),
        ),
        (
            "GET /trails/<id>/sections-with-items",
            5,
            lambda _: get_json(f"/trails/{trail.id}/sections-with-items"),
        ),
        (
            "GET /trails/<id>/included-items",
            5,
            lambda _: get_json(f"/trails/{trail.id}/included-items"),
        ),
        (
            "GET /trails/<id>/requirements",
            5,
            lambda _: get_json(f"/trails/{trail.id}/requirements"),
        ),
        (
            "GET /trails/<id>/audience",
            5,
            lambda _: get_json(f"/trails/{trail.id}/audience"),
        ),
        (
            "GET /trails/<id>/learn",
            5,
            lambda _: get_json(f"/trails/{trail.id}/learn"),
        ),
        (
            "PUT /trails/<id>/items/<item_id>/progress",
            3,
            lambda _: put_json(
                f"/trails/{trail.id}/items/{items['doc'].id}/progress",
                {"status": "COMPLETED", "progress_value": 100},
            ),
        ),
        (
            "GET /trails/<id>/items/<item_id>",
            5,
            lambda _: get_json(
                f"/trails/{trail.id}/items/{items['form'].id}"
            ),
        ),
        (
            "POST /trails/<id>/items/<item_id>/form-submissions",
            3,
            lambda _: post_json(
                f"/trails/{trail.id}/items/{items['form'].id}/form-submissions",
                {
                    "answers": [
                        {
                            "question_id": question.id,
                            "selected_option_id": options["correct"].id,
                        }
                    ],
                    "duration_seconds": 30,
                },
            ),
        ),
        (
            "POST /auth/register",
            3,
            lambda idx: post_json(
                "/auth/register",
                {
                    "email": f"perf-register-{idx}@example.com",
                    "password": "PerfPass123!",
                    "name_for_certificate": "Usuário Registro",
                    "sex": "M",
                    "birthday": "1990-01-01",
                    "username": f"perf-register-{idx}",
                    "role": "User",
                    "remember": False,
                },
            ),
        ),
        (
            "POST /auth/login",
            5,
            lambda _: post_json(
                "/auth/login",
                {"email": user.email, "password": password, "remember": False},
            ),
        ),
        ("POST /auth/logout", 5, lambda _: post_json("/auth/logout", {})),
        ("GET /me", 5, lambda _: get_json("/me")),
        (
            "GET /user-trails/<trail_id>/progress",
            5,
            lambda _: get_json(f"/user-trails/{trail.id}/progress"),
        ),
        (
            "GET /user-trails/<trail_id>/items-progress",
            5,
            lambda _: get_json(f"/user-trails/{trail.id}/items-progress"),
        ),
        (
            "GET /user-trails/<trail_id>/sections-progress",
            5,
            lambda _: get_json(f"/user-trails/{trail.id}/sections-progress"),
        ),
        (
            "POST /user-trails/<trail_id>/enroll",
            3,
            lambda _: post_json(f"/user-trails/{trail.id}/enroll", {}),
        ),
    ]

    results = _run_benchmarks(endpoint_cases)
    _print_results("Resultados de performance dos endpoints", results)

    # Garante que todas as métricas produziram valores positivos para tempo e RPS.
    for _, iterations, elapsed, rps, _ in results:
        assert iterations > 0
        assert elapsed >= 0
        assert rps >= 0


@pytest.mark.performance
def test_performance_queries(db_session, performance_data, monkeypatch):
    user: User = performance_data["user"]
    trail = performance_data["trail"]
    items = performance_data["items"]

    from app.repositories import UserTrailsRepository as user_trails_module

    monkeypatch.setattr(
        security, "get_current_user_id", lambda req=None: str(user.user_id)
    )
    monkeypatch.setattr(
        user_trails_module, "get_current_user_id", lambda req=None: str(user.user_id)
    )

    users_repo = UsersRepository(db_session)
    trails_repo = TrailsRepository(db_session)
    user_trails_repo = UserTrailsRepository(db_session)
    user_progress_repo = UserProgressRepository(db_session)

    def run_users_create(idx: int):
        email = f"perf-extra-{idx}@example.com"
        username = f"perf-extra-{idx}"
        users_repo.CreateUser(
            email=email,
            password_hash=hash_password("PerfPass123!"),
            name_for_certificate="Usuário Extra",
            username=username,
            sex=Sex.Female,
            role=RolesEnum.User,
            birthday="1995-05-15",
        )

    def toggle_role(_: int):
        current = user.role.code if user.role else "User"
        target = RolesEnum.Manager if current == "User" else RolesEnum.User
        users_repo.UpdateUserRole(user, target)

    def toggle_sex(_: int):
        current = user.sex.code if user.sex else "M"
        target = Sex.Female if current == "M" else Sex.Male
        users_repo.UpdateUserSex(user, target)

    def upsert_progress(_: int):
        user_progress_repo.upsert_item_progress(
            user.user_id,
            items["doc"].id,
            "IN_PROGRESS",
            progress_value=80,
        )

    query_cases: list[tuple[str, int, BenchmarkFn]] = [
        ("UsersRepository.GetUserByEmail", 10, lambda _: users_repo.GetUserByEmail(user.email)),
        ("UsersRepository.GetUserByUsername", 10, lambda _: users_repo.GetUserByUsername(user.username)),
        ("UsersRepository.GetUserById", 10, lambda _: users_repo.GetUserById(user.user_id)),
        ("UsersRepository.ExistsEmail", 10, lambda _: users_repo.ExistsEmail(user.email)),
        ("UsersRepository.ExistsUsername", 10, lambda _: users_repo.ExistsUsername(user.username)),
        ("UsersRepository.CreateUser", 3, run_users_create),
        ("UsersRepository.UpdateUserRole", 4, toggle_role),
        ("UsersRepository.UpdateUserSex", 4, toggle_sex),
        ("TrailsRepository.list_showcase", 10, lambda _: trails_repo.list_showcase()),
        (
            "TrailsRepository.list_all",
            10,
            lambda _: trails_repo.list_all(offset=0, limit=10),
        ),
        (
            "TrailsRepository.get_trail",
            10,
            lambda _: trails_repo.get_trail(trail.id),
        ),
        (
            "TrailsRepository.list_sections",
            10,
            lambda _: trails_repo.list_sections(trail.id, offset=0, limit=10),
        ),
        (
            "TrailsRepository.list_section_items",
            10,
            lambda _: trails_repo.list_section_items(
                trail.id, performance_data["sections"]["intro"].id, offset=0, limit=10
            ),
        ),
        (
            "TrailsRepository.list_sections_with_items",
            10,
            lambda _: trails_repo.list_sections_with_items(trail.id),
        ),
        (
            "TrailsRepository.list_included_items",
            10,
            lambda _: trails_repo.list_included_items(trail.id),
        ),
        (
            "TrailsRepository.list_requirements",
            10,
            lambda _: trails_repo.list_requirements(trail.id),
        ),
        (
            "TrailsRepository.list_audience",
            10,
            lambda _: trails_repo.list_audience(trail.id),
        ),
        (
            "UserTrailsRepository.count_items_in_trail",
            10,
            lambda _: user_trails_repo.count_items_in_trail(trail.id),
        ),
        (
            "UserTrailsRepository.get_progress_for_current_user",
            10,
            lambda _: user_trails_repo.get_progress_for_current_user(trail.id),
        ),
        (
            "UserTrailsRepository.get_progress_for_user",
            10,
            lambda _: user_trails_repo.get_progress_for_user(user.user_id, trail.id),
        ),
        (
            "UserTrailsRepository.ensure_enrollment",
            5,
            lambda _: user_trails_repo.ensure_enrollment(user.user_id, trail.id),
        ),
        (
            "UserTrailsRepository.sync_user_trail_progress",
            5,
            lambda _: user_trails_repo.sync_user_trail_progress(user.user_id, trail.id),
        ),
        (
            "UserTrailsRepository.get_progress_map_for_user",
            10,
            lambda _: user_trails_repo.get_progress_map_for_user(user.user_id, [trail.id]),
        ),
        (
            "UserTrailsRepository.find_blocking_item",
            10,
            lambda _: user_trails_repo.find_blocking_item(
                user.user_id, trail.id, items["form"].id
            ),
        ),
        (
            "UserTrailsRepository.get_items_progress",
            10,
            lambda _: user_trails_repo.get_items_progress(user.user_id, trail.id),
        ),
        (
            "UserTrailsRepository.get_sections_progress",
            10,
            lambda _: user_trails_repo.get_sections_progress(user.user_id, trail.id),
        ),
        (
            "UserTrailsRepository.get_first_trail_item_id",
            10,
            lambda _: user_trails_repo.get_first_trail_item_id(trail.id),
        ),
        ("UserProgressRepository.upsert_item_progress", 5, upsert_progress),
    ]

    results = _run_benchmarks(query_cases)
    _print_results("Resultados de performance das queries", results)

    for _, iterations, elapsed, rps, _ in results:
        assert iterations > 0
        assert elapsed >= 0
        assert rps >= 0
