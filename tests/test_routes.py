import uuid
from datetime import date, datetime, timezone

import pytest

from app.core.settings import settings
from app.models.lk_item_type import LkItemType
from app.models.lk_progress_status import LkProgressStatus
from app.models.trail_included_items import TrailIncludedItems
from app.models.trail_items import TrailItems
from app.models.trail_requirements import TrailRequirements
from app.models.trail_sections import TrailSections
from app.models.trail_target_audience import TrailTargetAudience
from app.models.trails import Trails
from app.models.user_item_progress import UserItemProgress
from app.models.user_trails import UserTrails
from app.models.users import Sex
from app.models.roles import RolesEnum
from app.repositories.UsersRepository import UsersRepository
from app.services.security import hash_password, sign_session


# ---------- helpers ----------


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}@example.com"


def unique_username(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def ensure_item_type(db_session, code: str) -> LkItemType:
    item_type = db_session.query(LkItemType).filter_by(code=code).first()
    if not item_type:
        item_type = LkItemType(code=code)
        db_session.add(item_type)
        db_session.commit()
    return item_type


def ensure_progress_status(db_session, code: str) -> LkProgressStatus:
    status = db_session.query(LkProgressStatus).filter_by(code=code).first()
    if not status:
        status = LkProgressStatus(code=code)
        db_session.add(status)
        db_session.commit()
    return status


def create_user_with_token(db_session):
    repo = UsersRepository(db_session)
    email = unique_email()
    username = unique_username()
    user = repo.CreateUser(
        email=email,
        password_hash=hash_password("secret123"),
        name_for_certificate="Test User",
        username=username,
        sex=Sex.NotSpecified,
        role=RolesEnum.User,
        birthday="1990-01-01",
        social_name="Tester",
    )
    token = sign_session(
        {
            "id": user.user_id,
            "email": user.email,
            "role": user.role.code,
            "username": user.username,
        }
    )
    return user, token


def register_user_via_api(client):
    email = unique_email("apiuser")
    username = unique_username("apiuser")
    payload = {
        "email": email,
        "password": "secret123",
        "name_for_certificate": "API User",
        "sex": "NotSpecified",
        "birthday": "1990-01-01",
        "username": username,
        "social_name": "API User",
        "role": RolesEnum.User.value,
    }
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()["user"]


def create_trail(
    db_session,
    *,
    name: str,
    created_date: date | None = None,
    author: str = "Autor Teste",
    description: str = "Descrição da trilha",
    review: float = 4.5,
) -> Trails:
    trail = Trails(
        name=name,
        thumbnail_url=f"https://example.com/{uuid.uuid4().hex}.png",
        author=author,
        description=description,
        review=review,
        created_date=created_date or date.today(),
    )
    db_session.add(trail)
    db_session.commit()
    return trail


def create_trail_with_content(
    db_session, *, name: str = "Trilha Completa", created_date: date | None = None
):
    trail = create_trail(
        db_session,
        name=name,
        created_date=created_date or date(2023, 1, 1),
        description="Trilha completa para testes",
    )

    section_intro = TrailSections(
        trail_id=trail.id, title="Introdução", order_index=1
    )
    section_advanced = TrailSections(
        trail_id=trail.id, title="Módulo Avançado", order_index=2
    )
    db_session.add_all([section_intro, section_advanced])
    db_session.flush()

    video_type = ensure_item_type(db_session, "VIDEO")
    doc_type = ensure_item_type(db_session, "DOC")
    form_type = ensure_item_type(db_session, "FORM")

    item_video_intro = TrailItems(
        trail_id=trail.id,
        section_id=section_intro.id,
        title="Boas-vindas",
        url="https://www.youtube.com/watch?v=video12345",
        duration_seconds=120,
        order_index=1,
        item_type_id=video_type.id,
    )
    item_doc = TrailItems(
        trail_id=trail.id,
        section_id=section_intro.id,
        title="Material complementar",
        url="https://example.com/doc1",
        duration_seconds=60,
        order_index=2,
        item_type_id=doc_type.id,
    )
    item_video_advanced = TrailItems(
        trail_id=trail.id,
        section_id=section_advanced.id,
        title="Aula prática",
        url="https://www.youtube.com/embed/video67890",
        duration_seconds=180,
        order_index=1,
        item_type_id=video_type.id,
    )
    item_form = TrailItems(
        trail_id=trail.id,
        section_id=None,
        title="Formulário final",
        url="https://example.com/formulario",
        duration_seconds=None,
        order_index=5,
        item_type_id=form_type.id,
    )
    db_session.add_all([item_video_intro, item_doc, item_video_advanced, item_form])
    db_session.flush()

    included1 = TrailIncludedItems(
        trail_id=trail.id, text_val="Acesso vitalício", ord=1
    )
    included2 = TrailIncludedItems(
        trail_id=trail.id, text_val="Comunidade exclusiva", ord=2
    )
    requirement1 = TrailRequirements(
        trail_id=trail.id, text_val="Computador com internet", ord=1
    )
    requirement2 = TrailRequirements(
        trail_id=trail.id, text_val="Vontade de aprender", ord=2
    )
    audience1 = TrailTargetAudience(
        trail_id=trail.id, text_val="Iniciantes na área", ord=1
    )
    audience2 = TrailTargetAudience(
        trail_id=trail.id, text_val="Profissionais em transição", ord=2
    )

    db_session.add_all(
        [
            included1,
            included2,
            requirement1,
            requirement2,
            audience1,
            audience2,
        ]
    )
    db_session.commit()

    return {
        "trail": trail,
        "sections": [section_intro, section_advanced],
        "items": [item_video_intro, item_doc, item_video_advanced, item_form],
    }


# ---------- tests: /me ----------


def test_me_requires_auth_cookie(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, db_session):
    user = register_user_via_api(client)

    resp = client.get("/me")
    assert resp.status_code == 200
    payload = resp.get_json()["user"]

    assert payload["user_id"] == user["user_id"]
    assert payload["email"] == user["email"]
    assert payload["username"] == user["username"]
    assert payload["role"] == user["role"]
    assert payload["sex"] == user["sex"]


# ---------- tests: /trails list/detail ----------


def test_get_trails_showcase_orders_by_created_date(client, db_session):
    create_trail(db_session, name="Trail Antiga", created_date=date(2021, 1, 1))
    create_trail(db_session, name="Trail Intermediária", created_date=date(2022, 6, 1))
    create_trail(db_session, name="Trail Recente", created_date=date(2023, 3, 1))

    resp = client.get("/trails/showcase")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.get_json()["trails"]]
    assert names == ["Trail Recente", "Trail Intermediária", "Trail Antiga"]


