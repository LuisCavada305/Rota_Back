from sqlalchemy.orm import Session
from app.models.trails import Trails as TrailsORM


class TrailsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_showcase(self, limit: int = 6) -> list[TrailsORM]:
        return self.db.query(TrailsORM).limit(limit).all()
    
    def list_all(self) -> list[TrailsORM]:
        return self.db.query(TrailsORM).all()
