from __future__ import annotations

import pandas as pd

from .config import Settings
from .dimensions import load_dimensions
from .io import read_table


HSL = ["HSLVT"] + [f"HSL{i:02d}" for i in range(1, 17)]


def build_balance(settings: Settings) -> tuple[pd.DataFrame, object]:
    settings.prepare()
    fields = ["RCLNT", "RYEAR", "DRCRK", "RTCUR", "RLDNR", "RRCTY", "RVERS", "RACCT", "RBUKRS", *HSL]
    df = read_table(settings.input_dir, "FAGLFLEXT", fields, settings.file_prefix)
    for c in ["RCLNT", "RYEAR", "RLDNR", "RRCTY", "RVERS", "RACCT", "RBUKRS", "DRCRK"]:
        df[c] = df[c].astype(str).str.strip()
    mask = df["RCLNT"].eq(settings.client) & df["RYEAR"].eq(settings.year) & df["RLDNR"].eq(settings.ledger)
    mask &= df["RRCTY"].eq("0") & df["RVERS"].eq("001")
    if settings.companies:
        mask &= df["RBUKRS"].isin(settings.companies)
    df = df.loc[mask].copy()
    for c in HSL:
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce").fillna(0.0)
    df["年度期初余额"] = df["HSLVT"]
    prior_cols = [f"HSL{i:02d}" for i in range(1, settings.first_period)]
    df["期初余额"] = df["HSLVT"] + (df[prior_cols].sum(axis=1) if prior_cols else 0.0)
    movement_cols = [f"HSL{i:02d}" for i in range(settings.first_period, settings.last_period + 1)]
    df["期间净发生额"] = df[movement_cols].sum(axis=1)
    df["借方发生额"] = df["期间净发生额"].where(df["DRCRK"].eq("S"), 0.0)
    df["贷方发生额"] = (-df["期间净发生额"]).where(df["DRCRK"].eq("H"), 0.0)
    # HSL is local-currency amount. RTCUR is a source-record currency dimension
    # and may have several values for the same company/account, so it must not
    # split the local-currency trial balance.
    result = df.groupby(["RCLNT", "RBUKRS", "RACCT"], as_index=False)[["年度期初余额", "期初余额", "借方发生额", "贷方发生额", "期间净发生额"]].sum()
    result["期末余额"] = result["期初余额"] + result["期间净发生额"]
    amount_cols = ["年度期初余额", "期初余额", "借方发生额", "贷方发生额", "期间净发生额", "期末余额"]
    result[amount_cols] = result[amount_cols].round(2)

    dims = load_dimensions(settings)
    company = dims["company"].rename(columns={"MANDT": "RCLNT", "BUKRS": "RBUKRS"})
    result = result.merge(company[["RCLNT", "RBUKRS", "BUTXT", "WAERS", "KTOPL"]], how="left", on=["RCLNT", "RBUKRS"], validate="many_to_one")
    account = dims["account"].rename(columns={"MANDT": "RCLNT", "SAKNR": "RACCT"})
    result = result.merge(account[["RCLNT", "KTOPL", "RACCT", "TXT50"]], how="left", on=["RCLNT", "KTOPL", "RACCT"], validate="many_to_one")
    result = result.rename(columns={"RBUKRS": "公司代码", "BUTXT": "公司名称", "RACCT": "总账科目", "TXT50": "科目名称", "WAERS": "本位币"})
    cols = ["公司代码", "公司名称", "总账科目", "科目名称", "本位币", "年度期初余额", "期初余额", "借方发生额", "贷方发生额", "期间净发生额", "期末余额"]
    result = result[cols].sort_values(["公司代码", "总账科目"])
    path = settings.output_path("科目余额表")
    result.to_csv(path, index=False, encoding="utf-8-sig")
    return result, path


def validate_journal_to_balance(settings: Settings) -> tuple[pd.DataFrame, object]:
    journal_path = settings.output_path("序时账期间汇总")
    if not journal_path.exists():
        raise FileNotFoundError("请先运行 journal 或 all 生成序时账期间汇总")
    journal = pd.read_csv(journal_path, dtype={"公司代码": str, "总账科目": str})
    balance, _ = build_balance(settings)
    check = journal.merge(
        balance[["公司代码", "总账科目", "期间净发生额"]],
        how="outer", on=["公司代码", "总账科目"], suffixes=("_序时账", "_余额表"), indicator=True,
    )
    numeric = ["借方本位币", "贷方本位币", "本位币金额", "净发生额", "期间净发生额"]
    for col in numeric:
        if col in check:
            check[col] = pd.to_numeric(check[col], errors="coerce").fillna(0.0)
    check["差异"] = (check["净发生额"] - check["期间净发生额"]).round(2)
    check["核对结果"] = check["差异"].abs().le(0.01).map({True: "一致", False: "差异"})
    path = settings.output_path("序时账与余额表核对")
    check.to_csv(path, index=False, encoding="utf-8-sig")

    bcf_path = settings.output_path("余额结转BCF汇总")
    if bcf_path.exists():
        bcf = pd.read_csv(bcf_path, dtype={"公司代码": str, "总账科目": str})
        opening = bcf.groupby(["公司代码", "总账科目"], as_index=False).agg(BCF记录数=("记录数", "sum"), ACDOCA余额结转=("本位币金额", "sum"))
        opening = opening.merge(
            balance[["公司代码", "总账科目", "年度期初余额"]], how="outer",
            on=["公司代码", "总账科目"], indicator=True,
        )
        for col in ["BCF记录数", "ACDOCA余额结转", "年度期初余额"]:
            opening[col] = pd.to_numeric(opening[col], errors="coerce").fillna(0.0)
        opening["差异"] = (opening["ACDOCA余额结转"] - opening["年度期初余额"]).round(2)
        opening["核对结果"] = opening["差异"].abs().le(0.01).map({True: "一致", False: "差异"})
        opening.to_csv(settings.output_path("ACDOCA余额结转与余额表期初核对"), index=False, encoding="utf-8-sig")
    return check, path
