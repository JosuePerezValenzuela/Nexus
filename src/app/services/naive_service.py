from typing import Any, cast

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.knowledge import KnowledgeBase
from app.services.llm_service import llm_service


class NaiveRAGService:
    async def answer_question(
        self, session: AsyncSession, query: str
    ) -> dict[str, Any]:
        """
        Flujo Naive RAG:
        1. Embed Query -> 2. Vector Search -> 3. Prompt Stuffing -> 4. LLM answer
        """

        # 1. Vectorizacion
        query_vector = await llm_service.get_embedding(f"query: {query}")

        # 2. Busqueda semantica
        statement = (
            select(KnowledgeBase)
            .order_by(
                KnowledgeBase.embedding.cosine_distance(query_vector)  # type: ignore
            )
            .limit(5)
        )

        results = await session.exec(statement)
        retrived_chunks = results.all()

        if not retrived_chunks:
            return {
                "answer": "No encontre informacion relevante en la base de conocimiento",  # noqa: E501
                "sources": [],
            }

        # 3. Construccion del Contexto
        context_text = "\n\n".join([chunk.content for chunk in retrived_chunks])
        sources = list(set([chunk.source for chunk in retrived_chunks]))

        system_prompt = (
            "Eres un asistente medico util y directo"
            " Usa SOLAMENTE el sigueinte contexto para responder a la pregunta"
            " Si la respuesta no esta en el contexto, di 'No lo se'."
            " No inventes informacion. \n\n"
            f"--- CONTEXTO ---\n {context_text}\n"
        )

        # 4. Llamada al LLM
        response = await llm_service.llm.ainvoke(
            [("system", system_prompt), ("user", query)]
        )

        answer_text = cast(str, response.content)  # type: ignore

        return {
            "answer": answer_text,
            "sources": sources,
        }


naiveRAGService = NaiveRAGService()
