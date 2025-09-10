from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.users import User
from app.models.users import RegisterIn, LoginIn, UserOut
from app.services.security import hash_password, verify_password, sign_session, set_session_cookie, clear_session_cookie
import uuid
from sqlalchemy import func
from app.models.roles import RolesEnum
from app.repositories.UsersRepository import UsersRepository

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=dict)
def register(payload: RegisterIn, res: Response, db: Session = Depends(get_db)):
    repo = UsersRepository(db)
    # email único
    exists = repo.GetUserByEmail(payload.email)
    if exists:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    exists_username = db.query(User).filter(User.username == payload.username).first()
    if exists_username:
        raise HTTPException(status_code=409, detail="Username já cadastrado")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        name_for_certificate=payload.name_for_certificate,
        username=payload.username,
        social_name=payload.social_name,
        sex=payload.sex,
        birthday=payload.birthday,
        role=RolesEnum.User.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = sign_session({"id": user.user_id, "email": user.email, "role": user.role, "username": user.username})
    set_session_cookie(res, token, remember=True)

    return {"user": UserOut(id=user.user_id, email=user.email, name=user.name, username=user.username, social_name=user.social_name, role=user.role)} 

@router.post("/login", response_model=dict)
def login(payload: LoginIn, res: Response, db: Session = Depends(get_db)):
    repo = UsersRepository(db)
    user: User | None = repo.GetUserByEmail(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = sign_session({"id": user.user_id, "email": user.email, "role": user.role})
    set_session_cookie(res, token, remember=payload.remember)

    return {"user": UserOut(id=user.user_id, email=user.email, name=user.name, username=user.username, social_name=user.social_name, role=user.role)}

@router.post("/logout", response_model=dict)
def logout(res: Response):
    clear_session_cookie(res)
    return {"ok": True}
