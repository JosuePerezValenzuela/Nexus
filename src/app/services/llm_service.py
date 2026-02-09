import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpointEmbeddings
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings

logger = logging.getLogger(__name__)


# Definicion de la estructura exacta que queremos que la IA nos devuelva
class SearchQueryResponse(BaseModel):
    queries: list[str] = Field(
        description="Lista de 3 variantes de busqueda tecnica y precisa."
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
        app_env = settings.ENVIRONMENT
        model_id = "intfloat/multilingual-e5-large"

        if app_env == "production":
            logger.info(" MODO PRODUCCION: Uso de HuggingFace API")
            self.embeddings = HuggingFaceEndpointEmbeddings(
                model=model_id,
                task="feature-extraction",
                huggingfacehub_api_token=settings.HF_TOKEN,
            )
        else:
            logger.info("Modo desarrollo: Cargando el modelo de embeddings")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_id,
                model_kwargs={"device": "cpu"},
                encode_kwargs={
                    "normalize_embeddings": True
                },  # Ayuda a la similitud de coseno
            )

    async def get_embedding(self, text: str) -> list[float]:
        """
        Genera embeddings para la query de busqueda.
        """
        # Limpiamos saltos de linea que a veces ensucian al vector
        clean_text = text.replace("\n", " ").strip()

        # Prefijo obligatorio para el modelo de embedings intfloat/multilingual/e5
        text_with_prefix = f"query: {clean_text}"

        return await self.embeddings.aembed_query(text_with_prefix)

    async def generate_search_queries(
        self, original_query: str, context_summary: str | None = None
    ) -> list[str]:
        """
        Genera variantes de la pregunta usando terminologia medica tecnica
        para mejorar la recuperacion en documentos oficiales, tambien usa el contexto
        del paciente si existe.
        """
        # Configuracion del parser
        parser = PydanticOutputParser(pydantic_object=SearchQueryResponse)

        # Prompt con inyeccion de contexto del paciente si existe
        prompt = PromptTemplate(
            template="""
            Eres un asistente experto en investigacion medica clinica.
            Tu objetivo es generar 3 consultas de busqueda (queries) optimizadas para
            una base de datos vectorial de guias medicas y protocolos.
            
            INFORMACION DE CONTEXTO (Datos del paciente encontrados previamente):
            {context}
            
            PREGUNTA DEL USUARIO:
            {query}
            
            INSTRUCCIONES:
            1. Si el contexto tiene datos de un paciente, Usalos para hacer la busqueda
            mas especifica.
                - Mal: "¿Que es la diabetes?"
                - Bien: "Protocolo diagnostico diabetes glucosa ayunas 145 mg/dL adulto"
            2. Usa terminologia medica tecnica (ej: "Hiperglucemia", "HbA1c", "Criterios ADA").
            3. Genera variantes que cubran diferentes aspectos (diagnostico, tratamiento, valores normales).
            
            {format_instructions}
            """,  # noqa: E501
            input_variables=["query", "context"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        try:
            # Si no hay contexto, pasamos un string vacio para no romper el prompt
            safe_context = (
                context_summary
                if context_summary
                else "No hay datos previos del paciente."
            )  # noqa: E501

            chain = prompt | self.llm | parser  # type: ignore

            response: SearchQueryResponse = await chain.ainvoke(  # type: ignore
                {  # type: ignore
                    "query": original_query,
                    "context": safe_context,
                }
            )

            generated_queries = response.queries
            # Agregamos la query original
            generated_queries.append(original_query)

            # Deduplicar
            return list(dict.fromkeys(generated_queries))

        except Exception as e:
            # Fallback seguro: Si falla la IA, usamos solo la original
            logger.warning(
                f"Fallo al generar variantes de busqueda. Usando query original. Error {e}"  # noqa: E501
            )  # noqa: E501
            return [original_query]


llm_service = LLMService()
