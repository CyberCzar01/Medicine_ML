import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
from sklearn import __version__ as SKLEARN_VERSION
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)

from urotriage.config import (
    ML_FEATURES,
    RANDOM_STATE,
    MODEL_VERSION,
    THRESHOLD_VERSION,
    SCHEMA_VERSION,
    MODEL_PATH,
    MODELS_DIR,
    RESULTS_DIR,
    ML_THRESHOLD_POLICY,
)
from urotriage.io_data import load_raw
from urotriage.cohort import filter_cohort
from urotriage.features import build_feature_frame
from urotriage.target import build_escalation_target
from urotriage.rule import evaluate_rule

warnings.filterwarnings("ignore")


_IMAGING_KEYS = ("почек", "мочевого пузыря", "остаточн", "предстательной", "мочевыводящ", "забрюшин")


def _imaging_text(df):
    cols = [
        c for c in df.columns
        if c.endswith("_conclusion")
        and "ультразвук" in c.lower()
        and any(k in c.lower() for k in _IMAGING_KEYS)
    ]
    if not cols:
        return pd.Series("", index=df.index)
    return df[cols].fillna("").astype(str).agg(" ".join, axis=1)


def _rule_zones(df):
    imaging = _imaging_text(df)
    creat = pd.to_numeric(df.get("laba_Определение креатинина"), errors="coerce")
    urea = pd.to_numeric(df.get("laba_Определение мочевины"), errors="coerce")
    temp = pd.to_numeric(df.get("triage_temp"), errors="coerce")
    crp = pd.to_numeric(df.get("laba_Определение белков острой фазы С-реактивный белок"), errors="coerce")
    wbc = pd.to_numeric(df.get("laba_Количество лейкоцитов (WBC)"), errors="coerce")
    hgb = pd.to_numeric(df.get("laba_Гемоглобин (HGB)"), errors="coerce")
    diag = df.get("adm_ds_name")
    comp = df.get("triage_complaints")
    zones = []
    for i in df.index:
        patient = {
            "creatinine": creat.get(i),
            "urea": urea.get(i),
            "temperature": temp.get(i),
            "crp": crp.get(i),
            "wbc": wbc.get(i),
            "hemoglobin": hgb.get(i),
            "diagnosis_text": diag.get(i) if diag is not None else None,
            "complaints_text": comp.get(i) if comp is not None else None,
            "imaging_text": imaging.get(i),
        }
        zones.append(evaluate_rule(patient)["zone"])
    return np.array(zones)


def _ece(y, p, bins=10):
    y = np.asarray(y)
    p = np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    total = len(y)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if not m.any():
            continue
        conf = p[m].mean()
        acc = y[m].mean()
        ece += abs(conf - acc) * m.sum() / total
    return float(ece)


def _select_green_upgrade_threshold(y_green, p_green, policy):
    if len(y_green) == 0 or y_green.sum() == 0:
        return 0.5
    min_sens = policy["green_upgrade_min_sensitivity"]
    max_share = policy["green_upgrade_max_share"]
    pos = y_green == 1
    rows = []
    for t in np.arange(0.05, 0.951, 0.01):
        upg = p_green >= t
        share = float(upg.mean())
        sens = float((upg & pos).sum() / pos.sum())
        rows.append((round(float(t), 3), share, sens))
    ok = [r for r in rows if r[2] >= min_sens and r[1] <= max_share]
    if ok:
        return max(ok, key=lambda r: (r[2], -r[1]))[0]
    capped = [r for r in rows if r[1] <= max_share]
    if capped:
        return max(capped, key=lambda r: r[2])[0]
    return float(rows[-1][0])


