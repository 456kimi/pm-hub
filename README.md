# PM-Hub 项目中枢

跨 AI 平台（WorkBuddy / CodeBuddy / Kimi CLI）共用的本地资产管理台账：
**项目 + 应用 + 文件地标**，单一真相源 `registry.json`。

## 关于本仓库

**这里只有工具代码，不含任何台账数据。** `registry.json`、`reports/`、导出的 `index.html`
以及运行日志全部通过 `.gitignore` 排除，因为它们记录的是本机真实的项目清单、文件路径与工作日志。

克隆后需要先建立自己的台账：把 `registry.json` 初始化成
`{"projects": [], "apps": [], "locations": []}`，再跑 `scanner.py` 盘点本机应用。
台账结构见 `AGENTS.md`。

想知道各条线的实际进展，看 [**PROJECT-STATUS.md**](PROJECT-STATUS.md) —— 它由
`export_status.py` 从台账导出，只包含超大项目（L1）及其子项目的目标、进度、任务与既有关键决策，
已剔除本机路径与私人日志。

## 日常使用

- 项目总览的「下一步工作」按任务状态汇总未归档项目的任务，点击「查看任务」可跳转到对应任务；待办状态不代表前置条件已经满足。
- 项目详情的任务清单默认显示未完成任务，可切换到全部或已完成；单条或批量新增后写入项目台账。
- 项目进度优先按任务完成数计算，没有任务时按目标计算，两者都没有时显示手动填写的值。超大项目会标明汇总口径和子项目任务覆盖情况；静态页面沿用相同口径。
- 看板与常用扫描脚本使用 `pm_registry.py` 安全提交台账，外部 AI 也应遵照 `AGENTS.md` 使用快照与 apply 命令。历史脚本如果直接覆盖 `registry.json`，会绕过并发保护。

## 快速开始

```bat
:: 1. 只读盘点（随时可重跑，绝不移动/删除文件）
python scanner.py

:: 2. 打开看板（浏览器 localhost:8501）
python -m streamlit run dashboard.py

:: 3. 不想开服务时：双击 index.html（每次台账变更自动重新导出）
```

依赖：Python 3.10+、`streamlit`。其余为标准库。

## 文件结构

| 文件 | 作用 |
|------|------|
| `AGENTS.md` | 所有 AI Agent 的接待文件（台账位置/读写协议/权限矩阵/禁区） |
| `registry.json` | 资产台账：`projects[]` + `apps[]` + `locations[]` |
| `scanner.py` | 只读扫描器：项目指纹识别 + 应用清点（注册表/开始菜单/便携目录） |
| `dashboard.py` | Streamlit 看板（总览/详情/应用台账/新增/待整理/地标） |
| `pm_registry.py` | 台账并发安全写入与本地命令 |
| `export_static.py` | 台账 → 静态 `index.html`（零依赖兜底） |
| `reports/` | 盘点报告与未登记清单（scan-YYYY-MM-DD.md / unregistered.json）｜本仓库不包含 |

## 规则速记

- 物理归档/删除/移动：**必须逐条确认**，≤10 条/批，先备份（见 AGENTS.md）
- AI 改台账必须署名 `operator`；台账建议纳入 git 版本控制
- 扫描器只读：任何情况下不移动、不删除、不改名用户文件
