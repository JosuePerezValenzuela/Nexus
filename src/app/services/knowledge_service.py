import asyncio
import logging
import os
import shutil
import tempfile
from typing import Any, cast

from fastapi import UploadFile
from flashrank import Ranker, RerankRequest  # type: ignore
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import PDFResponse
from app.services.llm_service import llm_service

# Configuracion del Logger
logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self):
        # OPTIMIZACION: Cargamos el modelo UNA sola vez al iniciar la app
        # Esto ahorra milisegundos valiosos en cada busqueda.
        logger.info(f"Cargando modelo Raranker: {settings.RAG_RERANKER_MODEL}...")
        self.ranker = Ranker(model_name=settings.RAG_RERANKER_MODEL, cache_dir="opt")
        logger.info("Modelo Reranker listo en memoria.")

    # Recibe una sesion de BD y datos
    async def create_new_document(
        self, session: AsyncSession, document_data: KnowledgeBase
    ) -> KnowledgeBase:
        """
        Crea un documento, genera su vector con IA y lo guarda en Postgres.
        """
        # 1. Aqui iria logica extra si existiera

        # Unimos titulo y contenido para que el vector tenga mas contexto
        full_text = f"{document_data.title}. {document_data.content}"

        # Agregamos prefijo
        text_to_embed = f"passage: {full_text}"

        # Generamos el vector y devolviendo la lista de floats
        vector = await llm_service.get_embedding(text_to_embed)

        # Asignar el vector al objeto
        document_data.embedding = vector

        # Guardamos en la BD
        session.add(document_data)
        await session.commit()
        await session.refresh(document_data)

        return document_data

    async def get_all_documents(self, session: AsyncSession) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase)
        results = await session.exec(statement)
        return list(results.all())

    async def proccess_pdf(
        self, session: AsyncSession, file: UploadFile
    ) -> PDFResponse:  # noqa: E501
        """
        Recibe un PDF, lo guarda temporalmente, lo trocea y vectoriza cada parte
        """
        suffix = os.path.splitext(file.filename or "")[1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_path = tmp_file.name

        try:
            # Carga del pdf
            logger.info(f"Procesando PDF: {file.filename}")

            # Carga y Chunking (CPU Bound - Rapido)
            loader = PyMuPDFLoader(temp_path)
            docs = loader.load()  # Extrae el texto pagina por pagina

            # Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.RAG_CHUNK_SIZE,
                chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            )
            splits = text_splitter.split_documents(docs)

            logger.info(f"Generados {len(splits)} chunks para {file.filename}")

            # Vectorizacion concurrente
            semaphore = asyncio.Semaphore(5)

            async def get_embedding_controlled(text: str):
                async with semaphore:
                    # Añadimos el prefijo
                    return await llm_service.get_embedding(f"passage: {text}")  # noqa: E501

            tasks = [get_embedding_controlled(split.page_content) for split in splits]

            # Ejecutamos todas la tareas en paralelo y esperamos los resultados
            vectors = await asyncio.gather(*tasks)

            # Insercion Masiva en BD
            new_chunks = []
            for i, split in enumerate(splits):
                meta = cast(dict[str, Any], split.metadata)  # type: ignore

                # Usamos el vector que ya calculamos en paralelo
                chunk = KnowledgeBase(
                    title=f"{file.filename} - Pag {meta.get('page', 0) + 1}",
                    content=split.page_content,
                    source=file.filename or "unknown",
                    embedding=vectors[i],
                )
                new_chunks.append(chunk)  # type: ignore

            session.add_all(new_chunks)  # type: ignore
            await session.commit()

            return PDFResponse(
                filename=file.filename or "unknown",
                message="PDF procesado exitosamente.",
                chunks_created=len(splits),
            )

        except Exception as e:
            logger.error(f"Error procesando PDF: {str(e)}")
            raise e
        finally:
            # Limpieza del archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def search_similarity(
        self,
        session: AsyncSession,
        query: str,
        k: int = 5,
        context_summary: str | None = None,
        score_threshold: float = 0.60,
    ) -> list[KnowledgeBase]:
        """
        Busqueda en 2 pasos:
        1. Recuperacion amplia (Vectores) -> Trae candidatos.
        2. Reranking (FlashRank) -> Ordena por relevancia real
        """
        # 1. Generacion de multiqueries
        logger.info(f"Query original: {query}")
        search_queries = await llm_service.generate_search_queries(
            query, context_summary
        )
        logger.info(f"Queries generadas: {search_queries}")

        # 2. Recuperacion masiva
        all_candidates: list[KnowledgeBase] = []
        seen_ids: set[Any] = set()

        for q in search_queries:
            q_vector = await llm_service.get_embedding(q)

            statement = (
                select(KnowledgeBase)
                .order_by(KnowledgeBase.embedding.cosine_distance(q_vector))  # type: ignore
                .limit(k * 2)
            )

            result = await session.exec(statement)

            results = result.all()

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

        logger.info(f"Reranking {len(passages)} candidatos...")

        # 3. Preparacion para QUERY ENRIQUECIDA para el RERANKER
        # El Reranker funciona mejor si le damos todo lo el contexto posible
        rerank_query = query
        if context_summary:
            rerank_query = f"{query}. Contexto relevante: {context_summary}"

        # 4. RERANKING
        # OJO: Aquí el Reranker compara los documentos encontrados contra
        # la pregunta ORIGINAL del usuario. Él decide cuál es la mejor respuesta.
        reranked_results = self.ranker.rerank(
            RerankRequest(query=rerank_query, passages=passages)
        )  # noqa: E501

        # 5. FILTRADO y RETORNO (THRESHOLDING)
        final_docs: list[KnowledgeBase] = []

        for result in reranked_results[:k]:
            # Casting y recuperación segura
            score = result.get("score", 0)
            doc_id = str(result["id"])

            logger.info(
                f"Doc: {doc_id} | Score: {score:.4f} | Threshold: {score_threshold}"
            )  # noqa: E501

            # Filtro de la basura
            if score < score_threshold:
                continue

            if doc := candidate_map.get(doc_id):
                final_docs.append(doc)

        return final_docs


knowledge_service = KnowledgeService()
