import pandas as pd

from urotriage.config import RAW_XLSX, CACHE_PKL, DATA_DIR


def _cache_fresh():
    if not CACHE_PKL.exists():
        return False
    if not RAW_XLSX.exists():
        return True
    return CACHE_PKL.stat().st_mtime >= RAW_XLSX.stat().st_mtime


def load_raw(use_cache=True):
    if use_cache and _cache_fresh():
        return pd.read_pickle(CACHE_PKL)
    if not RAW_XLSX.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_XLSX}. Set UROTRIAGE_RAW_XLSX to its path."
        )
    df = pd.read_excel(RAW_XLSX, engine="openpyxl")
    if use_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_pickle(CACHE_PKL)
    return df
