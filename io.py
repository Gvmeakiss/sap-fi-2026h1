from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import pandas as pd

from .config import SEP


def normalize(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    value = str(value).strip()
    return value[:-2] if value.endswith(".0") else value


def find_table_files(input_dir: Path, table: str, file_prefix: str | None = None) -> list[Path]:
    """Find extracted TXT parts and ignore KPMG log files and ZIP duplicates."""
    token = table.upper()
    prefix = (file_prefix or "").upper()
    files = []
    for p in input_dir.rglob("*"):
        name = p.name.upper()
        if not p.is_file() or p.suffix.upper() != ".TXT" or "KPMG_LOG" in name:
            continue
        if f"{token}_" not in name:
            continue
        if prefix and not (name.startswith(f"{prefix}{token}_") or name.startswith(f"{prefix}_{token}_")):
            continue
        files.append(p)
    return sorted(files)


def first_table_file(input_dir: Path, table: str, file_prefix: str | None = None) -> Path:
    files = find_table_files(input_dir, table, file_prefix)
    if not files:
        raise FileNotFoundError(f"未找到 {table} TXT 文件: {input_dir}")
    return files[0]


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return [c.strip().upper() for c in f.readline().rstrip("\r\n").split(SEP)]


def iter_delimited(
    paths: Sequence[Path],
    usecols: Iterable[str] | None = None,
    chunk_rows: int = 200_000,
) -> Iterator[pd.DataFrame]:
    """Fast, low-memory reader for KPMG's multi-character #|# separator."""
    wanted = tuple(c.upper() for c in usecols) if usecols else None
    for path in paths:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            header = [c.strip().upper() for c in f.readline().rstrip("\r\n").split(SEP)]
            if wanted:
                missing = [c for c in wanted if c not in header]
                if missing:
                    raise ValueError(f"{path.name} 缺少字段: {', '.join(missing)}")
                indexes = [header.index(c) for c in wanted]
                columns = list(wanted)
            else:
                indexes = list(range(len(header)))
                columns = header
            batch: list[list[str]] = []
            for line_no, line in enumerate(f, 2):
                values = line.rstrip("\r\n").split(SEP)
                if len(values) != len(header):
                    raise ValueError(
                        f"{path.name}:{line_no} 字段数 {len(values)} != 表头 {len(header)}"
                    )
                batch.append([values[i] for i in indexes])
                if len(batch) >= chunk_rows:
                    yield pd.DataFrame.from_records(batch, columns=columns)
                    batch = []
            if batch:
                yield pd.DataFrame.from_records(batch, columns=columns)


def read_table(
    input_dir: Path,
    table: str,
    usecols: Iterable[str] | None = None,
    file_prefix: str | None = None,
) -> pd.DataFrame:
    files = find_table_files(input_dir, table, file_prefix)
    if not files:
        return pd.DataFrame(columns=list(usecols or ()))
    return pd.concat(iter_delimited(files, usecols, 200_000), ignore_index=True)


def choose_language(df: pd.DataFrame, keys: list[str], lang_col: str, languages: tuple[str, ...]) -> pd.DataFrame:
    if df.empty or lang_col not in df:
        return df
    rank = {lang: i for i, lang in enumerate(languages)}
    selected = df[df[lang_col].isin(rank)].copy()
    if selected.empty:
        selected = df.copy()
        selected["__rank"] = len(rank)
    else:
        selected["__rank"] = selected[lang_col].map(rank)
    return selected.sort_values("__rank").drop_duplicates(keys).drop(columns="__rank")


class SplitCsvWriter:
    def __init__(self, output_dir: Path, prefix: str, rows_per_file: int, columns: Sequence[str]):
        self.output_dir = output_dir
        self.prefix = prefix
        self.rows_per_file = rows_per_file
        self.columns = list(columns)
        self.part = 0
        self.rows = 0
        self.handle = None
        self.writer = None
        self.paths: list[Path] = []

    def _open(self) -> None:
        self.close_current()
        self.part += 1
        path = self.output_dir / f"{self.prefix}_{self.part:03d}.csv"
        self.handle = path.open("w", encoding="utf-8-sig", newline="")
        self.writer = csv.writer(self.handle)
        self.writer.writerow(self.columns)
        self.rows = 0
        self.paths.append(path)

    def write(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df = df.reindex(columns=self.columns, fill_value="")
        start = 0
        while start < len(df):
            if self.handle is None or self.rows >= self.rows_per_file:
                self._open()
            count = min(len(df) - start, self.rows_per_file - self.rows)
            self.writer.writerows(df.iloc[start:start + count].itertuples(index=False, name=None))
            self.rows += count
            start += count

    def close_current(self) -> None:
        if self.handle:
            self.handle.close()
        self.handle = self.writer = None

    def close(self) -> None:
        self.close_current()
