from fastapi.testclient import TestClient

from app.main import app, load_chores

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chores_file_has_ten_valid_chores():
    data = load_chores()
    chores = data["chores"]
    assert data["season"] == "fall"
    assert len(chores) == 10
    assert len({c["id"] for c in chores}) == 10, "chore ids must be unique"
    for c in chores:
        assert c["expect"], f"{c['id']} needs at least one expected label"
        assert 0 < c["min_confidence"] <= 100


def test_get_one_chore():
    r = client.get("/chores/rake-leaves")
    assert r.status_code == 200
    assert "Rake" in r.json()["expect"]


def test_unknown_chore_is_404():
    assert client.get("/chores/shovel-snow").status_code == 404


def test_metrics_counts_requests():
    client.get("/healthz")
    body = client.get("/metrics").text
    assert 'cleanup_http_requests_total{endpoint="healthz"}' in body