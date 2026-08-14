# SAP FI 2026 H1 处理工具

> SAP FI 2026 上半年凭证、科目余额与维度数据的读取与规范化处理，输出供审计分析使用。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/SAP-FI%20%7C%20Journal%20%7C%20Balance-1F6FB2" alt="SAP FI">
  <img src="https://img.shields.io/badge/CLI-Supported-0E8A16" alt="CLI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/github/last-commit/Gvmeakiss/sap-fi-2026h1?label=updated" alt="Updated">
</p>

## 📋 目录

- [功能特性](#功能特性)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [环境要求](#环境要求)

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

## 🧩 模块说明

| 模块 | 职责 |
|------|------|
| `cli.py` | 命令行入口，支持参数化批处理与脚本集成 |
| `config.py` | 路径、期间等运行配置 |
| `journal.py` | SAP 会计凭证读取与规范化 |
| `balance.py` | 科目余额汇总与计算 |
| `dimensions.py` | 科目 / 成本中心等维度数据管理 |
| `io.py` | 输入输出与文件读写 |
| `preflight.py` | 数据完整性预检（缺字段、格式异常等） |

## 🧱 技术栈

| 领域 | 工具 / 技术 |
|------|-------------|
| 语言 | Python 3.8+ |
| 数据处理 | pandas |
| 文件读写 | openpyxl / csv |
| 入口 | CLI（argparse） |

---

<div align="center">

**James Li · 审计数据分析工具集**

📫 本工具用于内部审计与数据核对，辅助分析但不替代专业判断，不作为对外签字版本。

</div>
