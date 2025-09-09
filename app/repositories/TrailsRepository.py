from sqlalchemy.orm import Session
from app.models.trails import Trails as TrailsORM

class TrailsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_showcase(self, limit: int = 12) -> list[TrailsORM]:
        # Exemplo simples: tudo ou com limit
        return self.db.query(TrailsORM).limit(limit).all()
