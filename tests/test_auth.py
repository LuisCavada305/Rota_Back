# tests/test_auth.py
import uuid
from http.cookies import SimpleCookie
from sqlalchemy import text, select
from app.models.users import User
from app.services.security import generate_password_reset_token
import pytest
from app.models.roles import RolesEnum

# ---------- helpers ----------


def wipe_user(db_session, email: str):
    """Remove um usuário específico antes do teste (evita 409)."""
    db_session.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
    db_session.commit()


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def get_cookie_from_response(resp, name="rota_session"):
    sc = resp.headers.get("set-cookie")
    if not sc:
        return None
    cookies = SimpleCookie()
    cookies.load(sc)
    return cookies.get(name)


# ---------- tests: register ----------


def test_register_success(client, db_session):
    email = "testuser@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "testpass",
        "name_for_certificate": "Test User",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "2000-01-01",
        "username": "testuser",
        "social_name": "Test User",
        "role": "User",
    }

    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()["user"]
    assert data["email"] == email
    assert isinstance(data["user_id"], int)
    # não deve vazar hash na resposta
    assert "password_hash" not in r.get_data(as_text=True)
    assert data["role"] == payload["role"]
    assert data["color"] == "NS"


def test_register_conflict_on_duplicate_email(client, db_session):
    email = "dup@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "x",
        "name_for_certificate": "A",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "2000-01-01",
        "username": "dupuser",
        "social_name": "Dup User",
        "role": "User",
    }

    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 200, r1.get_data(as_text=True)

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409, r2.get_data(as_text=True)


def test_register_accepts_short_sex_letter(client, db_session):
    email = "enum_short@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "pass123",
        "name_for_certificate": "Enum Short",
        "sex": "N",  # <- letra curta
        "color": "NS",
        "birthday": "2000-01-01",
        "username": "enumshort",
        "social_name": "Enum Short",
        "role": "User",
    }

    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()["user"]
    assert data["email"] == email
    # No response data assertion needed here, only status code checked


# ---------- tests: login ----------


def test_login_success_and_cookie_flags(client, db_session):
    email = "login_ok@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "p@ss",
        "name_for_certificate": "U",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "2000-01-01",
        "username": "loginuser",
        "social_name": "Login User",
        "role": "User",
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.get_data(as_text=True)
    data = reg.get_json()["user"]
    assert data["username"] == payload["username"]
    assert data["role"] == payload["role"]

    # login remember=False
    r1 = client.post(
        "/auth/login", json={"email": email, "password": "p@ss", "remember": False}
    )
    assert r1.status_code == 200, r1.get_data(as_text=True)
    ck1 = get_cookie_from_response(r1, "rota_session")
    assert ck1 is not None
    # Em geral, quando remember=False, pode não haver Max-Age/Expires; mas deve ser HttpOnly:
    assert "httponly" in ck1.output().lower()
    login_data1 = r1.get_json()["user"]
    assert login_data1["role"] == payload["role"]

    # login remember=True
    r2 = client.post(
        "/auth/login", json={"email": email, "password": "p@ss", "remember": True}
    )
    assert r2.status_code == 200, r2.get_data(as_text=True)
    ck2 = get_cookie_from_response(r2, "rota_session")
    assert ck2 is not None
    # Quando remember=True, normalmente define Max-Age/Expires:
    assert ("max-age" in ck2.output().lower()) or ("expires=" in ck2.output().lower())
    login_data2 = r2.get_json()["user"]
    assert login_data2["role"] == payload["role"]


def test_login_fails_with_wrong_password(client, db_session):
    email = "wrongpass@example.com"
    wipe_user(db_session, email)

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "right",
            "name_for_certificate": "U",
            "sex": "NotSpecified",
            "color": "NS",
            "birthday": "2000-01-01",
            "username": "wrongpassuser",
            "social_name": "Wrong Pass User",
            "role": "User",
        },
    )

    r = client.post(
        "/auth/login", json={"email": email, "password": "WRONG", "remember": False}
    )
    assert r.status_code == 401, r.get_data(as_text=True)


