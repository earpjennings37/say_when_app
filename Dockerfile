# syntax=docker/dockerfile:1

# ---------- Stage 1: build (install dependencies) ----------
FROM python:3.13-slim AS build
WORKDIR /src
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime (only what's needed to run) ----------
FROM python:3.13-slim

# CI passes the git SHA here; it shows up at /version and on the /docs badge.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# NEW: apply Debian security patches newer than the base image (e.g. zlib),
# then remove pip. The app never installs anything at runtime, and pip's
# bundled libraries (msgpack, urllib3, setuptools) carried 5 HIGH CVEs.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip

# A user with no password, no home and no login shell. The app never runs as root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=build /install /usr/local
COPY app/ ./app/

USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
