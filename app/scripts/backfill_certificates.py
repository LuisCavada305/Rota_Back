"""Backfill certificates for trails já concluídas.

Executar após deploy da feature de certificados para gerar hashes para estudantes
que terminaram cursos no passado.
"""

from sqlalchemy import select

# Importa modelos que têm relationships declaradas por string (TrailItems -> LkItemType).
# Sem esses imports, o SQLAlchemy não encontra as classes durante o mapeamento.
import app.models  # noqa: F401  # load all models for relationship resolution

from app.core.db import session_scope
from app.models.user_trails import UserTrails
from app.models.lk_enrollment_status import LkEnrollmentStatus
from app.repositories.UserTrailsRepository import UserTrailsRepository


def main() -> None:
    with session_scope() as session:
        repo = UserTrailsRepository(session)

        completed_status_id = session.execute(
            select(LkEnrollmentStatus.id).where(LkEnrollmentStatus.code == "COMPLETED")
        ).scalar_one_or_none()
        if completed_status_id is None:
            print("Nenhum status COMPLETED encontrado; nada para fazer.")
            return

        completeds = (
            session.query(UserTrails)
            .filter(UserTrails.status_id == completed_status_id)
            .all()
        )

        if not completeds:
            print("Nenhuma trilha concluída pendente de certificado.")
            return

        processed = 0
        for ut in completeds:
            repo.sync_user_trail_progress(ut.user_id, ut.trail_id)
            processed += 1

        session.commit()
        print(
            f"Certificados verificados/gerados para {processed} matrículas concluídas."
        )


if __name__ == "__main__":
    main()