def test_login_fails_with_unknown_email(client):
    r = client.post(
        "/auth/login",
        json={"email": unique_email("nope"), "password": "x", "remember": False},
    )
    assert r.status_code == 401, r.get_data(as_text=True)


# ---------- tests: logout ----------


def test_logout_clears_cookie(client):
    r = client.post("/auth/logout")
    assert r.status_code == 200, r.get_data(as_text=True)
    ck = get_cookie_from_response(r, "rota_session")
    # clear_session_cookie deve mandar um cookie com expiração/Max-Age=0
    assert ck is not None
    out = ck.output().lower()
    assert ("max-age=0" in out) or ("expires=" in out)


# ---------- tests: segurança básica ----------


def test_password_is_hashed_in_db(client, db_session):
    email = "hash@example.com"
    wipe_user(db_session, email)

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "plain123",
            "name_for_certificate": "U",
            "sex": "NotSpecified",
            "color": "NS",
            "birthday": "2000-01-01",
            "username": "hashuser",
            "social_name": "Hash User",
            "role": "User",
        },
    )

    user = db_session.execute(select(User).where(User.email == email)).scalar_one()
    assert user.password_hash != "plain123"
    assert isinstance(user.password_hash, str) and len(user.password_hash) > 20


# ---------- extra robustness tests ----------
def test_register_fails_with_missing_fields(client):
    payload = {
        "email": unique_email("missing"),
        "password": "x",
        # missing name, name_for_certificate, sex, birthday, username, role
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422


def test_register_fails_with_invalid_role(client):
    payload = {
        "email": unique_email("badrole"),
        "password": "x",
        "name_for_certificate": "Bad Role",
        "sex": "MC",
        "color": "BR",
        "birthday": "1990-01-01",
        "username": "badroleuser",
        "role": "NotARole",
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422


def test_register_fails_with_invalid_sex(client):
    payload = {
        "email": unique_email("badsex"),
        "password": "x",
        "name_for_certificate": "Bad Sex",
        "sex": "X",
        "color": "NS",
        "birthday": "1990-01-01",
        "username": "badsexuser",
        "role": "User",
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422


def test_register_fails_with_invalid_color(client):
    payload = {
        "email": unique_email("badcolor"),
        "password": "x",
        "name_for_certificate": "Bad Color",
        "sex": "MC",
        "color": "??",
        "birthday": "1990-01-01",
        "username": "badcoloruser",
        "role": "User",
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422


def test_register_conflict_on_duplicate_username(client, db_session):
    email1 = unique_email("dupuser1")
    email2 = unique_email("dupuser2")
    wipe_user(db_session, email1)
    wipe_user(db_session, email2)
    payload1 = {
        "email": email1,
        "password": "x",
        "name_for_certificate": "A",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "2000-01-01",
        "username": "uniqueuser",
        "social_name": "Dup User",
        "role": "User",
    }
    payload2 = dict(payload1)
    payload2["email"] = email2
    r1 = client.post("/auth/register", json=payload1)
    assert r1.status_code == 200, r1.get_data(as_text=True)
    r2 = client.post("/auth/register", json=payload2)
    assert r2.status_code == 409, r2.get_data(as_text=True)


def test_forgot_password_is_idempotent(client):
    email = unique_email("missing")
    r = client.post("/auth/password/forgot", json={"email": email})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_password_reset_flow_updates_credentials(client, db_session):
    email = unique_email("reset")
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "antigaSenha!",
        "name_for_certificate": "Reset User",
        "sex": "NotSpecified",
        "color": "NS",
        "birthday": "2000-01-01",
        "username": f"user_{uuid.uuid4().hex[:6]}",
        "social_name": "Reset User",
        "role": RolesEnum.User.value,
    }

    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 200

    user = db_session.execute(select(User).where(User.email == email)).scalar_one()
    token = generate_password_reset_token(user)

    reset_resp = client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": "NovaSenha@123"},
    )
    assert reset_resp.status_code == 200, reset_resp.get_data(as_text=True)

    old_login = client.post(
        "/auth/login",
        json={"email": email, "password": "antigaSenha!", "remember": False},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": email, "password": "NovaSenha@123", "remember": False},
    )
    assert new_login.status_code == 200, new_login.get_data(as_text=True)
