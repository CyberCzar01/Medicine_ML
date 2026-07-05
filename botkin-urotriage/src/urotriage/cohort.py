import re

import pandas as pd

from urotriage.config import COHORT_RETENTION_RE, COHORT_HYPERPLASIA_RE
from urotriage.features import clean_text

_COHORT_RE = re.compile(f"{COHORT_RETENTION_RE}|{COHORT_HYPERPLASIA_RE}")


def cohort_mask(df):
    adm = clean_text(df.get("adm_ds_name", pd.Series(index=df.index, dtype=object)))
    fin = clean_text(df.get("final_ds_name", pd.Series(index=df.index, dtype=object)))
    text = (adm + " " + fin)
    return text.str.contains(_COHORT_RE, regex=True)


def filter_cohort(df):
    mask = cohort_mask(df)
    return df.loc[mask].reset_index(drop=True), int(mask.sum())
