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
