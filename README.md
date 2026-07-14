# S/4HANA FI 序时账导出工具

这是一个可复用的 ACDOCA 驱动序时账代码包。它按 BKPF 的过账日期限定期间，直接保留 ACDOCA 行级字段，并用 FAGLFLEXT 做期间发生额及年度期初余额核对。

## 处理边界

- 正常日记账：ACDOCA 行能够按客户端、公司代码、凭证编号、会计年度直接匹配 BKPF。
- 供应商：只输出当前 ACDOCA 行自身的 `LIFNR`，再直接关联 LFA1 名称；不跨行传播、不通过采购订单反查、不做复杂钩稽。
- 余额结转：优先识别 `SGTXT` 以 `BCF:` 开头的行，并保留当前项目已经验证过的无 BKPF 补充规则。
- 输出按公司拆分，每个 CSV 默认最多 80 万数据行，转换后每个 Excel 不超过 100 万行。

## 目录

```text
sap_s4hana_journal/       核心包
run_s4hana_journal.py     通用运行入口
run_2026h1.py             本次项目兼容入口
docs/2026H1/              本次字段映射和运行说明
input/                    KPMG 取数结果
output_2026H1/            已核对 CSV
output_2026H1_excel/      已转换 Excel
```

## 新系统使用

取数 TXT 文件可使用 `ACDOCA_0001.TXT`，也可使用 `任意前缀ACDOCA_0001.TXT`。程序按准确的 `TABLE_` 片段自动识别；如一个目录混有多批数据，可传 `--file-prefix` 限定批次。

先运行轻量检查：

```bash
python run_s4hana_journal.py preflight \
  --input-dir /path/to/input \
  --output-dir /path/to/output \
  --client 800 --ledger 0L --year 2026 \
  --date-from 20260101 --date-to 20260630 \
  --label 2026H1
```

检查为 `OK` 后生成序时账、余额表和核对文件：

```bash
python run_s4hana_journal.py all \
  --input-dir /path/to/input \
  --output-dir /path/to/output \
  --client 800 --ledger 0L --year 2026 \
  --date-from 20260101 --date-to 20260630 \
  --label 2026H1 --chunk-rows 200000 --rows-per-file 800000
```

如果会计年度不是自然年度，必须明确传 FAGLFLEXT 的期间范围，例如 `--period-start 4 --period-end 9`。日期范围仍用于 BKPF 过滤，期间参数用于余额表期初和发生额计算。

最后并行转换全部 CSV 为 Excel：

```bash
python -m sap_s4hana_journal.csv_to_xlsx \
  --input-dir /path/to/output \
  --output-dir /path/to/output_excel \
  --workers 4
```

Excel 转换使用常量内存流式写入，编号字段保持文本，金额字段保存为数值，并逐文件验证 ZIP 完整性、表头及行列数。

## 新系统上线前检查清单

1. 确认 ACDOCA、BKPF、FAGLFLEXT 以及主数据 TXT 均属于同一客户端和同一批次。
2. 先看 `运行前检查_<标签>.json`，缺字段时不要直接生成。
3. 确认公司代码、分类账、年度、日期和会计期间参数。
4. 先运行 `classify` 观察 BCF、正常日记账和无 BKPF 数量，再决定是否运行全量。
5. 完成后检查 `序时账与余额表核对_<标签>.csv` 和 `ACDOCA余额结转与余额表期初核对_<标签>.csv` 的差异数。

安装为本机命令（可选）：

```bash
python -m pip install -e .
s4hana-journal --help
```
