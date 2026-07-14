from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import pandas as pd

from .config import ACDOCA_FIELDS, BKPF_FIELDS, JOURNAL_COLUMNS, Settings
from .dimensions import load_dimensions
from .io import SplitCsvWriter, find_table_files, iter_delimited


JOIN_KEYS = ["MANDT", "BUKRS", "BELNR", "GJAHR"]
CLASSIFY_FIELDS = ["RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "BUZEI", "SGTXT", "RACCT", "HSL"]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def load_bkpf(settings: Settings, keys_only: bool = False) -> pd.DataFrame:
    read_fields = ["MANDT", "BUKRS", "BELNR", "GJAHR", "BUDAT"] if keys_only else list(BKPF_FIELDS)
    chunks = []
    for chunk in iter_delimited(
        find_table_files(settings.input_dir, "BKPF", settings.file_prefix),
        read_fields,
        settings.chunk_rows,
    ):
        chunk = _clean(chunk)
        mask = (
            chunk["MANDT"].eq(settings.client)
            & chunk["GJAHR"].eq(settings.year)
            & chunk["BUDAT"].between(settings.date_from, settings.date_to)
        )
        if settings.companies:
            mask &= chunk["BUKRS"].isin(settings.companies)
        chunks.append(chunk.loc[mask])
    if not chunks:
        raise ValueError("BKPF 没有符合范围的数据")
    result = pd.concat(chunks, ignore_index=True)
    if result.duplicated(JOIN_KEYS).any():
        duplicate_count = int(result.duplicated(JOIN_KEYS).sum())
        raise ValueError(f"BKPF 联接键不唯一，发现 {duplicate_count} 条重复记录")
    result["__BKPF_MATCH"] = "X"
    if keys_only:
        result = result[JOIN_KEYS + ["__BKPF_MATCH"]]
    return result


def _merge_dimensions(df: pd.DataFrame, dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    company = dims["company"].rename(columns={"MANDT": "RCLNT", "BUKRS": "RBUKRS"})
    df = df.merge(
        company[["RCLNT", "RBUKRS", "BUTXT", "KTOPL"]],
        how="left", on=["RCLNT", "RBUKRS"], validate="many_to_one",
    )
    account = dims["account"].rename(columns={"MANDT": "RCLNT", "SAKNR": "RACCT", "TXT50": "ACCOUNT_TEXT"})
    df = df.merge(account[["RCLNT", "KTOPL", "RACCT", "ACCOUNT_TEXT"]], how="left", on=["RCLNT", "KTOPL", "RACCT"], validate="many_to_one")

    joins = (
        ("doc_type", ["MANDT", "BLART"], {"LTEXT": "DOC_TYPE_TEXT"}),
        ("posting_key", ["MANDT", "BSCHL", "UMSKZ"], {"LTEXT": "POSTING_KEY_TEXT"}),
        ("user", ["MANDT", "USNAM"], {"BNAME": "USNAM", "NAME_TEXTC": "USER_TEXT"}),
        ("vendor", ["MANDT", "LIFNR"], {}),
        ("customer", ["MANDT", "KUNNR"], {}),
        ("asset", ["MANDT", "BUKRS", "ANLN1", "ANLN2"], {"TXT50": "ASSET_TEXT"}),
    )
    for name, keys, rename in joins:
        dim = dims[name].rename(columns=rename)
        if name == "vendor":
            dim["VENDOR_TEXT"] = dim[[c for c in ["NAME1", "NAME2", "NAME3", "NAME4"] if c in dim]].agg(" ".join, axis=1).str.strip()
            dim = dim.rename(columns={
                "NAME1": "VENDOR_NAME1", "NAME2": "VENDOR_NAME2",
                "NAME3": "VENDOR_NAME3", "NAME4": "VENDOR_NAME4",
            })
            dim = dim[["MANDT", "LIFNR", "VENDOR_TEXT", "VENDOR_NAME1", "VENDOR_NAME2", "VENDOR_NAME3", "VENDOR_NAME4"]]
        elif name == "customer":
            dim["CUSTOMER_TEXT"] = dim[["NAME1", "NAME2"]].agg(" ".join, axis=1).str.strip()
            dim = dim[["MANDT", "KUNNR", "CUSTOMER_TEXT"]]
        df = df.merge(dim, how="left", on=keys, validate="many_to_one")

    material = dims["material"].rename(columns={"MANDT": "RCLNT", "MAKTX": "MATERIAL_TEXT"})
    df = df.merge(material[["RCLNT", "MATNR", "MATERIAL_TEXT"]], how="left", on=["RCLNT", "MATNR"], validate="many_to_one")
    trans = dims["transaction"][["TCODE", "TTEXT"]].rename(columns={"TTEXT": "TCODE_TEXT"})
    df = df.merge(trans, how="left", on="TCODE", validate="many_to_one")
    ledger = dims["ledger"].rename(columns={"MANDT": "RCLNT", "NAME": "LEDGER_TEXT"})
    df = df.merge(ledger[["RCLNT", "RLDNR", "LEDGER_TEXT"]], how="left", on=["RCLNT", "RLDNR"], validate="many_to_one")
    return df


def _journal_view(df: pd.DataFrame, record_class: str = "正常日记账") -> pd.DataFrame:
    # LIFNR/KUNNR are intentionally copied from the current ACDOCA line only.
    # Do not propagate business partners across document lines or infer them
    # through purchase orders: this package promises direct-source fields only.
    hsl = pd.to_numeric(df["HSL"].str.replace(",", "", regex=False), errors="coerce").fillna(0.0).round(2)
    wsl = pd.to_numeric(df["WSL"].str.replace(",", "", regex=False), errors="coerce").fillna(0.0).round(2)
    debit = df["DRCRK"].eq("S")
    out = pd.DataFrame({
        "记录类别": record_class, "BKPF匹配状态": df.get("__BKPF_MATCH", ""),
        "客户端": df["RCLNT"], "分类账": df["RLDNR"], "分类账名称": df.get("LEDGER_TEXT", ""),
        "公司代码": df["RBUKRS"], "公司名称": df.get("BUTXT", ""), "会计年度": df["GJAHR"],
        "凭证编号": df["BELNR"], "行项目号": df["DOCLN"], "原始行项目号": df["BUZEI"],
        "凭证类型": df["BLART"], "凭证类型描述": df.get("DOC_TYPE_TEXT", ""), "凭证日期": df["BLDAT"],
        "过账日期": df["BUDAT"], "会计期间": df["MONAT"], "录入日期": df["CPUDT"], "录入时间": df["CPUTM"],
        "录入用户": df["USNAM"], "用户姓名": df.get("USER_TEXT", ""), "事务码": df["TCODE"],
        "事务码描述": df.get("TCODE_TEXT", ""), "参考凭证号": df["XBLNR"], "冲销凭证号": df["STBLG"],
        "凭证抬头文本": df["BKTXT"], "凭证货币": df["WAERS"], "凭证状态": df["BSTAT"],
        "业务交易": df["GLVOR"], "参考交易": df["AWTYP"], "源系统": df["AWSYS"],
        "计划冲销标识": df["XSTOV"], "冲销关系": df["XREVERSAL"], "分类账组": df["LDGRP"],
        "总账科目": df["RACCT"], "科目名称": df.get("ACCOUNT_TEXT", ""), "借贷方向": df["DRCRK"],
        "本位币金额": hsl, "交易币金额": wsl, "借方本位币": hsl.where(debit, 0.0),
        "贷方本位币": (-hsl).where(~debit, 0.0), "借方交易币": wsl.where(debit, 0.0),
        "贷方交易币": (-wsl).where(~debit, 0.0), "成本中心": df["RCNTR"], "利润中心": df["PRCTR"],
        "功能范围": df["RFAREA"], "贸易伙伴": df["RASSC"], "分配号": df["ZUONR"], "过账码": df["BSCHL"],
        "过账码描述": df.get("POSTING_KEY_TEXT", ""), "行项目文本": df["SGTXT"], "采购订单": df["EBELN"],
        "采购订单行": df["EBELP"], "销售订单": df["KDAUF"], "销售订单行": df["KDPOS"],
        "物料编号": df["MATNR"], "物料名称": df.get("MATERIAL_TEXT", ""), "供应商编号": df["LIFNR"],
        "供应商名称": df.get("VENDOR_TEXT", ""), "供应商名称1": df.get("VENDOR_NAME1", ""),
        "供应商名称2": df.get("VENDOR_NAME2", ""), "供应商名称3": df.get("VENDOR_NAME3", ""),
        "供应商名称4": df.get("VENDOR_NAME4", ""), "客户编号": df["KUNNR"], "客户名称": df.get("CUSTOMER_TEXT", ""),
        "科目类型": df["KOART"], "特别总账标识": df["UMSKZ"], "清账日期": df["AUGDT"],
        "清账凭证": df["AUGBL"], "资产主号": df["ANLN1"], "资产次号": df["ANLN2"],
        "资产名称": df.get("ASSET_TEXT", ""), "反向凭证标识": df["XREVERSING"],
    })
    return out.reindex(columns=JOURNAL_COLUMNS, fill_value="")


def _raw_amount_summary(df: pd.DataFrame, record_class: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["记录类别", "公司代码", "总账科目", "记录数", "本位币金额"])
    work = df[["RBUKRS", "RACCT", "HSL"]].copy()
    work["HSL"] = pd.to_numeric(work["HSL"].str.replace(",", "", regex=False), errors="coerce").fillna(0.0)
    work["记录数"] = 1
    result = work.groupby(["RBUKRS", "RACCT"], as_index=False).agg(记录数=("记录数", "sum"), 本位币金额=("HSL", "sum"))
    result = result.rename(columns={"RBUKRS": "公司代码", "RACCT": "总账科目"})
    result.insert(0, "记录类别", record_class)
    result["本位币金额"] = result["本位币金额"].round(2)
    return result


def classify_acdoca(settings: Settings) -> dict[str, object]:
    """Scan all ACDOCA rows without producing line-level journal files."""
    settings.prepare()
    bkpf = load_bkpf(settings, keys_only=True)
    parts: dict[str, list[pd.DataFrame]] = {"正常日记账": [], "余额结转BCF": [], "余额结转补充项": [], "无BKPF待核查": []}
    counts: defaultdict[str, int] = defaultdict(int)
    for chunk in iter_delimited(
        find_table_files(settings.input_dir, "ACDOCA", settings.file_prefix),
        CLASSIFY_FIELDS,
        settings.chunk_rows,
    ):
        chunk = _clean(chunk)
        mask = chunk["RCLNT"].eq(settings.client) & chunk["GJAHR"].eq(settings.year) & chunk["RLDNR"].eq(settings.ledger)
        if settings.companies:
            mask &= chunk["RBUKRS"].isin(settings.companies)
        chunk = chunk.loc[mask]
        if chunk.empty:
            continue
        merged = chunk.merge(
            bkpf[JOIN_KEYS + ["__BKPF_MATCH"]], how="left",
            left_on=["RCLNT", "RBUKRS", "BELNR", "GJAHR"], right_on=JOIN_KEYS,
            validate="many_to_one",
        ).fillna("")
        is_bcf = merged["SGTXT"].str.startswith("BCF:", na=False)
        has_header = merged["__BKPF_MATCH"].eq("X")
        is_bcf_supplement = (~is_bcf & ~has_header & merged["BELNR"].str.match(r"^B\d+$", na=False) & merged["BUZEI"].eq("000"))
        groups = {
            "余额结转BCF": merged.loc[is_bcf],
            "余额结转补充项": merged.loc[is_bcf_supplement],
            "正常日记账": merged.loc[~is_bcf & ~is_bcf_supplement & has_header],
            "无BKPF待核查": merged.loc[~is_bcf & ~is_bcf_supplement & ~has_header],
        }
        for name, group in groups.items():
            counts[name] += len(group)
            if not group.empty:
                parts[name].append(_raw_amount_summary(group, name))
    summaries = []
    for name, frames in parts.items():
        if not frames:
            continue
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.groupby(["记录类别", "公司代码", "总账科目"], as_index=False).agg(记录数=("记录数", "sum"), 本位币金额=("本位币金额", "sum"))
        combined["本位币金额"] = combined["本位币金额"].round(2)
        summaries.append(combined)
    summary = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    summary_path = settings.output_path("ACDOCA分类汇总")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    report = {
        "counts": dict(counts), "total": int(sum(counts.values())), "summary": str(summary_path),
        "classification_basis": {
            "余额结转BCF": "SGTXT 以 BCF: 开头（当前取数未包含 POPER）",
            "余额结转补充项": "无 BKPF、BELNR 为 B+数字且 BUZEI=000；通过与 FAGLFLEXT HSLVT 全量零差异验证",
            "正常日记账": "非 BCF 且按客户端/公司/凭证号/年度匹配 BKPF",
            "无BKPF待核查": "不满足上述规则且不能匹配 BKPF，不计入期间发生额",
        },
    }
    report_path = settings.output_path("ACDOCA分类报告", ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report"] = str(report_path)
    return report


def build_journal(settings: Settings) -> dict[str, object]:
    settings.prepare()
    bkpf = load_bkpf(settings)
    dims = load_dimensions(settings)
    writers: dict[str, SplitCsvWriter] = {}
    summary_parts: list[pd.DataFrame] = []
    bcf_parts: list[pd.DataFrame] = []
    unmatched_parts: list[pd.DataFrame] = []
    counts: defaultdict[str, int] = defaultdict(int)
    acdoca_files = find_table_files(settings.input_dir, "ACDOCA", settings.file_prefix)
    if not acdoca_files:
        raise FileNotFoundError("未找到 ACDOCA 分片")

    for chunk in iter_delimited(acdoca_files, ACDOCA_FIELDS, settings.chunk_rows):
        chunk = _clean(chunk)
        mask = chunk["RCLNT"].eq(settings.client) & chunk["GJAHR"].eq(settings.year) & chunk["RLDNR"].eq(settings.ledger)
        if settings.companies:
            mask &= chunk["RBUKRS"].isin(settings.companies)
        chunk = chunk.loc[mask]
        if chunk.empty:
            continue
        # ACDOCA also contains CO/allocation documents (for example B* document
        # numbers) which legitimately have no BKPF row. ACDOCA is the driving
        # table, so a left join is required to avoid silently dropping them.
        merged = chunk.merge(
            bkpf, how="left",
            left_on=["RCLNT", "RBUKRS", "BELNR", "GJAHR"],
            right_on=JOIN_KEYS, suffixes=("", "_BKPF"), validate="many_to_one",
        )
        merged = merged.fillna("")
        # Dimension tables use classic FI key names. Populate them from ACDOCA
        # even when no BKPF header exists.
        merged["MANDT"] = merged["RCLNT"]
        merged["BUKRS"] = merged["RBUKRS"]
        is_bcf = merged["SGTXT"].str.startswith("BCF:", na=False)
        has_header = merged["__BKPF_MATCH"].eq("X")
        is_bcf_supplement = (~is_bcf & ~has_header & merged["BELNR"].str.match(r"^B\d+$", na=False) & merged["BUZEI"].eq("000"))
        bcf = merged.loc[is_bcf]
        bcf_supplement = merged.loc[is_bcf_supplement]
        unmatched = merged.loc[~is_bcf & ~is_bcf_supplement & ~has_header]
        operational = merged.loc[~is_bcf & ~is_bcf_supplement & has_header]
        counts["余额结转BCF"] += len(bcf)
        counts["余额结转补充项"] += len(bcf_supplement)
        counts["无BKPF待核查"] += len(unmatched)
        if not bcf.empty:
            bcf_parts.append(_raw_amount_summary(bcf, "余额结转BCF"))
        if not bcf_supplement.empty:
            bcf_parts.append(_raw_amount_summary(bcf_supplement, "余额结转补充项"))
        if not unmatched.empty:
            unmatched_parts.append(_raw_amount_summary(unmatched, "无BKPF待核查"))
        if operational.empty:
            continue
        counts["正常日记账"] += len(operational)
        operational = _merge_dimensions(operational, dims)
        journal = _journal_view(operational, "正常日记账")
        summary_parts.append(journal.groupby(["公司代码", "总账科目"], as_index=False)[["借方本位币", "贷方本位币", "本位币金额"]].sum())
        for company, part in journal.groupby("公司代码", sort=False):
            if company not in writers:
                company_dir = settings.output_dir / "序时账"
                company_dir.mkdir(parents=True, exist_ok=True)
                writers[company] = SplitCsvWriter(
                    company_dir,
                    f"序时账_{company}_{settings.run_label}",
                    settings.rows_per_file,
                    JOURNAL_COLUMNS,
                )
            writers[company].write(part)
            counts[f"公司_{company}"] += len(part)
    for writer in writers.values():
        writer.close()

    if summary_parts:
        summary = pd.concat(summary_parts).groupby(["公司代码", "总账科目"], as_index=False).sum()
        amount_cols = ["借方本位币", "贷方本位币", "本位币金额"]
        summary[amount_cols] = summary[amount_cols].round(2)
        summary["净发生额"] = (summary["借方本位币"] - summary["贷方本位币"]).round(2)
    else:
        summary = pd.DataFrame(columns=["公司代码", "总账科目", "借方本位币", "贷方本位币", "本位币金额", "净发生额"])
    summary_path = settings.output_path("序时账期间汇总")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    def combine_raw(parts: list[pd.DataFrame], filename: str) -> Path:
        if parts:
            data = pd.concat(parts, ignore_index=True).groupby(["记录类别", "公司代码", "总账科目"], as_index=False).agg(记录数=("记录数", "sum"), 本位币金额=("本位币金额", "sum"))
            data["本位币金额"] = data["本位币金额"].round(2)
        else:
            data = pd.DataFrame(columns=["记录类别", "公司代码", "总账科目", "记录数", "本位币金额"])
        path = settings.output_dir / filename
        data.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    bcf_path = combine_raw(bcf_parts, f"余额结转BCF汇总_{settings.run_label}.csv")
    unmatched_path = combine_raw(unmatched_parts, f"无BKPF待核查汇总_{settings.run_label}.csv")
    return {
        "counts": dict(counts), "summary": summary_path, "balance_carryforward": bcf_path,
        "unmatched": unmatched_path, "files": {c: [str(p) for p in w.paths] for c, w in writers.items()},
    }
