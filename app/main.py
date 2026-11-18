"""Say When cleanup app: Fall Cleaning #1 skeleton.

Serves the chore list and its photo rules, plus health and Prometheus
metrics endpoints. Photo checking arrives in Fall #6.
"""

import os
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

APP_VERSION = os.environ.get("APP_VERSION", "dev")
CHORES_FILE = Path(os.environ.get("CHORES_FILE", Path(__file__).parent / "chores.yaml"))

REQUESTS = Counter(
    "cleanup_http_requests_total",
    "HTTP requests handled, by endpoint.",
    ["endpoint"],
)


def load_chores() -> dict:
    with CHORES_FILE.open() as f:
        data = yaml.safe_load(f)
    return {"season": data["season"], "chores": data["chores"]}


app = FastAPI(title="Say When Cleanup", version=APP_VERSION)


@app.get("/healthz")
def healthz() -> dict:
    REQUESTS.labels(endpoint="healthz").inc()
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    REQUESTS.labels(endpoint="version").inc()
    return {"version": APP_VERSION}


@app.get("/chores")
def list_chores() -> dict:
    REQUESTS.labels(endpoint="chores").inc()
    return load_chores()


@app.get("/chores/{chore_id}")
def get_chore(chore_id: str) -> dict:
    REQUESTS.labels(endpoint="chore").inc()
    for chore in load_chores()["chores"]:
        if chore["id"] == chore_id:
            return chore
    raise HTTPException(status_code=404, detail=f"No chore called {chore_id!r}")


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)