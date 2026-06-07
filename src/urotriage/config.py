import os
from pathlib import Path

RULE_VERSION = "rule-v4.0-provisional"
MODEL_VERSION = "ml-v4.0-escalation-proxy"
THRESHOLD_VERSION = "thr-v4.0"
SCHEMA_VERSION = "schema-v4.0"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("UROTRIAGE_DATA_DIR", PROJECT_ROOT / "data"))
MODELS_DIR = Path(os.environ.get("UROTRIAGE_MODELS_DIR", PROJECT_ROOT / "models"))
RESULTS_DIR = Path(os.environ.get("UROTRIAGE_RESULTS_DIR", PROJECT_ROOT / "results"))

_DEFAULT_RAW = PROJECT_ROOT.parent / "28-12-2025" / "На_УРОЛОГА (4).xlsx"
RAW_XLSX = Path(os.environ.get("UROTRIAGE_RAW_XLSX", _DEFAULT_RAW))
CACHE_PKL = DATA_DIR / "_cache_urolog.pkl"

_DEFAULT_SURVEY = PROJECT_ROOT.parent / "Анкета на опрос проба 13.05.2026.xlsx"
SURVEY_XLSX = Path(os.environ.get("UROTRIAGE_SURVEY_XLSX", _DEFAULT_SURVEY))
SURVEY_CLEAN_CSV = RESULTS_DIR / "survey_clean.csv"

MODEL_PATH = MODELS_DIR / "model_v4.joblib"

RANDOM_STATE = 42

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("UROTRIAGE_CORS_ORIGINS", "*").split(",")
    if o.strip()
]

COHORT_RETENTION_RE = r"\bозм\b|остр\w*\s+задерж\w*\s+моч|задерж\w*\s+моч|ишур|r\s*33|r33|n\s*13|n13"
COHORT_HYPERPLASIA_RE = r"гиперплазия предстательной|дгпж|аденом\w*\s+прост"

DIAG_FLAGS = {
    "diag_retention": r"\bозм\b|остр\w*\s+задерж\w*\s+моч|задерж\w*\s+моч|ишур|r\s*33|r33|n\s*13|n13",
    "diag_hematuria": r"гематури",
    "diag_colic": r"колик|почечная колика",
    "diag_catheter": r"катетер|цистостом",
    "diag_infection": r"нефрит|простатит|цистит|орхит|эпидидимит",
    "diag_stones": r"камн|уролитиаз|мочекаменн",
    "diag_hyperplasia": r"гиперплазия предстательной|дгпж|аденом\w*\s+прост",
    "diag_hydronephrosis": r"гидронефроз|уретерогидронефроз",
    "diag_tumor": r"новообразован|опухол|рак|злокачеств",
}

COMPLAINT_FLAGS = {
    "complaint_pain": r"бол[ьи]|болезнен",
    "complaint_fever": r"температур|лихорад|озноб",
    "complaint_retention": r"\bозм\b|не мочи|задержк|не может помочи|невозможн\w*\s+самостоятельн\w*\s+мочеисп|ишур",
    "complaint_blood": r"кров[ьи]|гематур|примес",
    "complaint_weakness": r"слабост|головокруж",
}

RULE_THRESHOLDS = {
    "creatinine_red": 130.0,
    "urea_red": 20.0,
    "temp_red": 38.0,
    "temp_yellow_low": 37.5,
    "temp_yellow_high": 37.9,
    "crp_red": 50.0,
    "wbc_red": 12.0,
    "hemoglobin_anemia": 90.0,
    "residual_urine_yellow": 500.0,
    "residual_urine_strong": 800.0,
}

RULE_PATTERNS = {
    "hydronephrosis_red": r"гидронефроз|уретерогидронефроз|обструкц\w*\s+верхн",
    "hydronephrosis_yellow": r"пиелоэктаз|расширен\w*\s+чашечно|расширен\w*\s+члс|каликоэктаз",
    "infection_dx": r"уросепсис|пиелонефрит|сепсис",
    "hematuria_severe": r"сгустк|тампонад|клиническ\w*\s+значим\w*\s+кровотеч|профузн\w*\s+кровотеч",
    "hematuria_any": r"макрогематури|гематури",
    "failed_catheter": r"(?:невозможн|неэффективн|не удалос|не уда[её]тся|безуспешн)\w*.{0,40}катетер|катетер.{0,40}(?:неэффективн|невозможн|не установл|безуспешн)",
    "severe_pain": r"выражен\w*\s+бол|сильн\w*\s+бол|интенсивн\w*\s+бол",
}

ESCALATION_OPER_RE = r"цистостом|эпицистост"

ML_FEATURES = [
    "age",
    "is_male",
    "temperature",
    "bp_systolic",
    "bp_diastolic",
    "pulse",
    "hemoglobin",
    "creatinine",
    "urea",
    "crp",
    "wbc",
    "shock_index",
    "pulse_pressure",
    "map_pressure",
    "has_fever",
    "has_tachycardia",
    "has_hypotension",
    "has_anemia",
    "age_elderly",
    "fever_and_pain",
    "diag_retention",
    "diag_hematuria",
    "diag_colic",
    "diag_catheter",
    "diag_infection",
    "diag_stones",
    "diag_hyperplasia",
    "diag_hydronephrosis",
    "diag_tumor",
    "complaint_pain",
    "complaint_fever",
    "complaint_retention",
    "complaint_blood",
    "complaint_weakness",
    "missing_creatinine",
    "missing_crp",
    "missing_temperature",
]

ML_THRESHOLD_POLICY = {
    "probability_source": "calibrated",
    "green_upgrade_min_sensitivity": 0.85,
    "green_upgrade_max_share": 0.30,
}

DISCLAIMERS = [
    "Инструмент поддержки решения для врача-уролога, не заменяет клиническое суждение.",
    "Светофор определяется прозрачным клиническим правилом; ML только подсвечивает скрытый риск и не повышает зону до красной.",
    "Пороги правила предварительные (provisional) и требуют подтверждения врачом.",
    "ML-метка escalation_proxy отражает риск эскалации (дренирование/летальный исход), а не истинную клиническую тяжесть.",
    "Признаки в ml.top_features — глобальные факторы модели, а не индивидуальное объяснение конкретного пациента.",
]
