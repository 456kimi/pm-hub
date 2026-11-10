# LOCAL-BASELINE-AUDIT — PM-Hub 本地基线审计（P0-01 / P0-02 / P0-03）

- **审计日期**：2026-11-10
- **审计对象**：用户本机正在运行的 PM-Hub（本地文件为唯一事实来源）
- **审计方式**：只读检查 + 隔离目录测试；未改写 `registry.json` 业务内容，未覆盖任何源文件
- **对应任务书**：PM-Hub V1.1-S 第三节 P0（本地审计与安全修复）

---

## 一、结论摘要

| 维度 | 结论 |
|---|---|
| 本地版本 | 可运行，入口与数据齐备；当前 HEAD `10d279b`，工作区干净 |
| 测试基线 | 审计前 **68 tests / OK / 4.3s**；本次修复后 **77 tests / OK / 5.6s** |
| P0-03 八项 | **5 项本地确认真实存在并已修复**、2 项上一轮已修、1 项部分成立已消解 |
| 私有数据入库 | 已跟踪 28 个文件，**无 registry / 日志 / 任务包 / 截图 / 报告被跟踪** |
| 台账备份 | `registry.backups/` 每次保存留档，实测最新一份为 20:48:53 |
| 遗留风险 | 台账内 1 个历史重复应用 id 未自动改写（需老板确认）；关键决策仍缺代码级审批（P1-04） |

---

## 二、本地实际运行版本

### 2.0 P0-01 十项检查回执（逐条实测）

| # | 任务书检查项 | 实测结果 |
|---|---|---|
| 1 | 确认项目根目录 | `H:\github\pm-hub`（`pwd` 实测）；`HUB` 由 `__file__` 推导 |
| 2 | 检查本地实际文件和目录 | 顶层 158 项；核心 8 个 py 模块 + `tests/`(8 个测试文件) + `registry.backups/` + `.streamlit/` |
| 3 | 确认程序入口与启动方式 | `start_dashboard.bat`、`pmhub_app.bat`（探活+自愈+Edge 独立窗口）、`stop_dashboard.bat`；命令行为 `streamlit run dashboard.py --server.address=127.0.0.1 --browser.gatherUsageStats false` |
| 4 | 确认正式台账位置 | `<根目录>/registry.json`，**773,072 字节**（21:51 登记 progress_log 后） |
| 5 | 确认扫描范围与路径配置 | `SCAN_ROOTS` 11 处、深度 1–2；排除 `C:\`、游戏/影音目录、`H:\Program Files` 等；微信目录不在范围内 |
| 6 | 检查 Git 状态 | 分支 `master`，HEAD `10d279b`，remote `456kimi/pm-hub` |
| 7 | 检查未保存/未提交修改 | `git status --porcelain` **为空**（工作区干净）；台账与 WORKLOG 的本地变化属忽略项，不入库 |
| 8 | 检查现有测试 | 8 个测试文件，覆盖台账并发、扫描并发、看板表单、交接包、导出脱敏、进度口径 |
| 9 | 运行非破坏性基线测试 | **Ran 77 tests / OK / 5.700s**（使用看板同一套解释器；未写正式台账） |
| 10 | 记录真实运行结果 | 本节 + 全文；看板进程实测见 2.3 |

> 看板运行态：审计时 **8501 无监听、无 streamlit 进程**。日志显示最后一次启动为 20:43:06（PID 36096），此后无 traceback，判定为被正常关闭；按 AGENTS.md"AI 不得代为启动应用"，本次未拉起。启动入口本身经 20:48 实测可用（health=ok）。

### 2.1 项目根目录与事实来源

- 本地根目录：`H:\github\pm-hub`（`dashboard.py` 用 `HUB = Path(__file__).resolve().parent` 推导，换目录可运行）
- 正式台账：`<根目录>/registry.json`，**773,072 字节**
- 台账规模实测：项目 36（其中 `kind=program` 4）、应用 722、位置 12、任务 80、决策 70（active 69 + revoked 1）、进展流水 180 条

### 2.2 Git 版本差异（重要）

| 项 | 值 |
|---|---|
| 本地 remote | `https://github.com/456kimi/pm-hub.git` |
| 任务书所写参考仓库 | `https://github.com/jgwse258/pm-hub` |