def test_get_trails_returns_all_sorted_by_name(client, db_session):
    create_trail(db_session, name="Zeta Trail")
    create_trail(db_session, name="Alpha Trail")
    create_trail(db_session, name="Beta Trail")

    resp = client.get("/trails/")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.get_json()["trails"]]
    assert names == ["Alpha Trail", "Beta Trail", "Zeta Trail"]


def test_get_trail_returns_single_trail(client, db_session):
    trail = create_trail(db_session, name="Trilha Única")

    resp = client.get(f"/trails/{trail.id}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["id"] == trail.id
    assert payload["name"] == trail.name
    assert payload["thumbnail_url"] == trail.thumbnail_url


# ---------- tests: /trails nested resources ----------


def test_get_sections_returns_sections_ordered(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/sections")
    assert resp.status_code == 200
    sections = resp.get_json()
    titles = [s["title"] for s in sections]
    assert titles == ["Introdução", "Módulo Avançado"]
    order_indexes = [s["order_index"] for s in sections]
    assert order_indexes == [1, 2]


def test_get_section_items_returns_items_with_type(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    section = data["sections"][0]

    resp = client.get(f"/trails/{trail.id}/sections/{section.id}/items")
    assert resp.status_code == 200
    items = resp.get_json()
    titles = [i["title"] for i in items]
    assert titles == ["Boas-vindas", "Material complementar"]
    assert items[0]["type"] == "VIDEO"
    assert items[1]["type"] == "DOC"
    assert [i["order_index"] for i in items] == [1, 2]


def test_get_sections_with_items_returns_nested_items(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/sections-with-items")
    assert resp.status_code == 200
    sections = resp.get_json()
    assert len(sections) == 2
    first_section = sections[0]
    assert first_section["title"] == "Introdução"
    assert [i["id"] for i in first_section["items"]] == [
        data["items"][0].id,
        data["items"][1].id,
    ]


def test_get_included_items_returns_texts_in_order(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/included-items")
    assert resp.status_code == 200
    values = [row["text_val"] for row in resp.get_json()]
    assert values == ["Acesso vitalício", "Comunidade exclusiva"]


def test_get_requirements_returns_texts(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/requirements")
    assert resp.status_code == 200
    values = [row["text_val"] for row in resp.get_json()]
    assert values == ["Computador com internet", "Vontade de aprender"]


def test_get_audience_returns_texts(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/audience")
    assert resp.status_code == 200
    values = [row["text_val"] for row in resp.get_json()]
    assert values == ["Iniciantes na área", "Profissionais em transição"]


def test_get_learn_returns_empty_list(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/trails/{trail.id}/learn")
    assert resp.status_code == 200
    assert resp.get_json() == []


# ---------- tests: item progress ----------


def test_set_item_progress_requires_authentication(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    item = data["items"][0]

    resp = client.put(
        f"/trails/{trail.id}/items/{item.id}/progress",
        json={"status": "IN_PROGRESS", "progress_value": 10},
    )
    assert resp.status_code == 401


def test_set_item_progress_creates_progress_record(client, db_session):
    status_in_progress = ensure_progress_status(db_session, "IN_PROGRESS")
    ensure_progress_status(db_session, "COMPLETED")
    user = register_user_via_api(client)
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    item = data["items"][0]

    resp = client.put(
        f"/trails/{trail.id}/items/{item.id}/progress",
        json={"status": "IN_PROGRESS", "progress_value": 55},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    progress = (
        db_session.query(UserItemProgress)
        .filter_by(user_id=user["user_id"], trail_item_id=item.id)
        .one()
    )
    assert progress.status_id == status_in_progress.id
    assert progress.progress_value == 55

    enrollment = (
        db_session.query(UserTrails)
        .filter_by(user_id=user["user_id"], trail_id=trail.id)
        .one()
    )
    assert enrollment.started_at is not None


def test_set_item_progress_returns_404_for_missing_item(client, db_session):
    ensure_progress_status(db_session, "IN_PROGRESS")
    ensure_progress_status(db_session, "COMPLETED")
    register_user_via_api(client)
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.put(
        f"/trails/{trail.id}/items/9999/progress",
        json={"status": "IN_PROGRESS", "progress_value": 10},
    )
    assert resp.status_code == 404


def test_set_item_progress_validates_payload(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    item = data["items"][0]

    resp = client.put(
        f"/trails/{trail.id}/items/{item.id}/progress",
        json={"status": "INVALID"},
    )
    assert resp.status_code == 422


# ---------- tests: trail item detail ----------


def test_get_item_detail_returns_youtube_and_neighbors(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    video_item = data["items"][0]
    doc_item = data["items"][1]

    resp = client.get(f"/trails/{trail.id}/items/{video_item.id}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["id"] == video_item.id
    assert payload["trail_id"] == trail.id
    assert payload["youtubeId"] == "video12345"
    assert payload["type"] == "VIDEO"
    assert payload["prev_item_id"] is None
    assert payload["next_item_id"] == doc_item.id


def test_get_item_detail_returns_empty_youtube_for_non_video(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    video_item = data["items"][0]
    doc_item = data["items"][1]

    resp = client.get(f"/trails/{trail.id}/items/{doc_item.id}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["youtubeId"] == ""
    assert payload["type"] == "DOC"
    assert payload["prev_item_id"] == video_item.id
    assert payload["next_item_id"] is None


def test_get_item_detail_404_when_item_not_in_trail(client, db_session):
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    other_trail = create_trail(db_session, name="Outra trilha")
    item = data["items"][0]

    resp = client.get(f"/trails/{other_trail.id}/items/{item.id}")
    assert resp.status_code == 404


# ---------- tests: user trails progress ----------


def test_user_trails_progress_returns_defaults_when_no_data(client, db_session):
    create_user_with_token(db_session)
    data = create_trail_with_content(db_session)
    trail = data["trail"]

    resp = client.get(f"/user-trails/{trail.id}/progress")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["done"] == 0
    assert payload["total"] == len(data["items"])
    assert payload["computed_progress_percent"] == 0.0
    assert payload["nextAction"] == "Começar"
    assert payload["enrolledAt"] is None


def test_user_trails_progress_counts_completed_items(client, db_session):
    user, _ = create_user_with_token(db_session)
    data = create_trail_with_content(db_session)
    trail = data["trail"]
    status_completed = ensure_progress_status(db_session, "COMPLETED")
    status_in_progress = ensure_progress_status(db_session, "IN_PROGRESS")

    started_at = datetime(2023, 1, 15, 8, 0, tzinfo=timezone.utc)
    db_session.add(
        UserTrails(user_id=user.user_id, trail_id=trail.id, started_at=started_at)
    )
    db_session.add(
        UserItemProgress(
            user_id=user.user_id,
            trail_item_id=data["items"][0].id,
            status_id=status_completed.id,
        )
    )
    db_session.add(
        UserItemProgress(
            user_id=user.user_id,
            trail_item_id=data["items"][1].id,
            status_id=status_in_progress.id,
        )
    )
    db_session.commit()

    resp = client.get(f"/user-trails/{trail.id}/progress")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["done"] == 1
    assert payload["total"] == len(data["items"])
    expected_percent = round(100.0 * 1 / len(data["items"]), 2)
    assert payload["computed_progress_percent"] == pytest.approx(expected_percent)
    assert payload["nextAction"] == "Continue a Estudar"
    assert payload["enrolledAt"].startswith("2023-01-15T08:00:00")
