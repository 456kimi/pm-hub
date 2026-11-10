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
`export_status.py` 从台账导出，只包含超大项目（L1）及其子项目的目标、进度、任务与
**现行决策（`status="active"`；已推翻的结论不会出现）**，已剔除本机路径、私人日志与密钥。

> 公开导出只有 `PROJECT-STATUS.md` 一个文件。改这一条要谨慎：
> 它还包含项目目标与策略结论，不含台账原文、不含绝对路径、不含任何凭据。

## 任务交接包（半自动 AI 协作）

没有模型 API 权益也能把活交给 AI：**PM-Hub 出任务包 → 你在对话框里交付 → AI 写回结果 → PM-Hub 校验**。
全程只走本地文件，不联网、不调用任何模型。

```bat
:: 为某条任务生成交接包（也可在看板任务详情里点「生成交接包」）
python pm_handoff.py export --project <小项目 id> --task <任务 id>

:: AI 执行完把 RESULT.md / EVIDENCE.json 写回该目录后：
python pm_handoff.py import --dir .pmhub\handoffs\<handoff_id>
```

生成的目录（`.pmhub/handoffs/<handoff_id>/`，已 gitignore）：

| 文件 | 谁写 | 内容 |
|------|------|------|
| `TASK.md` | PM-Hub | 任务正文、授权范围、禁止事项、验收标准 |
| `CONTEXT.md` | PM-Hub | 项目目标、L1/L2 现行决策、数据范围、非目标 |
| `MANIFEST.json` | PM-Hub | 机器可读的授权根目录与禁止项，校验以此为准 |
| `HANDOFF.md` | PM-Hub | 一段可直接贴进 ZCode / WorkBuddy 对话框的接手指令 |
| `RESULT.md` | 执行方 | 做了什么、改了哪些文件、还剩什么问题 |
| `EVIDENCE.json` | 执行方 | 结构化证据：文件清单、测试命令与结果、需审批事项 |
| `VALIDATION.json` | PM-Hub | 导入时的校验结论 |

校验只比对**格式、ID 与文件范围**，**绝不执行** EVIDENCE 里写的命令；
校验通过也不等于任务完成 —— 验收由人判断。

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

## 日常打开：双击 `pmhub_app.bat`

这是**推荐入口**，和"开个网页"不是一回事：

- 弹的是**独立应用窗口**（Edge `--app` 模式，无地址栏、单独任务栏图标），关掉不影响服务
- 每次启动**先做健康检查**（`/_stcore/health` 是否返回 `ok`）：
  - 健康 → 直接开窗口，不重复起服务
  - 死了 / 假活（端口在但页面报错）→ 自动清端口并重新拉起，最多等 45 秒
- 所以"打不开"的处置方式就是：**再点一次图标**。不用记命令、不用看日志

想放到桌面/任务栏：右键 `pmhub_app.bat` → 发送到 → 桌面快捷方式，再把快捷方式拖到任务栏。

> `open_dashboard.bat` 仍保留（探端口 + 开默认浏览器），是给"只想在浏览器里看"的场景用的；
> `pmhub_app.bat` 多了一层健康自愈，日常优先用它。

### 页面报错时怎么排查

1. 先看 `_dash_run.log` 末尾（pythonw 没有控制台，所有异常都落在这里）
2. 常见两类：
   - **改了代码后白屏 / `ImportError`**：以前必须重启进程。现在 `dashboard.py` 开头会按文件
     mtime 自动重载 `pm_progress / pm_registry / pm_handoff / theme / export_static`，
     改完刷新页面即可生效（重载失败会保留旧版本，不会整页崩）
   - **`ConnectionResetError [WinError 10054]`**：浏览器刷新/关标签时的噪音，不影响服务，可忽略
3. 真要硬重启：`stop_dashboard.bat` → `pmhub_app.bat`

## 文件结构

| 文件 | 作用 |
|------|------|
| `AGENTS.md` | 所有 AI Agent 的接待文件（台账位置/读写协议/权限矩阵/禁区） |
| `registry.json` | 资产台账：`projects[]` + `apps[]` + `locations[]` |
| `scanner.py` | 只读扫描器：项目指纹识别 + 应用清点（注册表/开始菜单/便携目录） |
| `dashboard.py` | Streamlit 看板（总览/详情/应用台账/新增/待整理/地标） |
| `pm_registry.py` | 台账并发安全写入与本地命令 |
| `pm_handoff.py` | 任务交接包：生成 TASK/CONTEXT/MANIFEST，回收并校验 RESULT/EVIDENCE |
| `pm_progress.py` | 进度口径（唯一实现，看板/静态页/状态导出共用） |
| `export_static.py` | 台账 → 静态 `index.html`（零依赖兜底） |
| `pmhub_app.bat` | **日常入口**：健康自检 + 自愈重启 + 独立应用窗口 |
| `open_dashboard.bat` | 备用入口：探端口后打开默认浏览器 |
| `stop_dashboard.bat` | 只杀占用 8501 的那个进程（不误伤别的 Python 进程） |
| `reports/` | 盘点报告与未登记清单（scan-YYYY-MM-DD.md / unregistered.json）｜本仓库不包含 |

## 规则速记

- 物理归档/删除/移动：**必须逐条确认**，≤10 条/批，先备份（见 AGENTS.md）
- AI 改台账必须署名 `operator`；台账**不入公开仓库**（`.gitignore` 已排除 `registry*`），
  本地版本留痕靠 `registry.backups/`（每次写入自动生成完整快照）
- 扫描器只读：任何情况下不移动、不删除、不改名用户文件