**两者不是同一个仓库**。按任务书 1.1 条，本次实施只以本地代码为准，未从任何 GitHub 仓库拉取或覆盖；该远端差异仅作记录。

### 2.3 程序入口与启动方式

| 用途 | 入口 | 说明 |
|---|---|---|
| 看板 | `start_dashboard.bat` / `pmhub_app.bat` | Streamlit，绑定 `127.0.0.1:8501`，已关遥测（符合"纯本地、禁公网"硬规则） |
| 关闭 | `stop_dashboard.bat` | 按端口/进程关闭 |
| 台账读写 | `pm_registry.py` | 文件锁（msvcrt/fcntl）+ 三方合并 + `NamedTemporaryFile → os.replace` 原子写 + `registry.backups/` 快照 |
| 盘点 | `scanner.py` | 只读扫描（项目指纹 + 应用清点），不改动被扫目录 |
| 静态导出 | `export_static.py` → `index.html` | 含全量台账，属敏感产物（已在 .gitignore） |
| 公开状态导出 | `export_status.py` → `PROJECT-STATUS.md` | 只导 4 个 `kind=program` 树，剔 `dev_logs`/`paths`，路径与密钥脱敏 |
| 交接包 | `pm_handoff.py`（CLI + 看板） | 纯文件、零网络、不调模型；结果导入只校验不执行 |

### 2.4 代码结构（行数实测）

| 文件 | 行数 | 职责 |
|---|---|---|
| `dashboard.py` | 2459 | 看板主脚本（三级下钻、任务/决策/日志、交接包入口、热重载） |
| `theme.py` | 816 | 7 套主题 token 与 CSS |
| `pm_handoff.py` | 685 | 任务包生成、校验、结果导入 |
| `bulk_describe.py` | 572 | 应用用途批量回填（启发式 + web 缓存） |
| `scanner.py` | 546 | 项目/应用盘点 |
| `export_status.py` | 392 | 脱敏公开状态导出 |
| `pm_registry.py` | 267 | 台账并发安全读写 |
| `pm_progress.py` | 59 | 进度统一口径（看板/静态页/导出共用） |

### 2.5 扫描范围与禁区

`scanner.py` 的扫描根：`H:\github`(深度2)、`H:\ai`(1)、`H:\`(1)、`H:\Claw_backup`(1)、`H:\voi`(1)、`H:\3#罐组智能系统`(1)、`G:\`(1)、`G:\agents`(2)、`G:\a`(2)、`G:\wechat-export`(1)、`E:\software`(1)。

