import re

from urotriage.config import (
    RULE_THRESHOLDS as T,
    RULE_PATTERNS as P,
    COHORT_RETENTION_RE,
    RULE_VERSION,
)

_retention_re = re.compile(COHORT_RETENTION_RE)
_patterns = {k: re.compile(v) for k, v in P.items()}
_negation_re = re.compile(r"\bнет\b|\bбез\b|\bне выявл|\bне отмеч|\bотрицает|\bисключен|\bне определ|\bне обнаруж|\bне наблюд")

_NEGATION_WINDOW = 28


def _f(x):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return v


def _norm(text):
    if text is None:
        return ""
    return str(text).lower().replace("ё", "е")


def _has(pattern_key, *texts):
    rx = _patterns[pattern_key]
    for t in texts:
        s = _norm(t)
        for m in rx.finditer(s):
            left = s[max(0, m.start() - _NEGATION_WINDOW):m.start()]
            right = s[m.end():m.end() + _NEGATION_WINDOW]
            if not _negation_re.search(left) and not _negation_re.search(right):
                return True
    return False


def evaluate_rule(patient):
    creatinine = _f(patient.get("creatinine"))
    urea = _f(patient.get("urea"))
    temp = _f(patient.get("temperature", patient.get("temp")))
    crp = _f(patient.get("crp"))
    wbc = _f(patient.get("wbc"))
    hemoglobin = _f(patient.get("hemoglobin"))
    residual = _f(patient.get("residual_urine_ml"))

    diagnosis = _norm(patient.get("diagnosis_text"))
    complaints = _norm(patient.get("complaints_text"))
    imaging = _norm(patient.get("imaging_text"))
    clinical = " ".join([diagnosis, complaints])

    red = []
    yellow = []

    if creatinine is not None and creatinine >= T["creatinine_red"]:
        red.append(_c("renal_dysfunction", "red",
                      f"Креатинин {creatinine:.0f} мкмоль/л ≥ {T['creatinine_red']:.0f} (почечная дисфункция, требует клинической интерпретации)"))
    elif creatinine is None and urea is not None and urea >= T["urea_red"]:
        red.append(_c("renal_dysfunction", "red",
                      f"Мочевина {urea:.1f} ммоль/л ≥ {T['urea_red']:.0f} (почечная дисфункция, требует клинической интерпретации)"))

    hydronephrosis_red = _has("hydronephrosis_red", imaging, diagnosis)
    if hydronephrosis_red:
        red.append(_c("hydronephrosis", "red", "Гидронефроз/обструкция верхних мочевых путей по визуализации/диагнозу"))

    inflammatory = (crp is not None and crp > T["crp_red"]) or (wbc is not None and wbc > T["wbc_red"])
    febrile = temp is not None and temp >= T["temp_red"]
    infection_dx = _has("infection_dx", diagnosis)
    infection_red = (febrile and inflammatory) or (infection_dx and (febrile or inflammatory))
    if infection_red:
        red.append(_c("infection_systemic", "red", "Системная инфекция: лихорадка и/или воспалительные маркеры (возможен уросепсис/пиелонефрит)"))

    hematuria_any = _has("hematuria_any", clinical, imaging)
    severe_hematuria = _has("hematuria_severe", clinical, imaging) or (
        hematuria_any and hemoglobin is not None and hemoglobin < T["hemoglobin_anemia"]
    )
    if severe_hematuria:
        red.append(_c("hematuria_severe", "red", "Макрогематурия со сгустками/тампонадой/кровотечением или анемией"))

    if _has("failed_catheter", clinical):
        red.append(_c("failed_catheterization", "red", "Неэффективная/невозможная катетеризация (провал первичной декомпрессии)"))

    if _has("hydronephrosis_yellow", imaging, diagnosis) and not hydronephrosis_red:
        yellow.append(_c("pyeloectasia", "yellow", "Пиелоэктазия/расширение ЧЛС без явного гидронефроза"))

    if febrile and not infection_red:
        yellow.append(_c("isolated_fever", "yellow",
                         f"Лихорадка {temp:.1f} ≥ {T['temp_red']:.1f} без подтверждённых воспалительных маркеров — исключить инфекцию, дообследовать"))
    elif temp is not None and T["temp_yellow_low"] <= temp < T["temp_red"]:
        yellow.append(_c("low_grade_fever", "yellow", f"Субфебрильная температура {temp:.1f}"))

    if _has("severe_pain", clinical):
        yellow.append(_c("severe_pain", "yellow", "Выраженный болевой синдром"))

    if residual is not None and residual >= T["residual_urine_yellow"]:
        msg = f"Большой объём остаточной мочи {residual:.0f} мл ≥ {T['residual_urine_yellow']:.0f}"
        if residual >= T["residual_urine_strong"]:
            msg += " (значительный объём)"
        yellow.append(_c("high_residual_urine", "yellow", msg))

    if hematuria_any and not severe_hematuria:
        yellow.append(_c("macrohematuria", "yellow", "Изолированная макрогематурия без признаков тяжёлого кровотечения"))

    resolved = {"creatinine": creatinine, "temp": temp, "crp": crp, "wbc": wbc}
    missing_fields = [k for k, v in resolved.items() if v is None]
    if not imaging:
        missing_fields.append("imaging_text")

    data_quality_warnings = [f"Поле '{f}' не заполнено" for f in missing_fields]

    retention_confirmed = bool(_retention_re.search(diagnosis) or _retention_re.search(complaints))
    no_lab_assessment = creatinine is None and crp is None and wbc is None
    no_imaging_assessment = not imaging
    if retention_confirmed and no_lab_assessment and no_imaging_assessment and not red:
        yellow.append(_c("critical_data_incomplete", "yellow",
                         "Подтверждённая ОЗМ без лабораторной и инструментальной оценки риска — нужен очный осмотр и дообследование"))

    if red:
        zone = "red"
    elif yellow:
        zone = "yellow"
    else:
        zone = "green"

    return {
        "zone": zone,
        "rule_version": RULE_VERSION,
        "fired_criteria": red + yellow,
        "missing_fields": missing_fields,
        "data_quality_warnings": data_quality_warnings,
    }


def _c(code, zone, message):
    return {"code": code, "zone": zone, "message": message}
