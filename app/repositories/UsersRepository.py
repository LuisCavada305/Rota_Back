from sqlalchemy.orm import Session
from typing import Optional
from app.models.users import User

class UsersRepository:
    def __init__(self, db: Session):
        self.db = db

    def GetUserByEmail(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def GetUserByUsername(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()