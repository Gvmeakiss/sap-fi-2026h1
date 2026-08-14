# SAP FI 2026 H1 处理工具 📊

> 读取 SAP 通用日记账（ACDOCA）、凭证抬头（BKPF）与科目余额（FAGLFLEXT），生成 2026 年上半年序时账、科目余额表并完成勾稽校验。

[![Language](https://img.shields.io/badge/language-Python-blue)](https://github.com/Gvmeakiss/sap-fi-2026h1) [![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/Gvmeakiss/sap-fi-2026h1/blob/main/LICENSE) [![Domain](https://img.shields.io/badge/domain-Audit%20Analytics-orange)](https://github.com/Gvmeakiss/sap-fi-2026h1)

## 📌 项目简介

本工具处理 2026 年上半年（`20260101`–`20260630`）SAP FI 数据（由审计提取工具以 `#|#` 分隔的 TXT 导出）。它读取 ACDOCA 通用日记账、BKPF 凭证抬头与 FAGLFLEXT 余额表，并关联 T001/SKAT/T003T/TBSLT/USER_ADDR/TSTCT/LFA1/KNA1/MAKT/ANLA/T881T 等维度表，输出规范化序时账、科目余额表与 ACDOCA 分类汇总，并对“序时账 vs 余额表”“余额结转 vs 期初”做交叉勾稽，支撑审计分析。

## ✨ 功能特性

- **前置检查 `preflight`**：校验 ACDOCA / BKPF / FAGLFLEXT / T001 / SKAT 的必含字段与文件存在性，输出 `运行前检查_2026H1.json`。
- **ACDOCA 分类 `classify`**：将记录区分为 正常日记账 / 余额结转BCF / 余额结转补充项 / 无BKPF待核查 四类，输出 `ACDOCA分类汇总_2026H1.csv`。
- **序时账 `journal`**：BKPF 与 ACDOCA 左连，合并维度表与中文字段名，生成规范化序时账（期间汇总）。
- **科目余额表 `balance`**：基于 FAGLFLEXT 计算期初、借方/贷方发生额与期末余额，输出 `科目余额表_2026H1.csv`。
- **勾稽校验 `validate`**：序时账期间汇总与余额表按（公司 + 科目）外连接勾稽（差异阈值 0.01），并核对 ACDOCA 余额结转与期初。
- **命令行入口 `cli`**：子命令 `preflight/classify/journal/balance/validate/all`，支持 `--companies` 多公司、`--ledger`、`--chunk-rows`、`--rows-per-file` 分块与分文件。

## 📂 目录结构

```
sap-fi-2026h1/
├── cli.py          # argparse 入口，子命令与参数
├── config.py       # Settings 数据类、ACDOCA/BKPF 字段常量、JOURNAL_COLUMNS、分隔符 #|#
├── journal.py      # load_bkpf、_merge_dimensions、build_journal、classify_acdoca
├── balance.py      # build_balance、validate_journal_to_balance
├── dimensions.py   # load_dimensions：T001/SKAT/T003T/TBSLT/USER_ADDR/TSTCT/LFA1/KNA1/MAKT/ANLA/T881T
├── io.py           # #|# 分隔符读取、分块 iter_delimited、SplitCsvWriter、choose_language
├── preflight.py    # 运行前字段/文件检查
├── __init__.py
└── requirements.txt
```

## 🔧 环境要求

- Python >= 3.10（代码使用 `dataclass(slots=True)`，需 3.10+）。
- 依赖：`pandas>=2.0`（见 `requirements.txt`）。

## 🚀 安装

```bash
git clone https://github.com/Gvmeakiss/sap-fi-2026h1.git
cd sap-fi-2026h1
pip install -r requirements.txt
```

## 💡 快速开始 / 使用示例

命令在仓库根目录运行（模块使用包内相对导入）：

```bash
# 运行前检查
python cli.py preflight --input-dir input --output-dir output_2026H1

# 全流程：分类 + 序时账 + 余额表 + 勾稽
python cli.py all --input-dir input --output-dir output_2026H1 --companies 4000 4010 --ledger 0L

# 仅生成科目余额表
python cli.py balance --input-dir input --output-dir output_2026H1
```

## 🧠 核心逻辑（方法论）

- **`preflight`**：校验 `ACDOCA_FIELDS`/`BKPF_FIELDS` 及 FAGLFLEXT、T001、SKAT 必含字段，统计文件大小，状态 `OK/ERROR` 写入 `运行前检查_2026H1.json`。
- **`journal`（build_journal）**：`load_bkpf` 按 `MANDT=client`、`GJAHR=year`、`BUDAT` 在 `[date_from, date_to]` 内过滤并做联接键去重校验，标记 `__BKPF_MATCH`；读取 ACDOCA 与 BKPF 左连后，按 `SGTXT` 前缀 `BCF:` 识别余额结转、按 `BELNR` 形如 `B\d+` 且 `BUZEI=000` 识别余额结转补充项、无 BKPF 匹配者归为待核查；`classify_acdoca` 分组汇总输出。
- **`balance`（build_balance）**：读取 FAGLFLEXT，过滤 `RYEAR/client/RLDNR=0L/RRCTY=0/RVERS=001`；`HSLVT` 为期初，`HSL01`–`HSL06` 求和得期间净发生额，按 `DRCRK`（S/H）拆借/贷方；按（公司 + 科目）`groupby` 得 `期末 = 期初 + 净发生额`。
- **`validate`（validate_journal_to_balance）**：序时账期间汇总与余额表按（公司 + 科目）外连接，`差异` 阈值 `0.01` 判定一致/差异；另以 ACDOCA 余额结转与期初余额核对，输出 `ACDOCA余额结转与余额表期初核对_2026H1.csv`。

## 📋 输入与输出

- **输入**：审计提取工具导出的 TXT（分隔符 `#|#`），命名形如 `FI202606<TOKEN>_*.TXT` 或 `<TOKEN>_*.TXT`；需含 ACDOCA、BKPF、FAGLFLEXT 及上述维度表。
- **输出**（`output_2026H1/`）：`运行前检查_2026H1.json`、`序时账期间汇总_2026H1.csv`、`科目余额表_2026H1.csv`、`ACDOCA分类汇总_2026H1.csv`、`ACDOCA余额结转与余额表期初核对_2026H1.csv`。

## ⚙️ 配置说明

`config.py` 中 `Settings` 默认值（可在 `cli` 通过参数覆盖）：

- `year="2026"`、`date_from="20260101"`、`date_to="20260630"`、`ledger="0L"`、`client="800"`
- `languages=("ZH","1","EN","E")`（维度表多语言优先级）、`chunk_rows=200_000`、`rows_per_file=800_000`
- `SEP="#|#"`；字段常量 `ACDOCA_FIELDS`、`BKPF_FIELDS`、`JOURNAL_COLUMNS`

## ⚠️ 注意事项

- 数据脱敏：不含真实客户业务数据，示例为脱敏/合成数据。
- 口径说明：匹配口径、期间与维度以代码与配置为准；`balance.py` 明确 FAGLFLEXT 的多币种维度 `RTCUR` 不拆分本位币余额。
- 输入目录需存在且包含前述必需表，否则 `preflight` 报错退出。

## 🔗 相关仓库

- [sap-abap-data-extraction](https://github.com/Gvmeakiss/sap-abap-data-extraction) — ECC6 取数 XML 配置与手册
- [sap-sd-three-match](https://github.com/Gvmeakiss/sap-sd-three-match) — SD 销售三单匹配与差异分析
- [test-tools](https://github.com/Gvmeakiss/test-tools) — 采购三单匹配测试与诊断工具集

## 📄 License

MIT

---

<div align="center">

*Disclaimer: Personal project and personal views. Not affiliated with or endorsed by KPMG or any client.*<br>
*本仓库为个人项目与个人观点，与任何前/现雇主及客户无关。*

</div>
