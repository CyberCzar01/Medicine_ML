from fastapi.testclient import TestClient

from urotriage.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "rule_version" in body["versions"]


def test_version():
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json()["schema_version"]


def test_schema():
    r = client.get("/schema")
    assert r.status_code == 200
    body = r.json()
    assert "age" in body["input_fields"]
    assert body["zones"] == ["green", "yellow", "red"]


def test_predict_red():
    r = client.post("/predict", json={
        "creatinine": 156, "temp": 38.4, "crp": 84, "wbc": 14.2,
        "diagnosis_text": "ОЗМ на фоне ДГПЖ", "imaging_text": "двусторонний гидронефроз",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["final_zone"] == "red"
    assert body["rule"]["zone"] == "red"
    assert len(body["rule"]["fired_criteria"]) >= 1


def test_predict_minimal():
    r = client.post("/predict", json={"diagnosis_text": "Острая задержка мочи"})
    assert r.status_code == 200
    body = r.json()
    assert body["final_zone"] in ("green", "yellow", "red")
    assert "disclaimers" in body


def test_predict_rejects_absurd_values():
    r = client.post("/predict", json={"temp": 384})
    assert r.status_code == 422


def test_batch_empty_rejected():
    r = client.post("/predict/batch", json={"patients": []})
    assert r.status_code == 422


def test_predict_batch():
    r = client.post("/predict/batch", json={"patients": [
        {"creatinine": 156, "imaging_text": "гидронефроз"},
        {"diagnosis_text": "Острая задержка мочи", "creatinine": 85, "temp": 36.6, "crp": 4, "wbc": 7, "imaging_text": "норма"},
    ]})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 2
    assert results[0]["final_zone"] == "red"
