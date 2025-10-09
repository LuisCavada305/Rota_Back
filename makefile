SHELL := /bin/bash

# -------- Config ----------
HOST        ?= 127.0.0.1   # local dev; em prod compart., provedor decide
PORT        ?= 8001
# Se você tem "app/main.py" com "app = Flask(__name__)" use:
APP         ?= app.main:app
ASGI_APP    ?= app.asgi:app
UVICORN_WORKERS ?= 2
UVICORN_KEEP_ALIVE ?= 5
# Se você usa factory "def create_app()" use:
# APP      ?= "app.main:create_app()"

CERT_DIR    ?= $(PWD)/certs
CERT_DAYS   ?= 365
CERT_KEY    := $(CERT_DIR)/localhost-key.pem
CERT_CRT    := $(CERT_DIR)/localhost-cert.pem

REQ_DEV     ?= requirements-dev.txt
REQ_MAIN    ?= requirements.txt

PY          ?= python

.PHONY: default run run-http run-prod-gunicorn run-prod-uvicorn run-prod-waitress test install-dev install-prod certs clean-certs
.DEFAULT_GOAL := run-prod-uvicorn

# ---------- Dev (HTTPS local opcional) ----------
run: install-dev certs
	FLASK_DEBUG=1 flask --app $(APP) run --host $(HOST) --port $(PORT) \
	  --cert "$(CERT_CRT)" --key "$(CERT_KEY)"

run-http: install-dev
	FLASK_DEBUG=1 flask --app $(APP) run --host $(HOST) --port $(PORT)

# ---------- Prod local (seu VPS / SSH). Em hospedagem compartilhada, use WSGI/Passenger abaixo ----------
run-prod-uvicorn: install-prod certs
	uvicorn $(ASGI_APP) \
	  --host 0.0.0.0 --port $(PORT) \
	  --workers $(UVICORN_WORKERS) \
	  --timeout-keep-alive $(UVICORN_KEEP_ALIVE) \
	  --ssl-certfile "$(CERT_CRT)" --ssl-keyfile "$(CERT_KEY)"

run-prod-gunicorn: run-prod-uvicorn

run-prod-waitress: install-prod
	waitress-serve --host=0.0.0.0 --port=$(PORT) $(APP)

test:
	pytest -v --disable-warnings --maxfail=1

install-dev:
	if [ -f "$(REQ_DEV)" ]; then \
		$(PY) -m pip install -r "$(REQ_DEV)"; \
	elif [ -f "$(REQ_MAIN)" ]; then \
		$(PY) -m pip install -r "$(REQ_MAIN)"; \
	else \
		echo "Nenhum requirements encontrado."; \
	fi

install-prod:
	$(PY) -m pip install -r requirements.txt

certs:
	mkdir -p "$(CERT_DIR)"
	if [ ! -f "$(CERT_KEY)" ] || [ ! -f "$(CERT_CRT)" ]; then \
		openssl req -x509 -newkey rsa:4096 -nodes \
			-keyout "$(CERT_KEY)" -out "$(CERT_CRT)" \
			-days $(CERT_DAYS) -subj "/CN=localhost"; \
		chmod 600 "$(CERT_KEY)"; \
	fi

clean-certs:
	rm -f "$(CERT_KEY)" "$(CERT_CRT)"
