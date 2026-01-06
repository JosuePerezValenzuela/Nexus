from typing import Literal

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Configuracion general}
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str
    VERSION: str

    # Configuracion de Base de datos
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Variables de IA
    HF_TOKEN: str
    LLM_HOST: str
    VLLM_API_KEY: str

    # computed_field calcula la URL automaticamente basandonos en los campos anteriores
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",  # Driver moderno para PostgreSQL
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # Seguridad (CORS)
    # Pydantic convierte automaticamente una string
    # '["a", "b"]' a una lista de python
    BACKEND_CORS_ORIGINS: list[str] = []

    # Entorno
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Configuracion de Pydantic para leer el .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",  # Si se tienen varaibles extras no dar error
    )


# Instaciamos la configuracion una sola vez para importarla donde sea
settings = Settings()  # type: ignore
