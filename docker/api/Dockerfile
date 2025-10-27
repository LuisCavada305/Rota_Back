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
    && python -m pip install gunicorn \
    && python -m pip install -r requirements.txt

COPY . ${APP_HOME}

# Cria usuário não privilegiado para rodar a API
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

ENV GUNICORN_CMD_ARGS="--workers 3 --worker-class gthread --threads 4 --worker-tmp-dir /dev/shm --bind 0.0.0.0:8000 --keep-alive 90 --timeout 90"

EXPOSE 8000

CMD ["gunicorn", "app.main:app"]
