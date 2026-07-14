from __future__ import annotations

import json
from pathlib import Path

from .config import ACDOCA_FIELDS, BKPF_FIELDS, Settings
from .io import find_table_files, read_header


REQUIRED = {
    "ACDOCA": set(ACDOCA_FIELDS),
    "BKPF": set(BKPF_FIELDS),
    "T001": {"MANDT", "BUKRS", "BUTXT", "KTOPL"},
    "SKAT": {"MANDT", "SPRAS", "KTOPL", "SAKNR", "TXT50"},
}


def preflight(settings: Settings) -> dict[str, object]:
    settings.prepare()
    required_tables = dict(REQUIRED)
    required_tables["FAGLFLEXT"] = {
        "RCLNT", "RYEAR", "DRCRK", "RTCUR", "RLDNR", "RRCTY", "RVERS",
        "RACCT", "RBUKRS", "HSLVT", *{f"HSL{i:02d}" for i in range(1, settings.last_period + 1)},
    }
    tables: dict[str, object] = {}
    ok = True
    for table, required in required_tables.items():
        files = find_table_files(settings.input_dir, table, settings.file_prefix)
        missing = sorted(required - set(read_header(files[0]))) if files else sorted(required)
        size = sum(p.stat().st_size for p in files)
        tables[table] = {
            "files": len(files),
            "size_gb": round(size / 1024**3, 3),
            "missing_fields": missing,
            "status": "OK" if files and not missing else "ERROR",
        }
        ok &= bool(files) and not missing
    report = {
        "status": "OK" if ok else "ERROR",
        "scope": {
            "client": settings.client, "year": settings.year,
            "date_from": settings.date_from, "date_to": settings.date_to,
            "period_start": settings.first_period, "period_end": settings.last_period,
            "ledger": settings.ledger, "label": settings.run_label,
        },
        "tables": tables,
    }
    path = settings.output_path("运行前检查", ".json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report"] = str(path)
    return report
