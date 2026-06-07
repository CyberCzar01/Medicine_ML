import re

import pandas as pd

from urotriage.config import ESCALATION_OPER_RE
from urotriage.features import clean_text

_oper_re = re.compile(ESCALATION_OPER_RE)
_death_re = re.compile(r"умер")


def build_escalation_target(df):
    oper = clean_text(df.get("oper_name", pd.Series(index=df.index, dtype=object)))
    outcome = clean_text(df.get("hosp_outcome", pd.Series(index=df.index, dtype=object)))
    drainage = oper.str.contains(_oper_re, regex=True)
    death = outcome.str.contains(_death_re, regex=True)
    target = (drainage | death).astype(int)
    components = {
        "drainage_cystostomy": int(drainage.sum()),
        "in_hospital_death": int(death.sum()),
        "positive_total": int(target.sum()),
        "n": int(len(df)),
    }
    return target, components
