FROM debian:11-slim AS build

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes python3-venv gcc libpython3-dev default-libmysqlclient-dev && \
    python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools
