# Imagen base ligera de python 12
FROM python:3.12-slim

# Traemos el binario de 'uv' desde su imagen ofical
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Evitamos que python genere archivos .pyc y forzar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Establecemos directorio de trabajo
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev\
    && rm -rf /var/lib/apt/lists/*

# Copiamos los archivos de las librerias
COPY pyproject.toml uv.lock ./

# Instalamos las dependencias
# Con frozen
# Sin herramientas de desarrollo
# Solo librerias no codigo aun
RUN uv sync --frozen --no-dev --no-install-project

# Copiamos el codigo
COPY src ./src

RUN touch README.md

# Syncronizacion
RUN uv sync --frozen --no-dev

# Agregamos el entorno virtual de uv al PATH
ENV PATH="/app/.venv/bin:$PATH"

# Creacion de usuario seguro
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Ejecutamos
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]