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
            model_kwargs={"max_tokens": 8192},
        )

        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

    async def get_embedding(self, text: str) -> list[float]:
        """
        Genera vectores para RAG
        """
        return await self.embeddings.aembed_query(text)


llm_service = LLMService()
