import httpx
from fastapi import HTTPException

from app.core.config import settings


class LLMService:
    EMBEDDING_ENDPOINT = "/api/embeddings"

    def __init__(self):
        # Lectura de variables que definimos en config.py y .env
        self.ollama_host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    def get_embedding(self, text: str) -> list[float]:
        """
        Envia texto a ollama y recibe su representacion vectorial
        """
        try:
            # Timeout = 60
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.ollama_host}{self.EMBEDDING_ENDPOINT}",
                    json={"model": self.model, "prompt": text},
                )

                # Si ollama no devuelve error
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Ollama Error ({response.status_code}):{response.text}",
                    )

                # Extraemos el resultado
                data = response.json()

                # Validamos
                if "embedding" not in data:
                    raise HTTPException(
                        status_code=500,
                        detail="La respuesta de Ollama no contine vectores.",
                    )

                return data["embedding"]

        except httpx.RequestError as e:
            # Si no se puede llegar a la ruta
            raise HTTPException(
                status_code=503,
                detail=f"No se conecto con el modelo {self.ollama_host},Error:{str(e)}",
            ) from e


# Instancia unica (Singleton) para usar en toda la app
llm_service = LLMService()
