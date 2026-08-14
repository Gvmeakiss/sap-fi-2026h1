# SAP FI 2026 H1 处理工具

SAP FI 2026 上半年凭证与余额处理工具包，用于凭证、科目余额及维度数据的读取与处理，输出规范化结果供后续分析与审计使用。

## 功能特性

- ✅ **凭证处理**：SAP 会计凭证读取与规范化
- ✅ **余额处理**：科目余额汇总与计算
- ✅ **维度处理**：科目/成本中心等维度数据管理
- ✅ **前置检查**：数据完整性预检（preflight）
- ✅ **CLI 支持**：命令行入口，便于批处理与脚本集成

## 目录结构

```
sap-fi-2026h1/
├── cli.py          # 命令行入口
├── config.py       # 配置项
├── journal.py      # 凭证处理
├── balance.py      # 余额处理
├── dimensions.py   # 维度处理
├── io.py           # 输入输出
├── preflight.py    # 数据预检
└── __init__.py
```

## 快速开始

```bash
pip install -r requirements.txt  # 如存在依赖清单
python3 cli.py --help
```

## 环境要求

- Python 3.8+
- 依赖库：pandas、openpyxl 等（按实际配置安装）
