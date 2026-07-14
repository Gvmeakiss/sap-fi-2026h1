from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    input_dir: Path
    output_dir: Path
    year: str = "2026"
    date_from: str = "20260101"
    date_to: str = "20260630"
    ledger: str = "0L"
    client: str = "800"
    languages: tuple[str, ...] = ("ZH", "1", "EN", "E")
    chunk_rows: int = 200_000
    rows_per_file: int = 800_000
    companies: tuple[str, ...] = field(default_factory=tuple)

    def prepare(self) -> None:
        self.input_dir = self.input_dir.expanduser().resolve()
        self.output_dir = self.output_dir.expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.input_dir.is_dir():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")
        if self.date_from > self.date_to:
            raise ValueError("date_from 不能晚于 date_to")


SEP = "#|#"

ACDOCA_FIELDS = (
    "RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "DOCLN", "RYEAR",
    "XREVERSING", "RACCT", "RCNTR", "PRCTR", "RFAREA", "RASSC", "WSL",
    "HSL", "DRCRK", "BUZEI", "ZUONR", "BSCHL", "EBELN", "EBELP",
    "SGTXT", "KDAUF", "KDPOS", "MATNR", "LIFNR", "KUNNR", "KOART",
    "UMSKZ", "AUGDT", "AUGBL", "ANLN1", "ANLN2",
)

BKPF_FIELDS = (
    "MANDT", "BUKRS", "BELNR", "GJAHR", "BLART", "BLDAT", "BUDAT",
    "MONAT", "CPUDT", "CPUTM", "USNAM", "TCODE", "XBLNR", "STBLG",
    "BKTXT", "WAERS", "BSTAT", "GLVOR", "AWTYP", "XSTOV", "AWSYS",
    "PPNAM", "XREVERSAL", "RLDNR", "LDGRP",
)

JOURNAL_COLUMNS = (
    "记录类别", "BKPF匹配状态", "客户端", "分类账", "分类账名称", "公司代码", "公司名称", "会计年度",
    "凭证编号", "行项目号", "原始行项目号", "凭证类型", "凭证类型描述",
    "凭证日期", "过账日期", "会计期间", "录入日期", "录入时间",
    "录入用户", "用户姓名", "事务码", "事务码描述", "参考凭证号",
    "冲销凭证号", "凭证抬头文本", "凭证货币", "凭证状态", "业务交易",
    "参考交易", "源系统", "计划冲销标识", "冲销关系", "分类账组",
    "总账科目", "科目名称", "借贷方向", "本位币金额", "交易币金额",
    "借方本位币", "贷方本位币", "借方交易币", "贷方交易币",
    "成本中心", "利润中心", "功能范围", "贸易伙伴", "分配号",
    "过账码", "过账码描述", "行项目文本", "采购订单", "采购订单行",
    "销售订单", "销售订单行", "物料编号", "物料名称", "供应商编号",
    "供应商名称", "供应商名称1", "供应商名称2", "供应商名称3", "供应商名称4",
    "客户编号", "客户名称", "科目类型", "特别总账标识",
    "清账日期", "清账凭证", "资产主号", "资产次号", "资产名称",
    "反向凭证标识",
)
