from __future__ import annotations

import argparse
import json
from pathlib import Path

from .balance import build_balance, validate_journal_to_balance
from .config import Settings
from .journal import build_journal, classify_acdoca
from .preflight import preflight


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="S/4HANA FI 序时账处理工具（ACDOCA 驱动）")
    p.add_argument("command", choices=["preflight", "classify", "journal", "balance", "validate", "all"])
    p.add_argument("--input-dir", default="input")
    p.add_argument("--output-dir", default="output_s4hana_journal")
    p.add_argument("--companies", nargs="*", default=[])
    p.add_argument("--ledger", default="0L")
    p.add_argument("--client", required=True)
    p.add_argument("--year", required=True)
    p.add_argument("--date-from", required=True, help="YYYYMMDD")
    p.add_argument("--date-to", required=True, help="YYYYMMDD")
    p.add_argument("--period-start", type=int, help="FAGLFLEXT 起始期间；默认取 date-from 月份")
    p.add_argument("--period-end", type=int, help="FAGLFLEXT 截止期间；默认取 date-to 月份")
    p.add_argument("--label", help="输出文件标签，例如 2026H1；默认按年度和期间生成")
    p.add_argument("--file-prefix", help="取数文件名前缀，例如 FI202606；默认自动识别 TABLE_ 模式")
    p.add_argument("--languages", nargs="*", default=["ZH", "1", "EN", "E"])
    p.add_argument("--chunk-rows", type=int, default=200_000)
    p.add_argument("--rows-per-file", type=int, default=800_000)
    return p


def main() -> None:
    args = parser().parse_args()
    settings = Settings(
        input_dir=Path(args.input_dir), output_dir=Path(args.output_dir), ledger=args.ledger,
        client=args.client, year=args.year, date_from=args.date_from, date_to=args.date_to,
        period_start=args.period_start, period_end=args.period_end, label=args.label,
        file_prefix=args.file_prefix, languages=tuple(args.languages),
        chunk_rows=args.chunk_rows, rows_per_file=args.rows_per_file, companies=tuple(args.companies),
    )
    if args.command in ("preflight", "all"):
        report = preflight(settings)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] != "OK":
            raise SystemExit(2)
    if args.command == "classify":
        print(json.dumps(classify_acdoca(settings), ensure_ascii=False, indent=2, default=str))
    if args.command in ("journal", "all"):
        result = build_journal(settings)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if args.command in ("balance", "all"):
        balance, path = build_balance(settings)
        print(f"科目余额表: {path} ({len(balance):,} 行)")
    if args.command in ("validate", "all"):
        check, path = validate_journal_to_balance(settings)
        print(f"交叉核对: {path}，差异 {int(check['核对结果'].eq('差异').sum()):,} 项")
        opening_path = settings.output_path("ACDOCA余额结转与余额表期初核对")
        if opening_path.exists():
            import pandas as pd
            opening = pd.read_csv(opening_path)
            print(f"期初核对: {opening_path}，差异 {int(opening['核对结果'].eq('差异').sum()):,} 项")


if __name__ == "__main__":
    main()
