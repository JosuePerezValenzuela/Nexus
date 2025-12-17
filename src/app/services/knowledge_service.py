from sqlmodel import Session

from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate


class KnowledgeService:
    # Recibe una sesion de BD y datos
    def create_new_document(
        self, session: Session, item_in: KnowledgeCreate
    ) -> KnowledgeBase:
        # 1. Aqui iria logica extra si existiera

        # 2. Convertir Schema -> Modelo
        knowledge_item = KnowledgeBase.model_validate(item_in)

        # 3. Guardamos
        session.add(knowledge_item)
        session.commit()
        session.refresh(knowledge_item)

        # 4. Aqui es donde en el futuro llamaremos a la IA para embeddings

        return knowledge_item


knowledge_service = KnowledgeService()
