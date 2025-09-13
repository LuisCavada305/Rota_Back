SHELL := /bin/bash

# -------- Config ----------
HOST        ?= 0.0.0.0
PORT        ?= 8001
APP         ?= app.main:app
CERT_DIR    ?= $(PWD)/certs
CERT_DAYS   ?= 365
CERT_KEY    := $(CERT_DIR)/localhost-key.pem
CERT_CRT    := $(CERT_DIR)/localhost-cert.pem

REQ_DEV     ?= requirements-dev.txt
REQ_MAIN    ?= requirements.txt

UVICORN_OPTS ?= --reload

.PHONY: default run run-http test install-dev certs clean-certs

default: run

# ---------- Tasks ----------
run: install-dev certs
	uvicorn $(APP) --host $(HOST) --port $(PORT) $(UVICORN_OPTS) \
	  --ssl-certfile "$(CERT_CRT)" --ssl-keyfile "$(CERT_KEY)"

run-http: install-dev
	uvicorn $(APP) --host $(HOST) --port $(PORT) $(UVICORN_OPTS)

test:
	pytest -v --disable-warnings --maxfail=1

install-dev:
	if [ -f "$(REQ_DEV)" ]; then \
		python -m pip install -r "$(REQ_DEV)"; \
	elif [ -f "$(REQ_MAIN)" ]; then \
		python -m pip install -r "$(REQ_MAIN)"; \
	else \
		echo "Nenhum requirements encontrado."; \
	fi

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

run-server: install-prod
	uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

install-prod:
	python -m pip install -r requirements.txt
