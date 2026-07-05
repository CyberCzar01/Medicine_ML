import numpy as np
import pandas as pd

from urotriage.config import DIAG_FLAGS, COMPLAINT_FLAGS

TRAIN_COLUMNS = {
    "age": "age",
    "sex": "sex",
    "temp": "triage_temp",
    "bp_sys": "triage_ad_s",
    "bp_dia": "triage_ad_d",
    "pulse": "triage_pulse",
    "hemoglobin": "laba_Гемоглобин (HGB)",
    "creatinine": "laba_Определение креатинина",
    "urea": "laba_Определение мочевины",
    "crp": "laba_Определение белков острой фазы С-реактивный белок",
    "wbc": "laba_Количество лейкоцитов (WBC)",
    "diagnosis": "adm_ds_name",
    "complaints": "triage_complaints",
}

SURVEY_COLUMNS = {
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
    "diagnosis": "diagnosis",
    "complaints": "complaints",
}

VITALS_BOUNDS = {
    "temperature": (34.0, 42.0),
    "bp_systolic": (60.0, 250.0),
    "bp_diastolic": (30.0, 150.0),
    "pulse": (30.0, 200.0),
}


def clean_text(s):
    return s.fillna("").astype(str).str.lower().str.replace("ё", "е", regex=False)


def normalize_sex(s):
    ss = s.fillna("").astype(str).str.strip().str.lower()
    male = ss.str.fullmatch(r"1|м|муж|мужской|male", na=False)
    female = ss.str.fullmatch(r"0|2|ж|жен|женский|female", na=False)
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out[male] = 1.0
    out[female] = 0.0
    numeric = pd.to_numeric(s, errors="coerce")
    out[numeric == 1] = 1.0
    out[numeric == 0] = 0.0
    return out


def _num(df, col):
    return pd.to_numeric(df.get(col), errors="coerce")


def build_feature_frame(df, source="train", include_target=True):
    cols = TRAIN_COLUMNS if source == "train" else SURVEY_COLUMNS
    r = pd.DataFrame(index=df.index)
    if include_target and "target" in df.columns:
        r["target"] = df["target"].astype(int)

    r["age"] = _num(df, cols["age"]).clip(18, 110)
    r["is_male"] = normalize_sex(df.get(cols["sex"], pd.Series(index=df.index, dtype=object)))

    raw_temp = _num(df, cols["temp"])
    raw_bps = _num(df, cols["bp_sys"])
    raw_bpd = _num(df, cols["bp_dia"])
    raw_pulse = _num(df, cols["pulse"])
    r["temperature"] = raw_temp.where((raw_temp >= VITALS_BOUNDS["temperature"][0]) & (raw_temp <= VITALS_BOUNDS["temperature"][1]))
    r["bp_systolic"] = raw_bps.where((raw_bps >= VITALS_BOUNDS["bp_systolic"][0]) & (raw_bps <= VITALS_BOUNDS["bp_systolic"][1]))
    r["bp_diastolic"] = raw_bpd.where((raw_bpd >= VITALS_BOUNDS["bp_diastolic"][0]) & (raw_bpd <= VITALS_BOUNDS["bp_diastolic"][1]))
    r["pulse"] = raw_pulse.where((raw_pulse >= VITALS_BOUNDS["pulse"][0]) & (raw_pulse <= VITALS_BOUNDS["pulse"][1]))

    r["hemoglobin"] = _num(df, cols["hemoglobin"]).clip(30, 220)
    r["creatinine"] = _num(df, cols["creatinine"]).clip(20, 2000)
    r["urea"] = _num(df, cols["urea"]).clip(0.5, 120)
    r["crp"] = _num(df, cols["crp"]).clip(0, 600)
    r["wbc"] = _num(df, cols["wbc"]).clip(0.1, 80)

    diag = clean_text(df.get(cols["diagnosis"], pd.Series(index=df.index, dtype=object)))
    for name, pat in DIAG_FLAGS.items():
        r[name] = diag.str.contains(pat, regex=True).astype(int)

    comp = clean_text(df.get(cols["complaints"], pd.Series(index=df.index, dtype=object)))
    for name, pat in COMPLAINT_FLAGS.items():
        r[name] = comp.str.contains(pat, regex=True).astype(int)

    return engineer(r)


def engineer(df):
    df = df.copy()
    df["shock_index"] = df["pulse"] / df["bp_systolic"]
    df["pulse_pressure"] = df["bp_systolic"] - df["bp_diastolic"]
    df["map_pressure"] = df["bp_diastolic"] + df["pulse_pressure"] / 3
    df["has_fever"] = np.where(df["temperature"].notna(), (df["temperature"] > 37.5).astype(float), np.nan)
    df["has_tachycardia"] = np.where(df["pulse"].notna(), (df["pulse"] > 100).astype(float), np.nan)
    df["has_hypotension"] = np.where(df["bp_systolic"].notna(), (df["bp_systolic"] < 90).astype(float), np.nan)
    df["has_anemia"] = np.where(df["hemoglobin"].notna(), (df["hemoglobin"] < 100).astype(float), np.nan)
    df["age_elderly"] = (df["age"] >= 70).astype(int)
    df["fever_and_pain"] = ((df["has_fever"] == 1) & (df["complaint_pain"] == 1)).astype(int)
    df["missing_creatinine"] = df["creatinine"].isna().astype(int)
    df["missing_crp"] = df["crp"].isna().astype(int)
    df["missing_temperature"] = df["temperature"].isna().astype(int)
    return df
