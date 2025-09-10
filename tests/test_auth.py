# tests/test_auth.py
import uuid
from http.cookies import SimpleCookie
from sqlalchemy import text, select
from app.models.users import User

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
        "name": "Test User",
        "name_for_certificate": "Test User",
        "sex": "NotSpecified",   # também testaremos "N" em outro caso
        "birthday": "2000-01-01",
    }

    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()["user"]
    assert data["email"] == email
    assert isinstance(data["id"], int)
    # não deve vazar hash na resposta
    assert "password_hash" not in r.text


def test_register_conflict_on_duplicate_email(client, db_session):
    email = "dup@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "x",
        "name": "A",
        "name_for_certificate": "A",
        "sex": "NotSpecified",
        "birthday": "2000-01-01",
    }

    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 200, r1.text

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409, r2.text


def test_register_accepts_short_sex_letter(client, db_session):
    email = "enum_short@example.com"
    wipe_user(db_session, email)

    payload = {
        "email": email,
        "password": "pass123",
        "name": "Enum Short",
        "name_for_certificate": "Enum Short",
        "sex": "N",  # <- letra curta
        "birthday": "2000-01-01",
    }

    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()["user"]
    assert data["email"] == email

# ---------- tests: login ----------

def test_login_success_and_cookie_flags(client, db_session):
    email = "login_ok@example.com"
    wipe_user(db_session, email)

    # registra
    reg = client.post("/auth/register", json={
        "email": email,
        "password": "p@ss",
        "name": "U",
        "name_for_certificate": "U",
        "sex": "NotSpecified",
        "birthday": "2000-01-01",
    })
    assert reg.status_code == 200, reg.text

    # login remember=False
    r1 = client.post("/auth/login", json={"email": email, "password": "p@ss", "remember": False})
    assert r1.status_code == 200, r1.text
    ck1 = get_cookie_from_response(r1, "rota_session")
    assert ck1 is not None
    # Em geral, quando remember=False, pode não haver Max-Age/Expires; mas deve ser HttpOnly:
    assert "httponly" in ck1.output().lower()

    # login remember=True
    r2 = client.post("/auth/login", json={"email": email, "password": "p@ss", "remember": True})
    assert r2.status_code == 200, r2.text
    ck2 = get_cookie_from_response(r2, "rota_session")
    assert ck2 is not None
    # Quando remember=True, normalmente define Max-Age/Expires:
    assert ("max-age" in ck2.output().lower()) or ("expires=" in ck2.output().lower())


def test_login_fails_with_wrong_password(client, db_session):
    email = "wrongpass@example.com"
    wipe_user(db_session, email)

    client.post("/auth/register", json={
        "email": email, "password": "right", "name": "U",
        "name_for_certificate": "U", "sex": "NotSpecified",
        "birthday": "2000-01-01",
    })

    r = client.post("/auth/login", json={"email": email, "password": "WRONG", "remember": False})
    assert r.status_code == 401, r.text


def test_login_fails_with_unknown_email(client):
    r = client.post("/auth/login", json={"email": unique_email("nope"), "password": "x", "remember": False})
    assert r.status_code == 401, r.text

# ---------- tests: logout ----------

def test_logout_clears_cookie(client):
    r = client.post("/auth/logout")
    assert r.status_code == 200, r.text
    ck = get_cookie_from_response(r, "rota_session")
    # clear_session_cookie deve mandar um cookie com expiração/Max-Age=0
    assert ck is not None
    out = ck.output().lower()
    assert ("max-age=0" in out) or ("expires=" in out)

# ---------- tests: segurança básica ----------

def test_password_is_hashed_in_db(client, db_session):
    email = "hash@example.com"
    wipe_user(db_session, email)

    client.post("/auth/register", json={
        "email": email, "password": "plain123", "name": "U",
        "name_for_certificate": "U", "sex": "NotSpecified",
        "birthday": "2000-01-01",
    })

    user = db_session.execute(select(User).where(User.email == email)).scalar_one()
    assert user.password_hash != "plain123"
    assert isinstance(user.password_hash, str) and len(user.password_hash) > 20
