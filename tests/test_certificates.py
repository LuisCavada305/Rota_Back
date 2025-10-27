from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import event, text

from app.models.trails import Trails
from app.models.trail_sections import TrailSections
from app.models.trail_items import TrailItems
from app.models.user_trails import UserTrails
from app.models.user_item_progress import UserItemProgress
from app.models.trail_certificates import TrailCertificates
from app.models.lk_enrollment_status import LkEnrollmentStatus
from app.models.lk_progress_status import LkProgressStatus
from app.models.lk_item_type import LkItemType


@event.listens_for(TrailCertificates, "before_insert")
def _assign_certificate_id(mapper, connection, target):
    if connection.dialect.name != "sqlite" or target.id is not None:
        return
    next_id = connection.execute(
        text("SELECT COALESCE(MAX(id), 0) + 1 FROM trail_certificates")
    ).scalar_one()
    target.id = next_id


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _ensure_lookups(session):
    session.add_all(
        [
            LkEnrollmentStatus(code="ENROLLED"),
            LkEnrollmentStatus(code="IN_PROGRESS"),
            LkEnrollmentStatus(code="COMPLETED"),
        ]
    )
    session.add_all(
        [
            LkProgressStatus(code="IN_PROGRESS"),
            LkProgressStatus(code="COMPLETED"),
        ]
    )
    session.add(LkItemType(code="DOC"))
    session.commit()


def test_certificate_endpoint_commits_generated_certificate(client, db_session):
    _ensure_lookups(db_session)

    email = _unique_email("cert")
    register_payload = {
        "email": email,
        "password": "StrongPass!123",
        "name_for_certificate": "Cert User",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "1990-01-01",
        "username": f"user_{uuid.uuid4().hex[:6]}",
        "social_name": "Cert User",
        "role": "User",
    }

    register_resp = client.post("/auth/register", json=register_payload)
    assert register_resp.status_code == 200, register_resp.get_data(as_text=True)
    user_id = register_resp.get_json()["user"]["user_id"]

    item_type = db_session.query(LkItemType).filter_by(code="DOC").one()
    enrollment_ids = {
        row.code: row.id for row in db_session.query(LkEnrollmentStatus).all()
    }
    progress_ids = {
        row.code: row.id for row in db_session.query(LkProgressStatus).all()
    }

    trail = Trails(name="Trail", thumbnail_url="https://example.com/thumb.jpg")
    db_session.add(trail)
    db_session.flush()

    section = TrailSections(trail_id=trail.id, title="Section", order_index=0)
    db_session.add(section)
    db_session.flush()

    item = TrailItems(
        trail_id=trail.id,
        section_id=section.id,
        title="Item",
        url="https://example.com/item",
        order_index=0,
        duration_seconds=0,
        legacy_type="DOC",
        item_type_id=item_type.id,
        requires_completion=True,
    )
    db_session.add(item)
    db_session.flush()

    user_trail = UserTrails(
        id=1,
        user_id=user_id,
        trail_id=trail.id,
        status_id=enrollment_ids["ENROLLED"],
        progress_percent=0,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(user_trail)

    progress = UserItemProgress(
        id=1,
        user_id=user_id,
        trail_item_id=item.id,
        status_id=progress_ids["COMPLETED"],
        progress_value=100,
        last_interaction=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(progress)
    db_session.commit()

    assert (
        db_session.query(TrailCertificates)
        .filter_by(user_id=user_id, trail_id=trail.id)
        .first()
        is None
    )

    resp = client.get(f"/certificates/me/trails/{trail.id}")
    assert resp.status_code == 200, resp.get_data(as_text=True)

    db_session.rollback()

    cert = (
        db_session.query(TrailCertificates)
        .filter_by(user_id=user_id, trail_id=trail.id)
        .first()
    )
    assert cert is not None

