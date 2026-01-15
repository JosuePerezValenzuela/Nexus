from typing import Any, cast

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import settings


class LLMService:
    """
    Servicio de infraestructura:
    Su unica responsabilidad es proveer instancias configuradas del LLM y Embeddings
    """

    def __init__(self):
        # Lectura de variables de entorno
        self.api_base = settings.LLM_HOST
        self.api_key = SecretStr(settings.VLLM_API_KEY)
        self.model_name = settings.LLM_MODEL_NAME

        # Orquestador
        self.llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.api_base,
            api_key=self.api_key,
            temperature=0.7,
            streaming=True,
            model_kwargs={"max_tokens": 2048},
        )

        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cpu"},
        )

    async def get_embedding(self, text: str) -> list[float]:
        """
        Genera vectores para RAG
        """
        return await self.embeddings.aembed_query(text)

    async def generate_search_queries(self, original_query: str) -> list[str]:
        """
        Genera variantes de la pregunta usando terminologia medica tecnica
        para mejorar la recuperacion en documentos oficiales
        """
        prompt = f"""
        Actúa como un experto en terminología médica y normas de salud de Bolivia.
        El usuario está buscando: "{original_query}"
        
        Tu tarea es generar 3 variantes de búsqueda para encontrar esta información 
        exacta en un manual técnico.
        
        Estrategia:
        1.  Usa sinónimos técnicos (ej: si busca "azúcar alta", busca "Hiperglucemia").
        2.  Desglosa siglas (ej: si busca "Prediabetes", busca 
        "Glicemia Alterada en Ayunas" y "Intolerancia a la Glucosa").
        3.  Si busca diagnóstico, incluye la palabra "Criterios".
        
        Salida:
        Devuelve SOLO las 3 frases de búsqueda, una por línea. Sin numeración, 
        sin guiones, sin introducciones.
        """

        messages = [
            {"role": "system", "content": "Eres un asistente de busqueda clinica."},
            {"role": "user", "content": prompt},
        ]

        response = await self.llm.ainvoke(messages)
        content_text = str(cast(Any, response.content))  # type: ignore

        queries = content_text.strip().split("\n")

        clean_queries: list[str] = []
        for q in queries:
            clean_q = (
                q.strip()
                .replace("- ", "")
                .replace("1. ", "")
                .replace("2. ", "")
                .replace("3. ", "")
            )
            if clean_q:
                clean_queries.append(clean_q)

        clean_queries.append(original_query)

        return list(set(clean_queries))


llm_service = LLMService()
