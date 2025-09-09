from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from core.db import get_db
from models import User
from models.users import RegisterIn, LoginIn, UserOut
from services.security import hash_password, verify_password, sign_session, set_session_cookie, clear_session_cookie
import uuid
from sqlalchemy import func
from models.roles import RolesEnum

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=dict)
def register(payload: RegisterIn, res: Response, db: Session = Depends(get_db)):
    # email único
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    user = User(
        user_id=str(uuid.uuid4()),
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        name_for_certificate=payload.name_for_certificate,
        created_at=func.now(),
        sex=payload.sex,
        birthday=payload.birthday
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # login automático após registro (opcional)
    token = sign_session({"id": user.id, "email": user.email, "role": RolesEnum.User.value})
    set_session_cookie(res, token, remember=True)

    return {"user": UserOut(id=user.id, email=user.email, name=user.name)}

@router.post("/login", response_model=dict)
def login(payload: LoginIn, res: Response, db: Session = Depends(get_db)):
    user: User | None = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = sign_session({"id": user.id, "email": user.email})
    set_session_cookie(res, token, remember=payload.remember)

    return {"user": UserOut(id=user.id, email=user.email, name=user.name)}

@router.post("/logout", response_model=dict)
def logout(res: Response):
    clear_session_cookie(res)
    return {"ok": True}
