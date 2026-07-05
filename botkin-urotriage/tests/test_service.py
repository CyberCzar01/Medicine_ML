from urotriage import service


def test_red_case_stays_red():
    r = service.predict({
        "creatinine": 156, "temp": 38.4, "crp": 84, "wbc": 14.2,
        "diagnosis_text": "Острая задержка мочи на фоне ДГПЖ",
        "imaging_text": "Двусторонний гидронефроз",
    })
    assert r["final_zone"] == "red"
    assert r["rule"]["zone"] == "red"


def test_green_case_zone_not_red():
    r = service.predict({
        "age": 60, "sex": "Мужской", "creatinine": 85, "temp": 36.6,
        "crp": 4, "wbc": 7, "hemoglobin": 145,
        "diagnosis_text": "Острая задержка мочи", "imaging_text": "без патологии",
        "residual_urine_ml": 150,
    })
    assert r["rule"]["zone"] == "green"
    assert r["final_zone"] in ("green", "yellow")
    assert r["versions"]["rule_version"]


def test_ml_present_has_probability():
    r = service.predict({"age": 70, "sex": "Мужской", "creatinine": 90, "temp": 36.6,
                         "crp": 5, "wbc": 7, "hemoglobin": 130, "imaging_text": "норма"})
    if service.model_loaded():
        assert r["ml"]["explanations_available"] is True
        assert r["ml"]["probability"] is not None
        assert len(r["ml"]["top_features"]) > 0


def test_batch_matches_single():
    patients = [
        {"creatinine": 156, "temp": 38.4, "crp": 84, "wbc": 14.2,
         "diagnosis_text": "ОЗМ на фоне ДГПЖ", "imaging_text": "двусторонний гидронефроз"},
        {"age": 60, "sex": "Мужской", "creatinine": 85, "temp": 36.6, "crp": 4, "wbc": 7,
         "hemoglobin": 145, "diagnosis_text": "Острая задержка мочи", "imaging_text": "без патологии"},
        {"diagnosis_text": "Острая задержка мочи"},
    ]
    batch = service.predict_batch(patients)
    singles = [service.predict(p) for p in patients]
    assert [b["final_zone"] for b in batch] == [s["final_zone"] for s in singles]
    assert [b["ml"]["probability"] for b in batch] == [s["ml"]["probability"] for s in singles]
    assert [b["rule"]["fired_criteria"] for b in batch] == [s["rule"]["fired_criteria"] for s in singles]


def test_empty_batch():
    assert service.predict_batch([]) == []
