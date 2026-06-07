import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from urotriage.config import SURVEY_CLEAN_CSV, RESULTS_DIR
from urotriage import service


def _row_to_patient(row):
    def g(k):
        v = row.get(k)
        return None if pd.isna(v) else v
    return {
        "age": g("age"),
        "sex": g("sex"),
        "temp": g("temp"),
        "bp_sys": g("bp_sys"),
        "bp_dia": g("bp_dia"),
        "pulse": g("pulse"),
        "creatinine": g("creatinine"),
        "urea": g("urea"),
        "crp": g("crp"),
        "hemoglobin": g("hgb"),
        "wbc": g("wbc"),
        "residual_urine_ml": g("drained_volume_ml"),
        "diagnosis_text": g("diagnosis"),
        "complaints_text": g("complaints"),
        "imaging_text": None,
    }


def main():
    if not SURVEY_CLEAN_CSV.exists():
        raise FileNotFoundError(f"{SURVEY_CLEAN_CSV} not found; run scripts/clean_survey.py first")
    df = pd.read_csv(SURVEY_CLEAN_CSV)
    rows = []
    zone_counts = {"green": 0, "yellow": 0, "red": 0}
    fired = {}
    for _, row in df.iterrows():
        res = service.predict(_row_to_patient(row))
        zone_counts[res["final_zone"]] += 1
        for c in res["rule"]["fired_criteria"]:
            fired[c["code"]] = fired.get(c["code"], 0) + 1
        rec = {
            "final_zone": res["final_zone"],
            "rule_zone": res["rule"]["zone"],
            "ml_probability": res["ml"]["probability"],
            "ml_action": res["ml"]["action"],
            "fired": "|".join(c["code"] for c in res["rule"]["fired_criteria"]),
        }
        if "had_operation" in df.columns:
            rec["had_operation"] = row.get("had_operation")
        rows.append(rec)

    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "survey_with_zones.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    summary = {
        "n": int(len(df)),
        "model_loaded": service.model_loaded(),
        "zone_counts": zone_counts,
        "rule_fired_counts": dict(sorted(fired.items(), key=lambda kv: kv[1], reverse=True)),
        "note": "Plumbing/sanity check on real survey data; not a clinical validation (no expert green/yellow/red labels yet).",
    }
    with open(RESULTS_DIR / "survey_validation.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
