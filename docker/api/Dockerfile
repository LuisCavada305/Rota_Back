FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/opt/app

# Instala dependências do sistema antes do build das libs Python
RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . ${APP_HOME}

# Cria usuário não privilegiado para rodar a API
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

ENV UVICORN_WORKERS=4 \
    UVICORN_KEEP_ALIVE=5 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.asgi:app --host ${UVICORN_HOST:-0.0.0.0} --port ${UVICORN_PORT:-8000} --workers ${UVICORN_WORKERS:-4} --timeout-keep-alive ${UVICORN_KEEP_ALIVE:-60} --proxy-headers --forwarded-allow-ips '*'"]
