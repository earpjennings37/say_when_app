"""Say When cleanup app: Fall Cleaning #1 skeleton.

Serves the chore list and its photo rules, plus health and Prometheus
metrics endpoints. Photo checking arrives in Fall #6.
"""

import hmac
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Header, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

APP_VERSION = os.environ.get("APP_VERSION", "dev")
CHORES_FILE = Path(os.environ.get("CHORES_FILE", Path(__file__).parent / "chores.yaml"))
# The admin token arrives as a file mounted from a Kubernetes Secret
# (synced from AWS Secrets Manager by External Secrets, Fall #3).
ADMIN_TOKEN_FILE_DEFAULT = "/etc/say-when/secrets/admin_token"

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

def read_admin_token() -> str | None:
    """Read the token on every call so a rotated Secret takes effect without
    a restart. None means admin is not configured (fail closed)."""
    path = Path(os.environ.get("ADMIN_TOKEN_FILE", ADMIN_TOKEN_FILE_DEFAULT))
    try:
        token = path.read_text().strip()
    except FileNotFoundError:
        return None
    return token or None


@app.get("/admin/status")
def admin_status(x_admin_token: str | None = Header(default=None)) -> dict:
    """Internal check that the app received its secret. Requires the
    X-Admin-Token header. Not routed through Envoy (see the HTTPRoute)."""
    REQUESTS.labels(endpoint="admin").inc()
    expected = read_admin_token()
    if expected is None:
        raise HTTPException(status_code=503, detail="Admin is not configured")
    if x_admin_token is None or not hmac.compare_digest(
        x_admin_token.encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return {
        "status": "ok",
        "admin": True,
        "version": APP_VERSION,
        "chores": len(load_chores()["chores"]),
    }