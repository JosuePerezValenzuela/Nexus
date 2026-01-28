import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings

logger = logging.getLogger(__name__)


# Definicion de la estructura exacta que queremos que la IA nos devuelva
class SearchQueryResponse(BaseModel):
    queries: list[str] = Field(
        description="Lista de 3 varaintes de busqueda tecnica y precisa."
    )


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
            temperature=0.3,
            streaming=True,
            max_tokens=2048,  # type: ignore
        )

        # Embeddings
        embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={
                "normalize_embeddings": True
            },  # Ayuda a la similitud de coseno
        )

    async def get_embedding(self, text: str) -> list[float]:
        """
        Genera vectores para RAG
        """
        # Limpiamos saltos de linea que a veces ensucian al vector
        clean_text = text.replace("\n", " ")
        return await self.embeddings.aembed_query(clean_text)

    async def generate_search_queries(self, original_query: str) -> list[str]:
        """
        Genera variantes de la pregunta usando terminologia medica tecnica
        para mejorar la recuperacion en documentos oficiales
        """
        # Configuracion del parser
        parser = PydanticOutputParser(pydantic_object=SearchQueryResponse)

        prompt = PromptTemplate(
            template="""
            Eres un experto en terminología médica.
            Genera 3 variantes de búsqueda técnica para: "{query}".
            
            {format_instructions}
            """,
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        try:
            # La IA devuelve directamente el objeto Pydantic validado
            chain = prompt | self.llm | parser  # type: ignore

            response = await chain.ainvoke({"query": original_query})  # type: ignore

            generated_queries = response.queries
            # Agregamos la original por si acaso
            generated_queries.append(original_query)

            logger.debug(f"Queries generadas: {generated_queries}")

            # Eliminamos duplicados manteniendo el orden
            return list(dict.fromkeys(generated_queries))
        except Exception as e:
            # Fallback seguro: Si falla la IA, usamos solo la original
            logger.warning(
                f"Fallo al generar variantes de busqueda. Usando query original. Error {e}"  # noqa: E501
            )  # noqa: E501
            return [original_query]


llm_service = LLMService()
