# -*- coding: utf-8 -*-
"""PM-Hub 三级项目体系迁移（2026-09-17）。

目标：projects[] 从"扁平列表"升级为"三级体系"：
    L1 超大项目(kind=program) → L2 小项目(kind=project, parent=<L1 id>) → L3 任务(tasks[])

本脚本幂等：重复执行不会重复创建 program、不会覆盖已有 tasks/parent。
写回规范见 AGENTS.md：整文件读 → 内存改 → 整体写回 + 备份 + 回读校验。
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HUB = Path(__file__).resolve().parent
REG = HUB / "registry.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OPERATOR = "阿布(workbuddy)"

# ---------------------------------------------------------------- L1 超大项目
# 2026-09-18 调整：「本地工作台与工具链」「内容与知识库」不是单一工程，已解散
# （见 rebalance_hierarchy_20260918.py），其成员改为独立小项目 —— 重跑本脚本不再创建这两个 L1。
_DISSOLVED = {"prog-workbench", "prog-content"}
_PROGRAMS = [
    {
        "id": "prog-quant-live",
        "name": "A股量化交易体系（实盘链路）",
        "category": "quant",
        "status": "active",
        "stage": "多项目协同 · 数据链待修复",
        "description": "从行情数据到底层执行的完整链路：数据底座 → 因子/选股 → 每日打分 → 模拟交易 → 盘中监控。四段各自独立成小项目，串联成一条可验证的生产线。",
        "notes": "L1 超大项目。链路顺序：free-stockdb（数据）→ qlib-alpha158（因子/选股）→ paper_sim（模拟盘）→ hawkeye（监控）。当前瓶颈：数据底座停更拖累全链。",
        "platform": ["workbuddy", "kimi-cli"],
        "data_deps": ["Sina/Tencent 免费行情接口"],
        "goals": [
            {"id": "g1", "text": "数据底座恢复日更（free-stockdb 引擎常驻，停更 ≤1 交易日）", "done": False},
            {"id": "g2", "text": "因子打分链路端到端可复现（数据→因子→打分→信号文件，一条命令跑通）", "done": False},
            {"id": "g3", "text": "模拟盘每日自动执行并留档（评分 + 交易逻辑 + 仓位计算可追溯）", "done": False},
            {"id": "g4", "text": "监控告警覆盖数据陈旧 / 因子失效 / 净值异常三类事件", "done": False},
        ],
        "progress_log": [
            {"date": "2026-09-17", "text": "建立 L1/L2/L3 三级体系，本超大项目下挂 4 个小项目。"},
        ],
    },
    {
        "id": "prog-quant-research",
        "name": "量化研究与 AI 因子挖掘",
        "category": "quant",
        "status": "active",
        "stage": "多项目并行",
        "description": "面向新因子的研究线：AI 自动挖因子（RD-Agent）+ 深度学习打分模型 + 基本面研究，产出经 OOS 验证后回流实盘链路。",
        "notes": "L1 超大项目。产出物必须有可交易口径的验证证据（naive IC 与可交易 IC 必须分开报告），否则不得回流 prog-quant-live。",
        "platform": ["workbuddy", "wsl2"],
        "data_deps": ["free-stockdb", "qlib 数据 H:\\Claw_backup\\etf_data\\qlib_data"],
        "goals": [
            {"id": "g1", "text": "资金动向线（RD-Agent）恢复运行并产出至少 1 个通过口径审计的因子", "done": False},
            {"id": "g2", "text": "daw-poc-gpu 因子去冗余完成，冗余因子集收敛到可用规模", "done": False},
            {"id": "g3", "text": "AI 挖掘因子完成 OOS 验证并整合进 paper_sim 打分模型", "done": False},
        ],
        "progress_log": [
            {"date": "2026-09-17", "text": "建立三级体系，本超大项目下挂 3 条研究线。"},
        ],
    },
    {
        "id": "prog-workbench",
        "name": "本地工作台与工具链",
        "category": "tool",
        "status": "active",
        "stage": "持续维护",
        "description": "支撑所有项目的本地基础设施：资产台账与看板（PM-Hub）、技能库、以及把重复劳动工具化的各类自建流水线。",
        "notes": "L1 超大项目。原则：一切工具产物写 H:/G 盘，不写 C 盘；能复用就沉淀成 skill 而不是脚本堆。",
        "platform": ["workbuddy"],
        "data_deps": [],
        "goals": [
            {"id": "g1", "text": "PM-Hub 成为跨 AI 平台的单一真相源（三级体系 + 任务可交付 AI）", "done": False},
            {"id": "g2", "text": "重复性工作流沉淀为 skill（有触发条件 + 可执行步骤）", "done": False},
            {"id": "g3", "text": "自建工具覆盖高频场景并达到可日常使用状态", "done": False},
        ],
        "progress_log": [
            {"date": "2026-09-17", "text": "建立三级体系；启动 PM-Hub 项目总览层级化改造。"},
        ],
    },
    {
        "id": "prog-content",
        "name": "内容与知识库",
        "category": "doc",
        "status": "warm",
        "stage": "半自动化",
        "description": "外部信息的自动采集与归纳：GitHub Trending 日报、IMA 知识库与微信投资群内容的批量导出与结构化归档。",
        "notes": "L1 超大项目。产出统一落 H:\\github\\ 下（github-trending-reports / ima-research-export）。",
        "platform": ["workbuddy"],
        "data_deps": ["IMA 知识库", "微信电脑版"],
        "goals": [
            {"id": "g1", "text": "GitHub Trending 日报稳定日更且无人值守", "done": True},
            {"id": "g2", "text": "IMA/微信内容导出半自动化，归档有统一目录规范", "done": False},
        ],
        "progress_log": [
            {"date": "2026-09-17", "text": "建立三级体系。"},
        ],
    },
]

# ---------------------------------------------------------------- L2 归属映射
PARENT_MAP = {
    "free-stockdb": "prog-quant-live",
    "qlib-alpha158": "prog-quant-live",
    "paper_sim": "prog-quant-live",
    "hawkeye": "prog-quant-live",
    "fin-quant": "prog-quant-research",
    "daw-poc-gpu": "prog-quant-research",
    "finq": "prog-quant-research",
}
# 以下为**独立小项目**（parent 留空，与 L1 平级）——2026-09-18 起不再归属任何超大项目：
# pm-hub / screen-translate-pipeline / scientific-skills / github-trending / ima-export
PROGRAMS = [p for p in _PROGRAMS if p["id"] not in _DISSOLVED]

# ------------------------------------------------- L3 示范任务（仅 pm-hub 本体）
PMHUB_TASKS = [
    {
        "id": "t1", "title": "建立三级数据模型（kind / parent / tasks）",
        "status": "done", "batch": "B1",
        "detail": "projects[] 增加 kind（program|project）、parent（父 id）、tasks[]（第三级任务，含验收/输入/输出/AI 指令），并保持对老条目的向后兼容。",
        "acceptance": "registry.json 中所有条目都有 kind/parent/tasks 字段；老项目不报错。",
        "inputs": "H:\\github\\pm-hub\\registry.json；H:\\github\\pm-hub\\AGENTS.md",
        "outputs": "migrate_hierarchy_20260917.py（迁移脚本，幂等）",
        "updated": "2026-09-17",
    },
    {
        "id": "t2", "title": "台账迁移：登记 4 个 L1 并把 12 个项目归位",
        "status": "done", "batch": "B1",
        "detail": "新增 prog-quant-live / prog-quant-research / prog-workbench / prog-content 四个超大项目，现有 12 个项目全部挂到对应 L1 之下。",
        "acceptance": "每个 L2 项目的 parent 指向存在的 L1 id；无孤儿项目；备份与回读校验记录在案。",
        "inputs": "registry.bak_20260917_prehierachy.json",
        "outputs": "更新后的 registry.json（含 4 L1 + 12 L2）",
        "updated": "2026-09-17",
    },
    {
        "id": "t3", "title": "看板总览改造为三级下钻（L1 卡 → L2 列表 → L3 任务）",
        "status": "doing", "batch": "B1",
        "detail": "项目总览页默认展示 L1 卡片；点进 L1 展示其下 L2 小项目；点进 L2 展示该项目详情与第三级任务清单（可勾选/改状态/看 AI 指令）。",
        "acceptance": "三级下钻全通，面包屑可回退；扁平视图仍可用；六页 AppTest 冒烟无异常。",
        "inputs": "H:\\github\\pm-hub\\dashboard.py",
        "outputs": "改造后的 dashboard.py",
        "updated": "2026-09-17",
    },
    {
        "id": "t4", "title": "任务包导出：一键生成可交付 AI 的完整指令",
        "status": "todo", "batch": "B2",
        "detail": "每条任务可复制/下载一份完整指令（项目背景 + 根目录 + 约束 + 任务目标 + 输入 + 交付物 + 验收标准 + 执行要求），按 batch 字段分批导出为 markdown 任务包。",
        "acceptance": "导出的 .md 落在 H:\\github\\pm-hub\\reports\\，内容含项目上下文与验收标准，可直接粘贴给 AI 执行。",
        "inputs": "registry.json 中 projects[].tasks[]",
        "outputs": "reports\\taskpack-<项目id>-<日期>.md",
        "updated": "2026-09-17",
    },
    {
        "id": "t5", "title": "AGENTS.md 补充三级体系契约",
        "status": "todo", "batch": "B2",
        "detail": "写清 L1/L2/L3 的定义、字段形状、AI 写任务的规范（必须带验收标准与输入输出）、以及 dev_logs 禁区重申。",
        "acceptance": "AGENTS.md 中有独立小节说明三级体系与任务字段；任意 AI 读后能正确登记任务。",
        "inputs": "H:\\github\\pm-hub\\AGENTS.md",
        "outputs": "更新后的 AGENTS.md",
        "updated": "2026-09-17",
    },
    {
        "id": "t6", "title": "静态页与冒烟回归",
        "status": "todo", "batch": "B2",
        "detail": "export_static.py 支持按 L1 分组展示 + L2 任务列表只读展示；改完跑六页 AppTest 冒烟与静态页导出。",
        "acceptance": "index.html 按超大项目分组渲染，L2 卡片含任务统计；AppTest 六页无 exception。",
        "inputs": "H:\\github\\pm-hub\\export_static.py；H:\\github\\pm-hub\\index.html",
        "outputs": "更新后的 export_static.py 与 index.html",
        "updated": "2026-09-17",
    },
]


def blank_program(p):
    """把 program 定义补成与 project 同构的完整条目。"""
    p = dict(p)
    p["kind"] = "program"
    p["parent"] = None
    p.setdefault("para", "program")
    p.setdefault("health", "ok")
    p.setdefault("entry_points", [])
    p.setdefault("docs", [])
    p.setdefault("files", [])
    p.setdefault("params", [])
    p.setdefault("ai_logs", [])
    p.setdefault("dev_logs", [])
    p.setdefault("tasks", [])
    p.setdefault("paths", {"root": "H:\\github\\pm-hub", "data": [], "wsl": []})
    p["last_activity"] = datetime.now().strftime("%Y-%m-%d")
    goals = p.get("goals") or []
    if goals:
        p["progress"] = round(sum(1 for g in goals if g.get("done")) * 100 / len(goals))
    return p


def main():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    projects = reg["projects"]
    by_id = {p["id"]: p for p in projects}

    shutil.copy2(REG, HUB / ("registry.bak_%s.json" % STAMP))

    created, linked, kept = [], [], []

    for prog in PROGRAMS:
        if prog["id"] in by_id:
            kept.append(prog["id"])
            continue
        p = blank_program(prog)
        projects.insert(0, p)
        by_id[p["id"]] = p
        created.append(p["id"])

    for pid, parent in PARENT_MAP.items():
        p = by_id.get(pid)
        if p is None:
            print("[warn] 项目不存在:", pid)
            continue
        p["kind"] = "project"
        if p.get("parent") is None:
            p["parent"] = parent
            linked.append(pid)
        elif p.get("parent") != parent:
            print("[warn] %s 已有 parent=%s，跳过（不覆盖）" % (pid, p.get("parent")))
        p.setdefault("tasks", [])

    # 兜底：任何既不是 program 也没 parent 的条目 → 视为未归类 L2
    for p in projects:
        p.setdefault("kind", "program" if p.get("para") == "program" else "project")
        p.setdefault("parent", None)
        p.setdefault("tasks", [])

    # pm-hub 示范任务
    hub = by_id.get("pm-hub")
    if hub is not None and not hub.get("tasks"):
        hub["tasks"] = [dict(t) for t in PMHUB_TASKS]
        print("已为 pm-hub 写入 %d 条示范任务" % len(hub["tasks"]))

    reg["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    reg["operator"] = OPERATOR
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REG)

    # ---- 回读校验 ----
    chk = json.loads(REG.read_text(encoding="utf-8"))
    ids = {p["id"] for p in chk["projects"]}
    bad = [p["id"] for p in chk["projects"]
           if p.get("parent") and p["parent"] not in ids]
    lv1 = [p["id"] for p in chk["projects"] if p.get("kind") == "program"]
    lv2 = [p["id"] for p in chk["projects"] if p.get("kind") == "project"]
    lv3 = sum(len(p.get("tasks") or []) for p in chk["projects"])
    print("新建 L1:", created or "无")
    print("已归位 L2:", len(linked))
    print("已存在 L1(跳过):", kept or "无")
    print("校验 → L1 %d / L2 %d / L3 任务 %d / parent 悬空 %s"
          % (len(lv1), len(lv2), lv3, bad or "无"))
    print("L1 清单:", lv1)
    assert not bad, "存在 parent 指向不存在的项目"
    return 0


if __name__ == "__main__":
    sys.exit(main())
