"""Fast tests: no network, no AWS. CI runs these before building the image."""

from fastapi.testclient import TestClient

from app.main import app, load_chores

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chores_file_has_ten_valid_chores():
    """Catches typos in chores.yaml before they ever reach the cluster."""
    data = load_chores()
    assert data["season"] == "fall"
    chores = data["chores"]
    assert len(chores) == 10
    ids = [c["id"] for c in chores]
    assert len(set(ids)) == len(ids), "chore ids must be unique"
    for c in chores:
        assert c["expect"], f"{c['id']} has no expected labels"
        assert 0 < c["min_confidence"] <= 100


def test_get_one_chore():
    r = client.get("/chores/rake-leaves")
    assert r.status_code == 200
    assert "Rake" in r.json()["expect"]


def test_unknown_chore_is_404():
    r = client.get("/chores/shovel-snow")
    assert r.status_code == 404


def test_metrics_counts_requests():
    client.get("/healthz")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert 'cleanup_http_requests_total{endpoint="healthz"}' in r.text
