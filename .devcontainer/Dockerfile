# Usamos Python 3.12 (versión estable moderna)
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

RUN rm -f /etc/apt/sources.list.d/yarn.list

# Instalamos uv (El gestor de paquetes ultrarrápido escrito en Rust)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configuración de entorno para uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Opcional: Instalar utilidades extra de sistema si las necesitamos luego
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /workspaces/Nexus/.venv && chown vscode:vscode /workspaces/Nexus/.venv