import logging
import math
import threading

import pandas as pd
import joblib
from sklearn import __version__ as SKLEARN_VERSION

from urotriage.config import (
    ML_FEATURES,
    MODEL_PATH,
    RULE_VERSION,
    THRESHOLD_VERSION,
    SCHEMA_VERSION,
    DISCLAIMERS,
)
from urotriage.features import build_feature_frame
from urotriage.rule import evaluate_rule
from urotriage.explain import explain_patient

_log = logging.getLogger("urotriage.service")

_ARTIFACT = None
_ARTIFACT_LOADED = False
_ARTIFACT_LOCK = threading.Lock()

_API_TO_SURVEY = {
    "age": "age",
    "sex": "sex",
    "temp": "temp",
    "bp_sys": "bp_sys",
    "bp_dia": "bp_dia",
    "pulse": "pulse",
    "hemoglobin": "hgb",
    "creatinine": "creatinine",
    "urea": "urea",
    "crp": "crp",
    "wbc": "wbc",
    "diagnosis_text": "diagnosis",
    "complaints_text": "complaints",
}


def load_artifact(force=False):
    global _ARTIFACT, _ARTIFACT_LOADED
    if _ARTIFACT_LOADED and not force:
        return _ARTIFACT
    with _ARTIFACT_LOCK:
        if _ARTIFACT_LOADED and not force:
            return _ARTIFACT
        artifact = None
        if MODEL_PATH.exists():
            try:
                artifact = joblib.load(MODEL_PATH)
            except Exception:
                _log.exception(
                    "Не удалось загрузить ML-модель из %s; сервис работает только на правиле", MODEL_PATH
                )
        _ARTIFACT = artifact
        _ARTIFACT_LOADED = True
        return _ARTIFACT


def model_loaded():
    return load_artifact() is not None


def _ml_features(patients):
    rows = [
        {survey_key: p.get(api_key) for api_key, survey_key in _API_TO_SURVEY.items()}
        for p in patients
    ]
    frame = build_feature_frame(pd.DataFrame(rows), source="survey", include_target=False)
    return frame.reindex(columns=ML_FEATURES)


def _clean_value(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def versions():
    artifact = load_artifact()
    return {
        "rule_version": RULE_VERSION,
        "model_version": artifact["model_version"] if artifact else None,
        "threshold_version": artifact["threshold_version"] if artifact else THRESHOLD_VERSION,
        "schema_version": SCHEMA_VERSION,
        "sklearn_version": SKLEARN_VERSION,
    }


def _rule_only_response(rule_result, vers):
    rule_zone = rule_result["zone"]
    return {
        "final_zone": rule_zone,
        "final_reason": f"rule_{rule_zone}",
        "rule": rule_result,
        "ml": {
            "probability": None,
            "proxy_zone": None,
            "action": "model_unavailable",
            "message": "ML-модель не загружена; зона определена только правилом.",
            "top_features": [],
            "explanations_available": False,
        },
        "versions": vers,
        "disclaimers": DISCLAIMERS,
    }


def _ml_response(rule_result, feature_row, probability, artifact, vers):
    rule_zone = rule_result["zone"]
    threshold = float(artifact["green_upgrade_threshold"])
    proxy_zone = "high" if probability >= threshold else "low"

    if rule_zone == "green" and probability >= threshold:
        final_zone = "yellow"
        final_reason = "ml_disagreement_upgrade"
        action = "upgrade_to_yellow"
        message = "Правило не нашло red/yellow критериев, но ML-риск эскалации выше порога; рекомендуется клиническая перепроверка."
    else:
        final_zone = rule_zone
        final_reason = f"rule_{rule_zone}"
        action = "none"
        message = "ML согласуется с правилом или зона определена правилом."

    feature_values = {k: _clean_value(v) for k, v in feature_row.to_dict().items()}
    top_features = explain_patient(artifact["feature_importances"], feature_values)

    return {
        "final_zone": final_zone,
        "final_reason": final_reason,
        "rule": rule_result,
        "ml": {
            "probability": round(probability, 4),
            "proxy_zone": proxy_zone,
            "action": action,
            "message": message,
            "top_features": top_features,
            "explanations_available": True,
        },
        "versions": vers,
        "disclaimers": DISCLAIMERS,
    }


def predict(patient):
    return predict_batch([patient])[0]


def predict_batch(patients):
    if not patients:
        return []
    rule_results = [evaluate_rule(p) for p in patients]
    artifact = load_artifact()
    vers = versions()
    if artifact is None:
        return [_rule_only_response(r, vers) for r in rule_results]
    X = _ml_features(patients)
    probabilities = artifact["calibrated"].predict_proba(X)[:, 1]
    return [
        _ml_response(rule_results[i], X.iloc[i], float(probabilities[i]), artifact, vers)
        for i in range(len(patients))
    ]
