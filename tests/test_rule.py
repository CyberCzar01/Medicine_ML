from urotriage.rule import evaluate_rule


def codes(result):
    return {c["code"] for c in result["fired_criteria"]}


def test_red_renal_dysfunction():
    r = evaluate_rule({"creatinine": 200, "temperature": 36.6, "crp": 5, "wbc": 7, "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "renal_dysfunction" in codes(r)


def test_red_hydronephrosis():
    r = evaluate_rule({"creatinine": 90, "imaging_text": "двусторонний гидронефроз"})
    assert r["zone"] == "red"
    assert "hydronephrosis" in codes(r)


def test_red_infection():
    r = evaluate_rule({"temperature": 38.6, "crp": 120, "wbc": 16, "creatinine": 90, "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "infection_systemic" in codes(r)


def test_red_failed_catheter():
    r = evaluate_rule({"creatinine": 90, "complaints_text": "невозможно установить катетер", "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "failed_catheterization" in codes(r)


def test_red_severe_hematuria():
    r = evaluate_rule({"creatinine": 90, "complaints_text": "макрогематурия со сгустками, тампонада", "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "hematuria_severe" in codes(r)


def test_yellow_high_residual():
    r = evaluate_rule({"creatinine": 90, "temperature": 36.6, "crp": 5, "wbc": 7, "residual_urine_ml": 700, "imaging_text": "норма"})
    assert r["zone"] == "yellow"
    assert "high_residual_urine" in codes(r)


def test_yellow_pyeloectasia_not_red():
    r = evaluate_rule({"creatinine": 90, "temperature": 36.6, "crp": 5, "wbc": 7, "imaging_text": "пиелоэктазия слева"})
    assert r["zone"] == "yellow"
    assert "pyeloectasia" in codes(r)
    assert "hydronephrosis" not in codes(r)


def test_yellow_low_grade_fever():
    r = evaluate_rule({"creatinine": 90, "temperature": 37.7, "crp": 10, "wbc": 8, "imaging_text": "норма"})
    assert r["zone"] == "yellow"
    assert "low_grade_fever" in codes(r)


def test_yellow_critical_incomplete():
    r = evaluate_rule({"diagnosis_text": "Острая задержка мочи"})
    assert r["zone"] == "yellow"
    assert "critical_data_incomplete" in codes(r)


def test_green_full_normal():
    r = evaluate_rule({"creatinine": 85, "temperature": 36.6, "crp": 4, "wbc": 7, "imaging_text": "без патологии", "residual_urine_ml": 150})
    assert r["zone"] == "green"
    assert r["fired_criteria"] == []


def test_missing_does_not_escalate():
    r = evaluate_rule({"creatinine": 85, "temperature": 36.6, "imaging_text": "без патологии"})
    assert r["zone"] == "green"
    assert "crp" in r["missing_fields"]
    assert "wbc" in r["missing_fields"]
    assert r["data_quality_warnings"]


def test_urea_not_red_when_creatinine_normal():
    r = evaluate_rule({"creatinine": 90, "urea": 25, "temperature": 36.6, "crp": 5, "wbc": 7, "imaging_text": "норма"})
    assert "renal_dysfunction" not in codes(r)


def test_urea_red_only_without_creatinine():
    r = evaluate_rule({"urea": 25, "temperature": 36.6, "crp": 5, "wbc": 7, "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "renal_dysfunction" in codes(r)


def test_negated_hematuria_not_red():
    r = evaluate_rule({"creatinine": 90, "temperature": 36.6, "crp": 5, "wbc": 7, "complaints_text": "без сгустков, кровотечения нет", "imaging_text": "норма"})
    assert "hematuria_severe" not in codes(r)


def test_negated_hydronephrosis_not_red():
    r = evaluate_rule({"creatinine": 90, "temperature": 36.6, "crp": 5, "wbc": 7, "imaging_text": "без гидронефроза, обструкции нет"})
    assert "hydronephrosis" not in codes(r)


def test_infection_dx_with_marker_no_fever_is_red():
    r = evaluate_rule({"diagnosis_text": "острый пиелонефрит", "crp": 60, "temperature": 36.6, "wbc": 9, "creatinine": 90, "imaging_text": "норма"})
    assert r["zone"] == "red"
    assert "infection_systemic" in codes(r)


def test_infection_dx_without_markers_not_red():
    r = evaluate_rule({"diagnosis_text": "пиелонефрит", "creatinine": 90, "imaging_text": "норма"})
    assert "infection_systemic" not in codes(r)