def train():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw()
    cohort, n_cohort = filter_cohort(raw)
    target, components = build_escalation_target(cohort)
    cohort = cohort.copy()
    cohort["target"] = target.values

    frame = build_feature_frame(cohort, source="train", include_target=True)
    X = frame[ML_FEATURES].copy()
    y = frame["target"].astype(int).values
    rule_zones = _rule_zones(cohort)

    idx = np.arange(len(X))
    idx_tmp, idx_test = train_test_split(idx, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    idx_train, idx_val = train_test_split(idx_tmp, test_size=0.25, random_state=RANDOM_STATE, stratify=y[idx_tmp])

    X_train, X_val, X_test = X.iloc[idx_train], X.iloc[idx_val], X.iloc[idx_test]
    y_train, y_val, y_test = y[idx_train], y[idx_val], y[idx_test]
    rz_val, rz_test = rule_zones[idx_val], rule_zones[idx_test]

    base = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.05, max_iter=400,
        l2_regularization=1.0, class_weight="balanced", random_state=RANDOM_STATE,
    )

    calibrators = {}
    for method in ("isotonic", "sigmoid"):
        cal = CalibratedClassifierCV(base, method=method, cv=5)
        cal.fit(X_train, y_train)
        p_val = cal.predict_proba(X_val)[:, 1]
        calibrators[method] = (cal, brier_score_loss(y_val, p_val))
    best_method = min(calibrators, key=lambda m: calibrators[m][1])
    model = calibrators[best_method][0]

    p_val = model.predict_proba(X_val)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    green_val = rz_val == "green"
    threshold = _select_green_upgrade_threshold(y_val[green_val], p_val[green_val], ML_THRESHOLD_POLICY)

    perm = permutation_importance(
        model, X_val, y_val, scoring="average_precision",
        n_repeats=10, random_state=RANDOM_STATE,
    )
    importances = {f: float(w) for f, w in zip(ML_FEATURES, perm.importances_mean)}

    green_test = rz_test == "green"
    yg = y_test[green_test]
    pg = p_test[green_test]
    upg = pg >= threshold
    pos_g = yg == 1
    uplift = {
        "rule_green_n": int(green_test.sum()),
        "rule_green_escalation_positives": int(pos_g.sum()),
        "ml_upgraded_n": int(upg.sum()),
        "ml_upgraded_share": float(upg.mean()) if len(pg) else 0.0,
        "captured_positives": int((upg & pos_g).sum()),
        "captured_sensitivity": float((upg & pos_g).sum() / pos_g.sum()) if pos_g.sum() else None,
        "false_upgrade_rate": float((upg & ~pos_g).sum() / upg.sum()) if upg.sum() else None,
        "brier_in_green": float(brier_score_loss(yg, pg)) if len(yg) and len(set(yg)) > 1 else None,
        "ece_in_green": _ece(yg, pg) if len(yg) else None,
    }

    def zone_counts(z):
        vals, cnts = np.unique(z, return_counts=True)
        return {str(v): int(c) for v, c in zip(vals, cnts)}

    results = {
        "version": "v4.0",
        "timestamp": datetime.now().isoformat(),
        "model_version": MODEL_VERSION,
        "threshold_version": THRESHOLD_VERSION,
        "schema_version": SCHEMA_VERSION,
        "sklearn_version": SKLEARN_VERSION,
        "cohort_n_in_full": n_cohort,
        "cohort_n_features": len(X),
        "target_definition": "escalation_proxy = cystostomy/epicystostomy OR in-hospital death",
        "target_components": components,
        "target_prevalence": float(y.mean()),
        "calibration_method": best_method,
        "calibration_brier_val": {m: float(v[1]) for m, v in calibrators.items()},
        "green_upgrade_threshold": threshold,
        "ml_threshold_policy": ML_THRESHOLD_POLICY,
        "split_sizes": {"train": len(X_train), "val": len(X_val), "test": len(X_test)},
        "test_metrics": {
            "roc_auc": float(roc_auc_score(y_test, p_test)),
            "pr_auc": float(average_precision_score(y_test, p_test)),
            "brier": float(brier_score_loss(y_test, p_test)),
            "ece": _ece(y_test, p_test),
        },
        "rule_zone_distribution_val": zone_counts(rz_val),
        "rule_zone_distribution_test": zone_counts(rz_test),
        "ml_green_upgrade_uplift_test": uplift,
        "feature_importances": importances,
    }

    artifact = {
        "calibrated": model,
        "features": ML_FEATURES,
        "model_version": MODEL_VERSION,
        "threshold_version": THRESHOLD_VERSION,
        "schema_version": SCHEMA_VERSION,
        "sklearn_version": SKLEARN_VERSION,
        "calibration_method": best_method,
        "green_upgrade_threshold": threshold,
        "ml_threshold_policy": ML_THRESHOLD_POLICY,
        "feature_importances": importances,
        "target_definition": results["target_definition"],
    }
    joblib.dump(artifact, MODEL_PATH)

    with open(RESULTS_DIR / "results_v4.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    loaded = joblib.load(MODEL_PATH)
    smoke = X_test.iloc[[0]]
    _ = float(loaded["calibrated"].predict_proba(smoke)[:, 1][0])

    return results


if __name__ == "__main__":
    r = train()
    print(json.dumps(r, ensure_ascii=False, indent=2))
