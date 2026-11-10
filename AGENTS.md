# 工作台接待文件（所有 AI Agent 必读）

> 本文件是 PM-Hub 的"前台接待"。任何 AI 平台（WorkBuddy / CodeBuddy / Kimi / 其他）进入工作台，
> 先读本文件，即可获得全部上下文与操作规则。

## 台账位置（唯一真相源）

- **资产台账**: `H:\github\pm-hub\registry.json`
  - `projects[]` 项目（**三级体系**：L1 超大项目 → L2 小项目 → L3 任务）| `apps[]` 应用 | `locations[]` 文件地标
- **盘点报告**: `H:\github\pm-hub\reports\`（scanner 只读扫描产物）
- **看板**: `streamlit run H:\github\pm-hub\dashboard.py` → 浏览器 localhost:8501
- **静态版**: `H:\github\pm-hub\index.html`（每次台账变更自动导出，双击即看）

## 读写协议

1. **读**：直接读 registry.json，字段含义见文件内首条注释与本文件附录。
   ⚠️ **动手前必读对应项目的 `decisions[]`（现行结论）**——那是老板定的当前口径，违反即返工。
2. **修改台账**：通过 `pm_registry.py` 提交，不要直接覆盖 `registry.json`。先运行
   `python H:\github\pm-hub\pm_registry.py snapshot --output H:\github\pm-hub\reports\my-base.json`，
   再将该文件复制为 `my-edited.json` 并修改副本，最后运行
   `python H:\github\pm-hub\pm_registry.py apply --base H:\github\pm-hub\reports\my-base.json --edited H:\github\pm-hub\reports\my-edited.json --operator 你的平台名`。
   每次任务使用独立文件名，冲突时保留草稿并检查最新台账。程序负责署名和更新时间。
   若台账已保存但静态页更新失败，使用 `python H:\github\pm-hub\pm_registry.py export` 单独重试导出。
3. **追加日志**：append 到对应项目根目录 `WORKLOG.md`，一行一条 `- [YYYY-MM-DD] 事件`。
4. **登记新项目/应用**：按既有条目结构追加，必填 name + purpose/description。
5. **扫描**：`python H:\github\pm-hub\scanner.py`（只读检查文件系统，可向台账安全回填发现的信息）。
6. **推进项目进度**（推荐方式）：优先给 L2 小项目的 `tasks[]` 增删任务、把已完成任务的 `status` 置 `done`；
   若项目还没有任务，则维护 `goals[]`（把已完成目标的 `done` 置 true）。
   两者都记得往 `progress_log[]` 追加一条 `{date, text}`"主要进展"。`progress` 会自动重算，无需手填。
7. **拆任务（推荐给 AI 下指令前先做）**：把一件事拆成 3–8 条可独立交付的任务写进 `tasks[]`，
   每条必须带 `acceptance`（可判定的验收标准）与 `inputs`（要读的文件）；`batch` 相同的任务表示同一批交付。
   看板上导出任务包后，把那一整段贴给 AI —— **不要用一句话指挥 AI**，上下文不全必然产出粗略。

## 结论与裁决（decisions）—— 推翻旧结论的唯一正道（2026-10-08 新增）

> 起因：老板指出 AI 长期记忆**只能追加、无法删除**，要推翻一个旧决定只能"再写一条『忘记 XX』"，
> 记忆越滚越乱、旧结论永远还在。⇒ **项目层面的结论一律放台账，不放 AI 记忆。**

- **`decisions[]{id, date, text, note, status(active|revoked), updated, revoked_on}`**
  - `status="active"` = **现行口径**，AI 必须遵守；`status="revoked"` = 已推翻（存档，不再执行）。
- **AI 的义务**：
  1. **动手前先读**本项目 `decisions[]` 里的 active 条目，按此执行；看板导出的任务包会自动带上这一段。
  2. 工作产生**新口径**（统一走某数据源、否决某方案、锁定某参数）→ **追加一条 decision**，
     `note` 写依据；**不要**把它只写进自己的长期记忆。
  3. 发现某条旧结论已被现在的做法取代 → 把那条 `status` 改成 `revoked` 并补 `revoked_on`，
     **不要**在别处写"忘记 XX"式补丁。
- **老板的义务（也是权限）**：在看板项目详情页「结论与裁决」区块可直接 **添加 / 改 / 推翻 / 删除**——
  这是唯一能"撤销 AI 认知"的地方。⛔ AI **不得**自行推翻老板写的结论（要推翻须先问）。
- 与 `progress_log` 的区别：`progress_log` 是**流水**（发生过什么，只增不改）；
  `decisions` 是**当前该怎么做**（可撤销的状态）。别把结论写进 progress_log 就当完事。

## AI 记忆存放规则（2026-10-08）—— 项目相关的一律写台账，别只写自己的记忆

> 老板原话："要推翻旧决定，只能在 AI 记忆上再加一条『忘记』，记忆系统会非常混乱。"
> ⇒ **凡是你希望老板看得见、改得掉的东西，就写进台账；写进 AI 自己的记忆文件，老板改不掉。**

按作用域分四处存放：

| 记忆类型 | 存哪 | AI 权限 | 老板权限 |
|---|---|---|---|
| 项目级结论 / 口径（会变的"该怎么做"） | 本项目 `decisions[]` | ✅ 可追加 | ⭐ 可改 / 推翻 / 删除 |
| 项目动态（发生了什么、参数或状态变化） | 本项目 `progress_log[]` | ✅ 可追加 | 可删 |
| AI 跑出来的日志文件 | 本项目 `ai_logs[]` | ✅ 可追加 | 可删 |
| 用到的文件 / 关键参数 / 任务 | 本项目 `files[]` / `params[]` / `tasks[]` | ✅ 可维护 | 可改 |
| **跨项目**稳定偏好（例：大文件一律放 G 盘） | 各自的记忆文件（`~/.workbuddy/MEMORY.md`、工作区 memory） | 可写 | 需直接改文件 |
| ⛔ `dev_logs[]`（我的日志） | 本项目，**老板专属** | **只读，严禁写改删** | 可写 |

**硬规则**：
1. 干了活 → **先写台账**（`decisions` / `progress_log` / `ai_logs`），再考虑写不写自己的记忆文件。
2. 写台账必须署名：写回后更新顶层 `operator`（例 `阿布(workbuddy)`）与 `updated_at`。
3. **项目相关的结论不要只写进 AI 长期记忆**——那对老板是不可撤销的，等于失控。
4. 老板要撤销 AI 的认知：在项目详情页「结论与裁决」点 **推翻 / 删除** 即可；
   下一轮 AI 读项目时看到的就是新的，**不需要**跟 AI 说"忘掉某某"。

## 三级项目体系（L1 / L2 / L3）

| 层级 | 实体 | 字段 | 看板位置 |
|------|------|------|----------|
| L1 超大项目 | `kind="program"` 的 project 条目 | `goals[]`（战略目标） | 项目总览 → 超大项目卡片 |
| L1' 独立小项目 | `kind="project"` + `parent=null` | `goals[]` / `tasks[]` | 项目总览 → 独立小项目卡片（**与超大项目平级**） |
| L2 小项目 | `kind="project"` + `parent=<L1 id>` | `goals[]` / `tasks[]` | 点 L1 卡片 → 小项目列表 |
| L3 任务 | `tasks[]` 条目 | 见下 | 点小项目卡片 → 任务清单 |

- ⚠️ **独立小项目是合法形态，不是"待归位"**：一个项目自成一体、不需要跟别的项目凑成"大工程"时，
  就让 `parent` 保持 `null`。**不要为了"整齐"把独立项目硬塞进某个超大项目。**
- **什么时候才建 L1**：只有当一件事**确实是要一次性开发的大东西、由多个体系/子系统构成**时，
  才建 `kind="program"` 并把它的子系统作为 L2 挂进去（例：A股量化交易体系 = 数据/因子/模拟盘/监控四段）。
  判断口径：拆掉其中任何一个子系统，这个 L1 还成立吗？成立 → 说明它不是 L1，只是若干独立项目的集合。

- `tasks[]` 条目形状：`{id, title, detail, acceptance, inputs, outputs, batch, status, updated, prompt}`
  - `status` ∈ `todo | doing | done | blocked`
  - `acceptance` 必填（否则无法判定交付）· `inputs` 写要读的绝对路径 · `batch` 例 `B1`（同批一起交给 AI）
  - `prompt` 一般留空；看板"AI 任务指令"面板与任务包导出会**自动**拼出完整指令
- **拆解原则**：一个小项目 = 一个能独立说清的目标；一条 L3 任务 = 一次可验收的交付。
  大目标不要直接交给 AI，先落小项目，再拆任务，再分批交付。
  独立项目**直接作为第一级条目存在**即可（`parent=null`），不必先找"上级"。
- **进度优先级**：`tasks` 非空 → `progress = 已完成任务 ÷ 任务总数`；否则 `progress = 已完成目标 ÷ 目标总数`。
- 新建条目有两种方式：看板「➕ 新增登记」（选「小项目」时归属可留空＝独立）、或通过上述安全写入命令提交。
  看板上给某 L1 新建 L2 的入口在 L1 详情页底部；把小项目改挂到某个 L1 用项目详情页的「层级归属」。
- 迁移脚本参考：`migrate_hierarchy_20260917.py`（幂等，可重复跑）。

## AI 操作矩阵（权限边界，硬规则）

| 操作 | 权限 |
|------|------|
| 读台账 / 读任意文件 | ✅ 自主 |
| 修改项目/应用信息、登记新条目、追加 WORKLOG | ✅ 自主（写回必须署名 operator） |
| 项目状态降级 archived（仅台账字段） | ✅ 自主 |
| **物理归档 / 删除 / 移动 / 重命名任何文件** | ⛔ 未经老板逐条确认，禁止 |
| **卸载 / 移动任何应用** | ⛔ 禁止（只能提醒） |
| **启动 / 运行本地应用（`os.startfile`）** | ⛔ 仅老板在看板点「启动应用」触发；AI 不得代为启动任何程序 |

物理操作固定流程：出清单 → 老板确认 → ≤10 个/批 → 同盘移 `_archive/` → 留备份记录。

## 禁区（扫描与操作永不进入）

`C:\` 写入、微信数据目录、`E:\play`、WSL vhdx 内部、`~/.workbuddy/binaries`。
大数据（free-stockdb 18GB、qlib 数据）只登记路径元数据，永不复制/移动。

## registry.json 字段速查

- projects: `id name description category(quant|tool|doc|data|infra) para(project|area|resource|archive)
  status(active|warm|cold|archived) stage progress(0-100|null) paths{root,data[],wsl[]}
  platform[] entry_points[] data_deps[] docs[] last_activity health(ok|stale|broken) notes
  kind(program|project) parent(L1 id 或 null) tasks[]{id,title,detail,acceptance,inputs,outputs,batch,status,updated,prompt}
  goals[]{id,text,done} progress_log[]{date,text} files[]{path,note} params[]{name,value,updated}
  ai_logs[]{name,path,date,note} dev_logs[]{date,text}
  decisions[]{id,date,text,note,status,updated,revoked_on}
  relations[]{id,from,to,type,note} integration(str)`
  - **层级**：`kind="program"` = L1 超大项目（`parent` 为 null）；
    `kind="project"` + `parent=<某 L1 id>` = 归属该超大项目的 L2 小项目；
    `kind="project"` + `parent=null` = **独立小项目**（合法、常见的形态，看板单列一区展示）。
    `parent` 指向不存在的 id 时会被当作独立小项目处理（属于脏数据，发现后应修正）。
  - **进度规则**：`tasks` 非空时 `progress` 由任务自动重算（= 已完成任务数 ÷ 任务总数 × 100）；
    `tasks` 为空但 `goals` 非空时按目标重算；两者都为空时由人工填写。
  - `progress_log` 为该项目的"主要进展"流水（一行一条，带日期），**动态更新记录**放这里，
    参数/状态变化也写进来（例：`- 2026-09-10 木板厚度 15→18mm；最高速度 2.8→3.4 m/s`）。
  - `files[]` 为"用到的文件"清单（`path` 绝对路径 + `note` 用途），详情页以圆点标示文件是否存在（绿=存在 / 橙=缺失）。
  - `params[]` 为"关键参数"当前值快照（`name` 参数名 / `value` 当前值 / `updated` 更新日期）。
  - `ai_logs[]` 为"日志信息"——**AI 生成的日志文件清单**（`name` 名称 / `path` 地址 / `date` 日期 / `note` 备注）。
    AI 可自主往本栏目追加（把跑出来的 log 文件按 名称+地址 登记进来）。
  - `dev_logs[]` 为"我的日志"——**仅老板本人可写**（详情页标"仅本人可写"）。
    ⛔ **AI 严禁向 `dev_logs` 写入、修改或删除任何条目**（只允许读取/展示）。AI 需要留痕的内容一律写 `ai_logs` 或 `progress_log`。
    条目形状：`{date, text, file_name, file_path}`
    - `file_path` 为空 = 纯文字日志；非空 = **文件日志**（内容体在文件里，台账只记文件名 + 路径）。
    - 长文（>300 字且无文件）在看板上**自动折叠**为前 120 字 + 「展开全文」，
      并有「存为文件」按钮（把全文写进 `H:\github\pm-hub\devlogs\<项目id>\<时间戳>.md` 后改为文件链接）。
    - 文件条目有「打开」（系统默认程序打开）与「目录」（资源管理器定位）按钮——
      **仅老板点击触发，AI 不得代为打开任何文件**（同"启动应用"规则）。
    - 「记录长文 / 已有文件」表单：填**路径**即只记录不复制；只贴**长文**则自动落盘成 md。
  - `decisions[]` 为"**结论与裁决**"——**当前生效的口径**（`status="active"`），AI 动手前必读；
    老板可在看板直接添加/改/推翻（`status` 置 `revoked`）/删除。详见上文专节。
    这是**唯一能撤销 AI 认知的地方**：结论变了就在这改，不要写"忘记 XX"式补丁。
  - `relations[]` 为"**小项目关系（整合）**"——仅 L1 超大项目使用，描述**下辖小项目之间怎么连接**：
    `{id, from, to, type(数据供给|接口调用|顺序依赖（前者须先完成）|共享配置|产出汇入|其他), note}`；
    `from`/`to` 是**小项目的 id**。看板会把它画成连线图（按入度拓扑排序，数据源排最前）。
  - `integration` 为**整合说明**（一段文字）：这几个小项目如何构成一个大工程、数据怎么流、先后顺序。
    AI 接手 L1 相关工作时先读它，别只看单个小项目。

### L1 超大项目页有哪些栏目（2026-10-08 起与 L2 对齐）

L1 详情页 = 头部卡 → **战略目标** → **小项目关系（整合）**（连线图 + 关系清单 + 整合说明）
→ **小项目（第二级）** → 本超大项目全部任务 → **结论与裁决** → 主要进展 → 关键参数 →
用到的文件 → 日志信息（AI） → 我的日志（仅老板） → 新建小项目。

⇒ **AI 对 L1 也有同样的留痕义务**：超大项目层面的进展写 `progress_log`、日志文件写 `ai_logs`、
口径写 `decisions`、用到的文件写 `files`——不要只写在小项目里。
- apps: `id name purpose category(ai|quant|dev|browser|media|system|office|game|security|comm|download|finance|input|tool|other)
  path exe version usage(daily|often|rare|unused|unknown) source(manual|startmenu|registry|winget|scan)
  desc_confirmed related_projects[]`
  - 类别含义：`security` 安全杀毒 · `comm` 通讯/会议/社交 · `download` 网盘/下载/云同步 · `finance` 证券金融 ·
    `input` 输入法 · `office` 办公 · `media` 音视频/内容 · `game` 游戏 · `browser` 浏览器 · `dev` 开发 ·
    `ai` AI 工具 · `system` 系统组件 · `tool` 工具 · `other` 其他/辅助入口。
  - 登记或修正应用时，请选**最贴近的类别**，不要一律丢进 `tool`；「卸载 X」这类条目归 `other` 并在用途注明"非独立软件"。
- locations: `id path purpose kind(data|output|doc|model|cache) size_note`
