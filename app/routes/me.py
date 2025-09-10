from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.db import get_db
from models import User
from core.settings import settings
import jwt

router = APIRouter(tags=["me"])

def get_current_user_id(request: Request) -> str:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"require": ["exp"]})
        return decoded["id"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Sessão inválida")

@router.get("/me", response_model=dict)
def me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"user": {"id": user.id, "email": user.email, "name": user.name}}
