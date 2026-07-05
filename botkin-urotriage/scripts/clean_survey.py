import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from urotriage.config import SURVEY_XLSX, SURVEY_CLEAN_CSV, RESULTS_DIR

RENAME = {
    "номер": "case_id", "Пол": "sex", "Возраст": "age", "диагноз": "diagnosis",
    "Жалобы": "complaints", "Время от начала заболевания": "time_since_onset_txt",
    "Лейкоциты крови": "wbc", "Гемоглобин": "hgb", "Креатинин": "creatinine",
    "Мочевина": "urea", "СРБ": "crp", "Объем простаты": "prostate_vol",
    "Операция": "operation_txt",
    "Время от поступления до оперативного лечения, ч": "hours_to_oper",
    "Индекс Чарльсона": "charlson", "ИМТ": "bmi", "Прокальцитонин": "pct",
    "Температура": "temp", "пульс": "pulse", "АД": "bp",
    "Исход": "outcome", "Повторное обращение": "readmission_txt",
    "Наличие осложнений": "complications_txt", "наличие средней доли": "median_lobe",
    "размер средней доли": "median_lobe_size", "Уровень ПСА": "psa",
    "длительность заболевания": "disease_duration",
    "наличие остаточной мочи ранее": "prior_residual",
    "объем выпущенной мочи": "drained_volume_ml",
    "наличие камней мочевого пузыря": "bladder_stones",
    "кратность предшествующей катетеризации мочевого пузыря": "prior_cath_count",
    "прием альфа-блокаторов": "alpha_blockers",
    "Прием блокаторов 5-альфа-редуктазы": "reductase_inhibitors",
    "Наличие операций на простате в анамнезе": "prior_prostate_surgery",
    "Наличие ретенции верхних мочевых путей": "upper_tract_retention",
    "Прогноз: восстановится мочеиспускание или нет: ДА или НЕТ": "prognosis_void",
    "метод дренирования": "drainage_method",
}


def to_num(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(",", ".")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan


def yesno(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s.startswith("да") or s.startswith("есть") or s == "высокий":
        return 1
    if s.startswith("нет") or s.startswith("норма") or s == "низкий":
        return 0
    return np.nan


def split_bp(x):
    if pd.isna(x):
        return (np.nan, np.nan)
    m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", str(x))
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def had_op(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s in ("нет", "не проводилась", "отказано") or s.startswith("не пров"):
        return 0
    if any(k in s for k in ["тур", "цистост", "уретротом", "литоэкстр", "бужир", "аденом", "эпицистост", "дренир"]):
        return 1
    return np.nan


def clean():
    raw = pd.read_excel(SURVEY_XLSX, header=0).rename(columns=RENAME)
    ages = raw["age"].apply(to_num)
    df = raw[(ages >= 18) & (ages <= 110)].copy().reset_index(drop=True)

    num_cols = ["age", "wbc", "hgb", "creatinine", "urea", "crp", "prostate_vol",
                "hours_to_oper", "charlson", "bmi", "pct", "temp", "pulse", "psa",
                "drained_volume_ml", "prior_cath_count", "median_lobe_size"]
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].apply(to_num)

    if "case_id" in df.columns:
        has_id = df["case_id"].notna() & (df["case_id"].astype(str).str.strip() != "")
        with_id = df[has_id].drop_duplicates(subset=["case_id"], keep="first")
        without_id = df[~has_id]
        df = pd.concat([with_id, without_id], axis=0).sort_index().reset_index(drop=True)

    yn_cols = ["readmission_txt", "complications_txt", "median_lobe", "prior_residual",
               "bladder_stones", "alpha_blockers", "reductase_inhibitors",
               "prior_prostate_surgery", "upper_tract_retention"]
    for c in yn_cols:
        if c in df.columns:
            df[c + "_bin"] = df[c].apply(yesno)

    if "bp" in df.columns:
        df["bp_sys"], df["bp_dia"] = zip(*df["bp"].apply(split_bp))

    if "operation_txt" in df.columns:
        df["had_operation"] = df["operation_txt"].apply(had_op)

    n = len(df)
    quality = {"n_patients": int(n), "fields": {}}
    for c in df.columns:
        nn = int(df[c].notna().sum())
        quality["fields"][c] = {"filled": nn, "pct": round(nn / n * 100, 1) if n else 0.0}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(SURVEY_CLEAN_CSV, index=False, encoding="utf-8-sig")
    with open(RESULTS_DIR / "survey_quality.json", "w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)
    return df, quality


def main():
    df, quality = clean()
    print(f"Пациентов в анкете: {quality['n_patients']}")
    print(f"survey_clean.csv -> {SURVEY_CLEAN_CSV}")
    if "had_operation" in df.columns:
        print("had_operation:")
        print(df["had_operation"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
