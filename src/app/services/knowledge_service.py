import os
import shutil
from typing import Any, cast

from fastapi import UploadFile
from flashrank import Ranker, RerankRequest  # type: ignore
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session, select

from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import PDFResponse
from app.services.llm_service import llm_service


class KnowledgeService:
    # Recibe una sesion de BD y datos
    async def create_new_document(
        self, session: Session, document_data: KnowledgeBase
    ) -> KnowledgeBase:
        """
        Crea un documento, genera su vector con IA y lo guarda en Postgres.
        """
        # 1. Aqui iria logica extra si existiera

        # Unimos titulo y contenido para que el vector tenga mas contexto
        full_text = f"{document_data.title}. {document_data.content}"

        # Generamos el vector, llamando a ollama y devolviendo la lista de floats
        vector = await llm_service.get_embedding(full_text)

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

    async def proccess_pdf(self, session: Session, file: UploadFile) -> PDFResponse:
        """
        Recibe un PDF, lo guarda temporalmente, lo trocea y vectoriza cada parte
        """
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)

        safe_filename = file.filename or "temp_document.pdf"

        temp_file_path = os.path.join(temp_dir, safe_filename)

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # Carga del pdf
            loader = PyMuPDFLoader(temp_file_path)
            docs = loader.load()  # Extrae el texto pagina por pagina

            # Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200, chunk_overlap=300
            )
            splits = text_splitter.split_documents(docs)

            print(f"📄 Procesando PDF: {len(splits)} fragmentos generados.")

            # Procesamiento de cada fragmento
            for split in splits:
                vector = await llm_service.get_embedding(split.page_content)

                meta = cast(dict[str, Any], split.metadata)  # type: ignore

                page_num = meta.get("page", 0)
                # Creacion del objeto a guardar en la BD
                new_chunk = KnowledgeBase(
                    title=f"{file.filename} - Pag {page_num}",
                    content=split.page_content,
                    source=safe_filename,
                    embedding=vector,
                )

                session.add(new_chunk)

            session.commit()
            return PDFResponse(
                filename=safe_filename,
                message="PDF procesado exitosamente.",
                chunks_created=len(splits),
            )

        finally:
            # Limpieza del archivo temporal
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    async def search_similarity(
        self, session: Session, query: str, k: int = 5
    ) -> list[KnowledgeBase]:
        """
        Busqueda en 2 pasos:
        1. Recuperacion amplia (Vectores) -> Trae candidatos.
        2. Reranking (FlashRank) -> Ordena por relevancia real
        """
        # Generacion de multiqueries
        print(f"🤔 Generando sinónimos para: '{query}'...")
        search_queries = await llm_service.generate_search_queries(query)
        print(f"🔍 Buscando por: {search_queries}")

        # Recuperacion masiva
        all_candidates: list[KnowledgeBase] = []
        seen_ids: set[Any] = set()

        for q in search_queries:
            q_vector = await llm_service.get_embedding(q)

            statement = (
                select(KnowledgeBase)
                .order_by(KnowledgeBase.embedding.cosine_distance(q_vector))  # type: ignore
                .limit(k * 2)
            )

            results = session.exec(statement).all()

            for doc in results:
                if doc.id not in seen_ids:
                    all_candidates.append(doc)
                    seen_ids.add(doc.id)

        if not all_candidates:
            return []

        passages: list[dict[str, Any]] = []
        candidate_map: dict[str, KnowledgeBase] = {}

        for doc in all_candidates:
            doc_id = str(doc.id)
            candidate_map[doc_id] = doc
            passages.append(
                {"id": doc_id, "text": doc.content, "meta": {"title": doc.title}}
            )

        print(f"⚡️ Reranking {len(passages)} documentos candidatos...")

        # 4. RERANKING
        # Usamos TinyBERT que ya probamos que funciona
        ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="opt")

        # OJO: Aquí el Reranker compara los documentos encontrados contra
        # la pregunta ORIGINAL del usuario. Él decide cuál es la mejor respuesta.
        reranked_results = ranker.rerank(RerankRequest(query=query, passages=passages))

        # 5. RETORNAR LOS TOP K
        final_docs: list[KnowledgeBase] = []
        for result in reranked_results[:k]:
            # Casting y recuperación segura
            doc_id = str(result["id"])
            original_doc = candidate_map.get(doc_id)
            if original_doc:
                final_docs.append(original_doc)

        return final_docs


knowledge_service = KnowledgeService()