排除：`C:\`、`E:\play`、`G:\g`、`G:\SteamLibrary`、`G:\CloudMusic`、`G:\Youku Files`、`G:\动漫`、`G:\夸克`、`G:\照片`、`G:\相机来`、`G:\视频`、`G:\MOD`、`H:\WindowsApps`、`H:\Program Files`、`H:\XBOX`，以及 `node_modules/.git/venv/site-packages/__pycache__` 等。

**微信数据目录 `D:\xwechat_files` 不在任何扫描根下**，不会被盘点触及。扫描器全程只读，不移动/删除文件。

> `SCAN_ROOTS` / `APP_PORTABLE_DIRS` 中的盘符是本机盘点配置（业务输入），不属于"换目录无法运行"的硬编码缺陷；本次只修了运行时路径常量。

### 2.6 未提交修改

审计启动时 `git status` 有 6 项改动（上轮 P0-A/P1-A 之后的看板稳定性修复 + 本次 P0 修复），**审计过程中未发现被意外覆盖的本地文件**。这些改动已随 `10d279b` 提交，当前 `git status --porcelain` 为空。

台账与 `WORKLOG.md` 的本地变化属 `.gitignore` 忽略项，不进入公开仓库。

---

## 三、测试基线

- 必须使用看板同一套解释器：`<workbuddy env>/python.exe -m unittest discover -s tests`
- 系统裸 `python` 会因缺 `streamlit` 只跑 23 项并报 1 error，**不能作为基线**
- 测试不写正式台账（`registry.json` mtime 保持不变），全部在 `tests/phase2_apptest_*` 临时目录内运行

| 时点 | 数量 | 结果 | 耗时 |
|---|---|---|---|
| 本轮审计启动前 | 68 | OK | 4.3s |
| 本次 P0 修复后 | **77** | **OK** | **5.6s** |

新增 9 项：`tests/test_p0_fixes.py`（扫描 id 唯一性 3、web 代拟 1、交接包验收 2、看板缺验收拦截 1、卡片转义 1、路径卫生 1）。

---

## 四、P0-02 本地数据安全核查

| 检查项 | 实测结果 | 判定 |
|---|---|---|
| 台账备份保护 | `pm_registry.save_registry` 写入 `registry.backups/<时间戳>_<uuid>.json`；实测最新 20:48:53，与保存次数同步 | ✅ |
| 路径配置 | 运行时路径均由 `HUB`（`__file__`）推导；仅扫描配置含本机盘符（设计如此） | ✅ 已修硬编码 1 处 |
| 扫描越界 | 扫描根限定 11 处、深度 1–2，`C:\`/微信目录/游戏目录在排除或范围外；全程只读 | ✅ |
| 私有数据误提交 | `git ls-files` 共 28 个文件，无 `registry*`、`reports/`、`devlogs/`、`index.html`、`.pmhub/`、截图、`WORKLOG.md` | ✅ |
| 未授权文件修改 | 交接包只授 `allowed_roots`（项目 root + 任务输入/输出所在目录），`validate_pack` 对越界与"改台账"直接阻断 | ✅（P1-A 已建） |
| 未审批改关键决策 | 代码层无审批闸门：任何能跑 Python 的进程都可经 `pm_registry` 改 `decisions`；当前依赖 AGENTS.md 约定 | ⚠️ 已知风险 → P1-04 |
| 私有内容外发 | 无任何自动上传逻辑；`export_status.py` 只导 4 个 program 树且脱敏 | ✅ |

`.gitignore` 已覆盖：`registry*`、`unresolved.json`、`web_cache.json`、`ui_prefs.json`、`.pmhub/`、`index.html`、`preview/`、`WORKLOG.md`、`reports/`、`devlogs/`、`*.log`、`*.png/jpg/docx`、`__pycache__`、`tests/phase2_apptest_*/`、`.env*`。

> `.gitignore` 只防误提交，不承担本地访问控制——该边界已写入 README/AGENTS。

---

## 五、P0-03 八项逐条判定

| # | 审查项 | 本地判定 | 证据 | 处置 |
|---|---|---|---|---|
| 1 | 已撤销决策被当有效导出 | 真实存在（上轮已修） | `export_status.py` 原 decisions 零过滤；台账 69 active + 1 revoked（`d10` 尾部型风险，2026-10-19 被 `d11` 取代） | 上轮改为只导 active；`tests/test_export_status.py` 断言含 revoked 台账不出现该条 |
| 2 | 新建任务允许缺验收标准 | **真实存在，本次已修** | `dashboard.py` 原逻辑仅 `if nt_ok and nt_title.strip()`；批量粘贴第 3 段可空 | 单条：缺验收拒绝入库并提示；批量：缺标题/验收整行跳过并报数；交接包：`export_pack` 前置 `ValueError`。测试 3 项 |
| 3 | 应用扫描生成重复 ID | **真实存在（台账实证 1 例），本次已修** | 台账 `dup_ids=1`：`microsoft.net.workload.mono.toolchain.ne`；id 由 `norm(name)[:40]` 生成，不同名字截断后撞车，而原代码用 **name 集合**判重 | 抽 `assign_unique_ids()` 按 **id** 判重，冲突依次 `-2/-3…`；新增 3 项测试。**存量重复 id 未自动改写**（见风险 R1） |
| 4 | AI 代拟内容被标为用户确认 | **真实存在，本次已修** | `bulk_describe.py:515` 命中 `web_cache` 即 `desc_confirmed = True`，与文件头注释"保留 False（AI 代拟待确认）"自相矛盾；`web_cache.json` 9 条含"具体产品待确认" | 抽 `apply_web_cache()` 固定 `desc_confirmed=False` 且保留 `auto_source="web"`；1 项测试 |
| 5 | 页面未正确处理不可信 HTML | **真实存在，本次已修** | `dashboard.py` 仅 4 处 `html.escape`，而 `card_program_html` / `card_project_html` 直接插入 `name/description/root/stage`；台账实测 5 个字段含 `&`（如 `ACA & MEP 2018 Object Enabler`） | 卡片内台账文本统一 `html.escape`；AppTest 断言渲染结果含 `&lt;b&gt;` |
| 6 | 任务包遗漏上级项目有效决策 | 真实存在（上轮已修） | 原 `render_task_brief` 只带 L2 决策 | 上轮 `pm_handoff` 增加父 L1 的 active 决策；`tests/test_handoff.py` 覆盖 |
| 7 | 本地绝对路径写死 | **真实存在 1 处，本次已修** | `dashboard.py:1125` `DEVLOGS_DIR = r"H:\github\pm-hub\devlogs"` | 改为 `str(HUB / "devlogs")`；源码守卫测试断言不含该字面量 |
| 8 | 文档与代码的 AI 权限规则不一致 | 部分成立，已消解 | ① 同 #4：`bulk_describe` 文件头声明与实现相反；② 交接包 `forbidden` 未列 `dev_logs`（AGENTS.md 明令 AI 只读）；③ 文档未声明任务包自身只读 | 均补齐：注释与实现一致、`forbidden` 增 `dev_logs` 与"任务包只读快照" |

---

## 六、未解决风险

| 编号 | 风险 | 影响 | 建议 |
|---|---|---|---|
| R1 | 台账存量 1 个重复 app id（`microsoft.net.workload.mono.toolchain.ne`） | 若其他条目用 `related_projects` 引用它，会指向两条记录之一 | 生成侧已阻断新增；存量需老板确认后改名（涉及引用），本轮不擅自动台账 |
| R2 | 关键决策无代码级审批 | 能跑 Python 的进程可直接改 `decisions` | P1-04 审批记录 + 决策激活闸门 |
| R3 | `PROJECT-STATUS.md` 公开导出含项目目标与结论措辞 | 策略性表述外泄（不含密钥/绝对路径/公司项目） | 已确认可接受；如需更严，P1 增加白名单段落 |
| R4 | 一次性 `sync_entry_*` / `update_entry_*` 脚本写死本机路径 | 换机不可复用 | 历史存档、已 gitignore、不再运行；不属本次范围 |
| R5 | 看板热重载仅覆盖 5 个模块 | 改 `scanner.py`/`bulk_describe.py` 需重启看板才生效（本次改动即属此类） | 已在 README 说明；重启由老板执行（禁止擅杀进程） |

---

## 七、阶段交付清单

**本次修改文件（5 改 1 增）**

| 文件 | 改动 |
|---|---|
| `scanner.py` | 新增 `assign_unique_ids()`，按 id 判重替换原按 name 判重 |
| `bulk_describe.py` | 新增 `apply_web_cache()`，web 代拟不再标 `desc_confirmed=True` |
| `dashboard.py` | ① `DEVLOGS_DIR` 改由 `HUB` 推导；② 两处卡片 HTML 转义；③ 单条/批量新增任务强制验收标准 |
| `pm_handoff.py` | ① 无验收标准拒绝生成交接包；② `forbidden` 补 `dev_logs` 与任务包只读 |
| `tests/test_dashboard_concurrency.py` | fixture 补验收标准，符合新规则 |
| `tests/test_p0_fixes.py` | 新增 9 项回归测试 |

**验证证据**

- `python -m unittest discover -s tests` → `Ran 77 tests / OK / 5.700s`（复跑一次 5.585s，均在 5.6–5.7s 区间）
- 真实台账 AppTest 渲染：项目总览 / 项目详情两页 `exception=False`
- 台账业务数据未改：仅保留原有 mtime 20:48（本次未走写台账流程）

**下一阶段依赖**

- P1-B（审批流）/ P1-C（run manifest）尚未开始；P1-06 的审批与恢复入口依赖二者
- 看板需重启才能加载 `scanner.py` / `bulk_describe.py` 的改动（`dashboard.py` 走热重载，已自动生效）
