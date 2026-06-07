import math

import pandas as pd
import joblib
from sklearn import __version__ as SKLEARN_VERSION

from urotriage.config import (
    ML_FEATURES,
    MODEL_PATH,
    RULE_VERSION,
    MODEL_VERSION,
    THRESHOLD_VERSION,
    SCHEMA_VERSION,
    DISCLAIMERS,
)
from urotriage.features import build_feature_frame
from urotriage.rule import evaluate_rule
from urotriage.explain import explain_patient

_ARTIFACT = None
_ARTIFACT_LOADED = False

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
    if MODEL_PATH.exists():
        _ARTIFACT = joblib.load(MODEL_PATH)
    else:
        _ARTIFACT = None
    _ARTIFACT_LOADED = True
    return _ARTIFACT


def model_loaded():
    return load_artifact() is not None


def _survey_row(patient):
    row = {}
    for api_key, survey_key in _API_TO_SURVEY.items():
        row[survey_key] = patient.get(api_key)
    return pd.DataFrame([row])


def _ml_features(patient):
    frame = build_feature_frame(_survey_row(patient), source="survey", include_target=False)
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


def predict(patient):
    rule_result = evaluate_rule(patient)
    rule_zone = rule_result["zone"]
    artifact = load_artifact()

    if artifact is None:
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
            "versions": versions(),
            "disclaimers": DISCLAIMERS,
        }

    X = _ml_features(patient)
    probability = float(artifact["calibrated"].predict_proba(X)[:, 1][0])
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

    feature_values = {k: _clean_value(v) for k, v in X.iloc[0].to_dict().items()}
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
        "versions": versions(),
        "disclaimers": DISCLAIMERS,
    }


def predict_batch(patients):
    return [predict(p) for p in patients]
