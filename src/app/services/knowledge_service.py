from sqlmodel import Session, select

from app.models.knowledge import KnowledgeBase
from app.services.llm_service import llm_service


class KnowledgeService:
    # Recibe una sesion de BD y datos
    def create_new_document(
        self, session: Session, document_data: KnowledgeBase
    ) -> KnowledgeBase:
        """
        Crea un documento, genera su vector con IA y lo guarda en Postgres.
        """
        # 1. Aqui iria logica extra si existiera

        # Unimos titulo y contenido para que el vector tenga mas contexto
        full_text = f"{document_data.title}. {document_data.content}"

        # Generamos el vector, llamando a ollama y devolviendo la lista de floats
        vector = llm_service.get_embedding(full_text)

        # Asignar el vector al objeto
        document_data.embedding = vector

        # Guardamos en la BD
        session.add(document_data)
        session.commit()
        session.refresh(document_data)

        return document_data

    def get_all_documents(self, session: Session) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase)
        results = session.exec(statement)
        return list(results.all())


knowledge_service = KnowledgeService()
