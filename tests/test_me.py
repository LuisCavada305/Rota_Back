import uuid


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def register_and_login(
    client, db_session
):  # noqa: ARG001 - fixture triggers DB seeding
    _ = db_session
    email = unique_email("me")
    payload = {
        "email": email,
        "password": "TestPass!123",
        "name_for_certificate": "Me Route",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "1990-01-01",
        "username": f"user_{uuid.uuid4().hex[:6]}",
        "social_name": "Me Route",
        "role": "User",
    }
    register_resp = client.post("/auth/register", json=payload)
    assert register_resp.status_code == 200, register_resp.get_data(as_text=True)
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": payload["password"], "remember": False},
    )
    assert login_resp.status_code == 200, login_resp.get_data(as_text=True)
    return login_resp


def test_me_requires_authentication(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_returns_profile_and_csrf_header(client, db_session):
    login_resp = register_and_login(client, db_session)
    csrf_header = login_resp.headers.get("X-CSRF-Token")
    assert csrf_header, "login should return CSRF header"

    me_resp = client.get("/me")
    assert me_resp.status_code == 200, me_resp.get_data(as_text=True)
    payload = me_resp.get_json()
    assert payload["user"]["email"].endswith("@example.com")
    assert payload["user"]["username"]
    assert "color" in payload["user"]

    returned_csrf = me_resp.headers.get("X-CSRF-Token")
    assert returned_csrf == csrf_header
