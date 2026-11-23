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

# ---------- /admin/status (Fall #3) ----------

def test_admin_not_configured_is_503(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_TOKEN_FILE", str(tmp_path / "missing"))
    assert client.get("/admin/status").status_code == 503


def test_admin_wrong_or_missing_token_is_401(monkeypatch, tmp_path):
    token_file = tmp_path / "admin_token"
    token_file.write_text("s3cret\n")
    monkeypatch.setenv("ADMIN_TOKEN_FILE", str(token_file))
    assert client.get("/admin/status").status_code == 401
    assert client.get("/admin/status", headers={"X-Admin-Token": "nope"}).status_code == 401


def test_admin_right_token_is_200(monkeypatch, tmp_path):
    token_file = tmp_path / "admin_token"
    token_file.write_text("s3cret\n")
    monkeypatch.setenv("ADMIN_TOKEN_FILE", str(token_file))
    r = client.get("/admin/status", headers={"X-Admin-Token": "s3cret"})
    assert r.status_code == 200
    assert r.json()["admin"] is True
    assert "s3cret" not in r.text  # never echo the secret


def test_admin_token_rotation_needs_no_restart(monkeypatch, tmp_path):
    token_file = tmp_path / "admin_token"
    monkeypatch.setenv("ADMIN_TOKEN_FILE", str(token_file))
    token_file.write_text("one")
    assert client.get("/admin/status", headers={"X-Admin-Token": "one"}).status_code == 200
    token_file.write_text("two")  # simulate the kubelet refreshing the Secret
    assert client.get("/admin/status", headers={"X-Admin-Token": "one"}).status_code == 401
    assert client.get("/admin/status", headers={"X-Admin-Token": "two"}).status_code == 200