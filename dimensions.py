from __future__ import annotations

import pandas as pd

from .config import Settings
from .io import choose_language, read_table


def _dim(settings: Settings, table: str, cols: list[str], keys: list[str], lang: str | None = None) -> pd.DataFrame:
    df = read_table(settings.input_dir, table, cols)
    if df.empty:
        return df
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    if lang:
        df = choose_language(df, keys, lang, settings.languages)
    return df.drop_duplicates(keys)


def load_dimensions(settings: Settings) -> dict[str, pd.DataFrame]:
    return {
        "company": _dim(settings, "T001", ["MANDT", "BUKRS", "BUTXT", "WAERS", "KTOPL", "PERIV"], ["MANDT", "BUKRS"]),
        "account": _dim(settings, "SKAT", ["MANDT", "SPRAS", "KTOPL", "SAKNR", "TXT50"], ["MANDT", "KTOPL", "SAKNR"], "SPRAS"),
        "doc_type": _dim(settings, "T003T", ["MANDT", "SPRAS", "BLART", "LTEXT"], ["MANDT", "BLART"], "SPRAS"),
        "posting_key": _dim(settings, "TBSLT", ["MANDT", "SPRAS", "BSCHL", "UMSKZ", "LTEXT"], ["MANDT", "BSCHL", "UMSKZ"], "SPRAS"),
        "user": _dim(settings, "USER_ADDR", ["MANDT", "BNAME", "NAME_TEXTC"], ["MANDT", "BNAME"]),
        "transaction": _dim(settings, "TSTCT", ["SPRSL", "TCODE", "TTEXT"], ["TCODE"], "SPRSL"),
        "vendor": _dim(settings, "LFA1", ["MANDT", "LIFNR", "NAME1", "NAME2", "NAME3", "NAME4"], ["MANDT", "LIFNR"]),
        "customer": _dim(settings, "KNA1", ["MANDT", "KUNNR", "NAME1", "NAME2"], ["MANDT", "KUNNR"]),
        "material": _dim(settings, "MAKT", ["MANDT", "MATNR", "SPRAS", "MAKTX"], ["MANDT", "MATNR"], "SPRAS"),
        "asset": _dim(settings, "ANLA", ["MANDT", "BUKRS", "ANLN1", "ANLN2", "SPRAS", "TXT50"], ["MANDT", "BUKRS", "ANLN1", "ANLN2"], "SPRAS"),
        "ledger": _dim(settings, "T881T", ["MANDT", "LANGU", "RLDNR", "NAME"], ["MANDT", "RLDNR"], "LANGU"),
    }
