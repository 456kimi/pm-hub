#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PM-Hub 任务交接包（handoff）：任务落成目录 → AI 在对话窗口执行 → 结果回收校验。

设计前提（V1.1 方案，2026-11-10）：
  - **不调用任何模型 API**。用户把任务包目录交给 ZCode / WorkBuddy 的对话框，
    由已购买的套餐执行；AI 完成后把 RESULT.md 与 EVIDENCE.json 写回同一目录。
  - 本模块只做「生成 / 校验 / 归档」，**绝不执行** AI 在 EVIDENCE 里写下的任何命令。
  - **不改 registry.json**。导入只产出校验报告；是否接受任务、是否写台账，
    由用户在台账里决定（走 pm_registry.py 的安全写入协议）。

目录布局（本地，由 .gitignore 排除）：

    .pmhub/handoffs/<handoff_id>/
      TASK.md          任务正文、授权范围、验收标准      （PM-Hub 生成）
      CONTEXT.md       项目目标、现行决策、非目标、数据范围（PM-Hub 生成）
      MANIFEST.json    机器可读的授权与校验基准          （PM-Hub 生成）
      RESULT.md        执行报告：做了什么 / 为什么 / 剩余问题（AI 写回）
      EVIDENCE.json    结构化证据：改动文件、测试、风险   （AI 写回）
      VALIDATION.json  导入时的校验结论                  （PM-Hub 生成）

命令行：
    python pm_handoff.py list
    python pm_handoff.py export --project <L2 项目 id> --task <任务 id>
    python pm_handoff.py validate --dir .pmhub/handoffs/<handoff_id>
    python pm_handoff.py import   --dir .pmhub/handoffs/<handoff_id>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDOFF_DIRNAME = ".pmhub"
SCHEMA_VERSION = "1"
DEFAULT_OPERATOR = "PM-Hub"

# 盘符绝对路径（抽取用）：C:\a\b、D:/a/b
WIN_PATH = re.compile(r"[A-Za-z]:[\\/][^\s，。；、）)\]】\"'|?*<>]*")
# EVIDENCE 里绝不允许声称改过的东西（硬禁止）
HARD_FORBIDDEN_FILES = {"registry.json", "registry.json.lock"}
# 允许的 EVIDENCE 状态
ALLOWED_STATUS = {"ready_for_review", "blocked", "failed", "partial"}
# RESULT.md 的实质内容下限（字符）。低于此值视为敷衍，不是字数考核：
# 中文一句话就能交代清楚「改了什么 + 测了什么」，20 字足够；空壳/「已完成」四字不够。
MIN_RESULT_CHARS = 20


# ---------------------------------------------------------------- 基础工具

def handoff_root(base: Path | None = None) -> Path:
    """交接包根目录，默认 H:\\github\\pm-hub\\.pmhub\\handoffs。"""
    return Path(base) if base else (ROOT / HANDOFF_DIRNAME / "handoffs")


def _now(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return datetime.now().strftime(fmt)


def active_decisions(obj: dict | None) -> list[dict]:
    """取现行决策（status=active）。

    这是全项目唯一的过滤口径，与 dashboard.task_pack_text、AGENTS.md 一致。
    缺 status 字段的历史数据按 active 处理（老数据无 status 即视为生效）。
    """
    items = (obj or {}).get("decisions") or []
    return [d for d in items if isinstance(d, dict) and d.get("status", "active") == "active"]


def revoked_decisions(obj: dict | None) -> list[dict]:
    """取已推翻的决策，仅供本地核对，不进任何对外导出。"""
    items = (obj or {}).get("decisions") or []
    return [d for d in items if isinstance(d, dict) and d.get("status") == "revoked"]


def _fmt_decisions(items: list[dict]) -> list[str]:
    out = []
    for d in items:
        line = "    - [%s] %s" % (d.get("date", ""), d.get("text", ""))
        if d.get("note"):
            line += "（依据：%s）" % d["note"]
        out.append(line)
    return out


def extract_paths(*texts) -> list[str]:
    """从自由文本里抽出盘符绝对路径，去重保序。"""
    seen, out = set(), []
    for t in texts:
        if not isinstance(t, str):
            continue
        for m in WIN_PATH.findall(t):
            key = os.path.normcase(m.rstrip("\\/"))
            if key not in seen:
                seen.add(key)
                out.append(m.rstrip("\\/"))
    return out


def is_within(path: str, roots: list[str]) -> bool:
    """判断 path 是否落在任一 roots 之内（Windows 大小写不敏感、正反斜杠等价）。"""
    p = os.path.normcase(os.path.abspath(os.path.normpath(path)))
    for r in roots:
        if not r:
            continue
        rr = os.path.normcase(os.path.abspath(os.path.normpath(r)))
        if p == rr or p.startswith(rr + os.sep):
            return True
    return False


# ---------------------------------------------------------------- 渲染

def render_task_brief(prog, proj, task, name_map=None) -> str:
    """把一条 L3 任务渲染成交付 AI 的完整任务包正文。

    输出与看板原有的「AI 任务指令」保持一致，另外补两处：
      - 超大项目（L1）的现行决策（原版只带 L2 的，而 L1 的口径同样约束任务）
      - 完成后的写回要求（仅在交接包模式下由 TASK.md 拼接，此处不写路径）

    name_map: {project_id: name}，用于渲染小项目关系；缺省时退回用 id。
    """
    name_map = name_map or {}
    root = (proj.get("paths") or {}).get("root") or "（待补）"
    deps = "、".join(proj.get("data_deps") or []) or "无"
    L = []
    L.append("【任务包】%s / %s" % (proj.get("name", ""), task.get("title", "")))
    L.append("")
    L.append("一、背景（先读，别跳）")
    if prog:
        L.append("- 所属超大项目：%s —— %s" % (prog.get("name", ""), prog.get("description", "")))
        if prog.get("notes"):
            L.append("- 超大项目约束：%s" % prog["notes"])
        if prog.get("integration"):
            L.append("- 该超大项目的整合说明（本小项目在其中的位置）：%s" % prog["integration"])
        rels = prog.get("relations") or []
        if rels:
            L.append("- 小项目之间的连接关系：")
            for r in rels:
                L.append("    · %s ──%s──▶ %s%s" % (
                    name_map.get(r.get("from"), r.get("from", "?")), r.get("type", ""),
                    name_map.get(r.get("to"), r.get("to", "?")),
                    ("（%s）" % r["note"]) if r.get("note") else ""))
    L.append("- 小项目：%s —— %s" % (proj.get("name", ""), proj.get("description", "")))
    L.append("- 项目阶段：%s" % (proj.get("stage") or "—"))
    L.append("- 项目根目录：%s" % root)
    L.append("- 数据依赖：%s" % deps)
    if proj.get("notes"):
        L.append("- 项目备注：%s" % proj["notes"])

    prog_decs = active_decisions(prog) if prog else []
    own_decs = active_decisions(proj)
    if prog_decs:
        L.append("")
        L.append("- 超大项目**现行结论（同样必须遵守）**：")
        L.extend(_fmt_decisions(prog_decs))
    if own_decs:
        L.append("")
        L.append("- 本项目**现行结论（必须遵守，不得违反）**：")
        L.extend(_fmt_decisions(own_decs))
    if not prog_decs and not own_decs:
        L.append("")
        L.append("- 本项目暂无现行结论；若你的工作产生了新的口径，请在收尾时用「结论与裁决」写入台账。")

    L.append("")
    L.append("二、本任务（编号 %s%s）" % (task.get("id", ""),
                                     ("，批次 " + task["batch"]) if task.get("batch") else ""))
    L.append("- 目标：%s" % task.get("title", ""))
    if task.get("detail"):
        L.append("- 说明：%s" % task["detail"])
    L.append("- 输入（动手前必须读）：%s" % (task.get("inputs") or "见项目根目录与 WORKLOG.md"))
    L.append("- 交付物：%s" % (task.get("outputs") or "（未指定，请先给出方案再执行）"))
    L.append("- 验收标准：%s" % (task.get("acceptance") or "（未指定，请先向我确认验收口径）"))
    L.append("")
    L.append("三、执行要求")
    L.append("1. 先读上述输入与项目 WORKLOG.md，用三句话复述你的理解，再动手。")
    L.append("2. 产物写明确路径，H:/G 盘可以，禁止写 C 盘；完成后贴实际命令输出或文件清单作为证据。")
    L.append("3. 不编造未验证的数据与结论；不确定的标注「待确认」并给出验证方法。")
    L.append("4. 严格限定在本任务范围内；发现范围外的问题只记录到「发现但未处理」，不要顺手改。")
    L.append("5. 结束后按 PM-Hub 的 AGENTS.md 写入协议，通过统一入口登记 ai_logs / progress_log 并更新任务状态；不要直接覆盖 registry.json。")
    L.append("6. 若本次工作产生了**新的口径 / 否决了旧做法**，写进台账的 `decisions[]`（现行结论），"
             "不要只写在自己的长期记忆里——那不可撤销。")
    return "\n".join(L)


def render_task_md(manifest: dict, prog, proj, task, name_map=None) -> str:
    """TASK.md：任务正文 + 授权边界 + 写回要求。"""
    body = render_task_brief(prog, proj, task, name_map)
    roots = manifest.get("allowed_roots") or []
    forbid = manifest.get("forbidden") or []
    L = ["# 交接任务 %s" % manifest["handoff_id"], ""]
    L.append("> 本目录是 PM-Hub 生成的任务交接包。你是执行方，不是需求方：")
    L.append("> 只做下面这一件事，不要顺手扩展。执行完把 `RESULT.md` 和 `EVIDENCE.json` 写回本目录。")
    L.append("")
    L.append("- 任务 ID：`%s` ｜ 小项目：`%s` ｜ 超大项目：`%s`"
             % (manifest["task_id"], manifest["project_id"], manifest.get("program_id") or "—"))
    L.append("- 生成时间：%s ｜ 生成方：%s" % (manifest["created"], manifest.get("operator", "")))
    L.append("- 交接包目录：`%s`" % manifest["pack_dir"])
    L.append("")
    L.append(body)
    L.append("")
    L.append("四、授权范围（MANIFEST.json 同内容，越界即停）")
    if roots:
        L.append("- 允许读写的根目录：")
        for r in roots:
            L.append("    - `%s`" % r)
    else:
        L.append("- 允许范围：**未限定**（台账里该项目没有登记根目录）→ 动手前先向我确认范围，不要自行扩大。")
    L.append("- 明确禁止：")
    for f in forbid:
        L.append("    - %s" % f)
    L.append("")
    L.append("五、完成后必须写回（缺一不可）")
    L.append("1. `%s/RESULT.md`：做了什么、为什么这么做、改了哪些文件、还剩什么问题。" % manifest["handoff_id"])
    L.append("2. `%s/EVIDENCE.json`：按目录内模板填写，`task_id` 必须写 `%s`。"
             % (manifest["handoff_id"], manifest["task_id"]))
    L.append("3. 测试只写**真实跑过的**；没跑就写 `未运行` 并说明原因。不要自称通过。")
    L.append("")
    L.append("> 写回后不要宣称任务已完成 —— 验收由 PM-Hub 校验 + 用户确认，不由执行方自判。")
    return "\n".join(L)


def render_context_md(manifest: dict, prog, proj) -> str:
    """CONTEXT.md：项目目标、现行决策、非目标、数据范围。换会话换软件都能接手。"""
    L = ["# 项目上下文 %s" % (proj.get("name") or manifest["project_id"]), ""]
    L.append("> 本文件是任务开始时的只读快照。正式目标与正式决定以本地 `registry.json` 为准；")
    L.append("> 你在执行中**不能**修改正式目标或把建议写成正式决定。")
    L.append("")
    L.append("## 项目")
    L.append("")
    L.append("- 小项目：%s（`%s`）" % (proj.get("name", ""), proj.get("id", "")))
    if prog:
        L.append("- 所属超大项目：%s（`%s`）" % (prog.get("name", ""), prog.get("id", "")))
        if prog.get("description"):
            L.append("- 超大项目说明：%s" % prog["description"])
    L.append("- 阶段：%s" % (proj.get("stage") or "—"))
    L.append("- 根目录：`%s`" % ((proj.get("paths") or {}).get("root") or "（待补）"))
    if proj.get("description"):
        L.append("- 说明：%s" % proj["description"])
    L.append("")

    goals = [g for g in (proj.get("goals") or []) if isinstance(g, dict)]
    if goals:
        L.append("## 目标（未完成项才是本次工作的方向）")
        L.append("")
        for g in goals:
            L.append("- [%s] %s" % ("x" if g.get("done") else " ", g.get("text", "")))
        L.append("")

    if prog and (prog.get("goals") or []):
        L.append("## 超大项目目标")
        L.append("")
        for g in prog["goals"]:
            if isinstance(g, dict):
                L.append("- [%s] %s" % ("x" if g.get("done") else " ", g.get("text", "")))
        L.append("")

    L.append("## 现行决策（必须遵守）")
    L.append("")
    prog_decs, own_decs = active_decisions(prog), active_decisions(proj)
    if prog_decs:
        L.append("**超大项目层面：**")
        L.append("")
        L.extend(_fmt_decisions(prog_decs))
        L.append("")
    if own_decs:
        L.append("**本项目层面：**")
        L.append("")
        L.extend(_fmt_decisions(own_decs))
        L.append("")
    if not prog_decs and not own_decs:
        L.append("（无现行决策）")
        L.append("")

    deps = proj.get("data_deps") or []
    if deps:
        L.append("## 数据范围")
        L.append("")
        for d in deps:
            L.append("- %s" % d)
        L.append("")

    if proj.get("notes"):
        L.append("## 备注")
        L.append("")
        L.append(str(proj["notes"]))
        L.append("")

    L.append("## 非目标（本次不做）")
    L.append("")
    L.append("- 不重构与任务无关的模块；不做顺手优化。")
    L.append("- 不修改 `registry.json`、不把建议写成正式决定。")
    L.append("- 不推送 GitHub、不合并 PR、不发布部署、不产生额外付费调用。")
    return "\n".join(L)


def build_manifest(manifest_id: str, prog, proj, task, operator: str, pack_dir: Path) -> dict:
    """MANIFEST.json：机器可读的授权与校验基准。"""
    p = (proj.get("paths") or {})
    roots: list[str] = []
    if p.get("root"):
        roots.append(str(p["root"]))
    # 任务输入里出现的路径，其所在目录一并授权（AI 通常要就地改写这些文件）
    for one in extract_paths(task.get("inputs") or "", task.get("outputs") or ""):
        parent = os.path.dirname(one.rstrip("\\/"))
        if parent and not any(is_within(parent, [r]) for r in roots):
            roots.append(parent)
    forbidden = [
        "修改或覆盖 registry.json（正式台账只能走 pm_registry.py）",
        "把建议写成正式 decision，或改动项目长期目标",
        "推送 GitHub / 合并 PR / 发布部署",
        "删除、移动、重命名授权范围之外的文件",
        "把本机台账、私人日志、密钥上传到任何云端或公开仓库",
        "在授权范围之外新建目录",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "handoff_id": manifest_id,
        "task_id": task.get("id", ""),
        "task_title": task.get("title", ""),
        "project_id": proj.get("id", ""),
        "project_name": proj.get("name", ""),
        "program_id": (prog or {}).get("id", ""),
        "program_name": (prog or {}).get("name", ""),
        "created": _now(),
        "operator": operator,
        "pack_dir": str(pack_dir),
        "allowed_roots": roots,
        "forbidden": forbidden,
        "acceptance": task.get("acceptance") or "",
        "inputs": task.get("inputs") or "",
        "outputs": task.get("outputs") or "",
        "result_files": {"result": "RESULT.md", "evidence": "EVIDENCE.json"},
        "next_state": "handed_off",
    }


def evidence_template(manifest: dict) -> dict:
    """EVIDENCE.json 模板。留空字段由执行方填真值，不要照抄占位符。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "handoff_id": manifest["handoff_id"],
        "task_id": manifest["task_id"],
        "status": "ready_for_review",
        "agent_app": "",
        "model": "",
        "files_changed": [],
        "tests": [
            {
                "command": "",
                "outcome": "未运行",
                "notes": "",
            }
        ],
        "unresolved": [],
        "requires_approval": False,
        "notes": "",
        "_comment": "agent_app 填软件名（ZCode / WorkBuddy），model 填真实模型名；"
                    "files_changed 用绝对路径或相对项目根目录的路径；"
                    "tests[].outcome 只能是 passed / failed / 未运行。"
                    "自称 passed 不等于通过，PM-Hub 会另做范围与格式校验。",
    }


# ---------------------------------------------------------------- 生成

def _next_handoff_id(proj_id: str, task_id: str, root: Path) -> str:
    """H-YYYYMMDD-<项目>-<任务>，同日同任务重复导出则追加序号。"""
    stem = "H-%s-%s-%s" % (datetime.now().strftime("%Y%m%d"), proj_id, task_id)
    if not (root / stem).exists():
        return stem
    n = 2
    while (root / ("%s-%d" % (stem, n))).exists():
        n += 1
    return "%s-%d" % (stem, n)


def export_pack(proj: dict, task: dict, prog: dict | None = None,
                out_root: Path | None = None, operator: str = DEFAULT_OPERATOR,
                name_map: dict | None = None) -> dict:
    """生成一个交接包目录，返回 {handoff_id, pack_dir, files, manifest}。

    纯文件操作，不联网、不调用模型、不碰台账。
    """
    root = handoff_root(out_root)
    root.mkdir(parents=True, exist_ok=True)
    hid = _next_handoff_id(proj.get("id", "x"), task.get("id", "x"), root)
    pack = root / hid
    pack.mkdir(parents=True, exist_ok=False)

    manifest = build_manifest(hid, prog, proj, task, operator, pack)
    (pack / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (pack / "TASK.md").write_text(
        render_task_md(manifest, prog, proj, task, name_map), encoding="utf-8")
    (pack / "CONTEXT.md").write_text(
        render_context_md(manifest, prog, proj), encoding="utf-8")
    (pack / "EVIDENCE.template.json").write_text(
        json.dumps(evidence_template(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    (pack / "HANDOFF.md").write_text(
        render_handoff_card(manifest), encoding="utf-8")

    return {
        "handoff_id": hid,
        "pack_dir": str(pack),
        "files": sorted(p.name for p in pack.iterdir()),
        "manifest": manifest,
    }


def render_handoff_card(manifest: dict) -> str:
    """HANDOFF.md：给用户复制到对话框的那一段（短，不含长篇背景）。"""
    L = ["# 接手指令（复制下面整段，贴进 ZCode / WorkBuddy 对话框）", ""]
    L.append("```text")
    L.append("你现在不是来重新制定项目方向，而是执行 PM-Hub 中已分配的一项任务。")
    L.append("")
    L.append("任务包目录：%s" % manifest["pack_dir"])
    L.append("请依次读取该目录下的 TASK.md、CONTEXT.md、MANIFEST.json，然后按 TASK.md 执行。")
    L.append("")
    L.append("规则：")
    L.append("1. 先用三句话复述项目目标、本任务范围与验收条件，再动手。")
    L.append("2. 只在 MANIFEST.json 的 allowed_roots 内操作，不因为发现别的问题就扩展需求。")
    L.append("3. 优先用项目已有技术栈；遇问题先查本项目源码与测试，再查公开资料并记录链接。")
    L.append("4. 测试只报真实结果，没跑的写「未运行」。")
    L.append("5. 要改长期目标 / 正式决定 / 架构 / 数据格式 / 加依赖 / 删移文件 / 危险命令时，停下来先问我。")
    L.append("6. 不直接覆盖 registry.json，不 push，不合并 PR。")
    L.append("7. 完成后把 RESULT.md 与 EVIDENCE.json 写回本任务包目录，然后在对话框只回一段简短摘要。")
    L.append("```")
    L.append("")
    L.append("> 该指令不依赖任何模型 API，用的是你在智能体软件里已购买的套餐。")
    return "\n".join(L)


# ---------------------------------------------------------------- 校验 / 导入

def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pack(pack_dir: str | Path) -> dict:
    """校验一个交接包的结果文件。返回 {ok, issues, warnings, evidence, manifest}。

    issues   = 阻断性问题（必须返工）
    warnings = 可接受但需人工看一眼
    """
    pack = Path(pack_dir)
    issues: list[str] = []
    warnings: list[str] = []
    result: dict = {"ok": False, "issues": issues, "warnings": warnings,
                    "pack_dir": str(pack), "handoff_id": pack.name,
                    "manifest": None, "evidence": None, "validated_at": _now()}

    if not pack.is_dir():
        issues.append("任务包目录不存在：%s" % pack)
        return result

    manifest = None
    mf = pack / "MANIFEST.json"
    if not mf.exists():
        issues.append("缺少 MANIFEST.json —— 这不是 PM-Hub 生成的交接包")
    else:
        try:
            manifest = _read_json(mf)
            result["manifest"] = manifest
        except Exception as exc:
            issues.append("MANIFEST.json 无法解析：%s" % exc)

    res = pack / "RESULT.md"
    if not res.exists():
        issues.append("缺少 RESULT.md（执行报告）")
    elif len(res.read_text(encoding="utf-8", errors="replace").strip()) < MIN_RESULT_CHARS:
        issues.append("RESULT.md 内容过短（<%d 字）—— 至少写清做了什么、改了哪些文件、还剩什么问题"
                      % MIN_RESULT_CHARS)

    ev_path = pack / "EVIDENCE.json"
    if not ev_path.exists():
        issues.append("缺少 EVIDENCE.json（结构化证据；可参考 EVIDENCE.template.json）")
        return result
    try:
        ev = _read_json(ev_path)
        result["evidence"] = ev
    except Exception as exc:
        issues.append("EVIDENCE.json 无法解析：%s" % exc)
        return result

    # --- 逐项核对
    if str(ev.get("schema_version")) != SCHEMA_VERSION:
        issues.append("EVIDENCE.schema_version 应为 %r，实为 %r"
                      % (SCHEMA_VERSION, ev.get("schema_version")))
    if manifest:
        if ev.get("handoff_id") and ev["handoff_id"] != manifest.get("handoff_id"):
            issues.append("handoff_id 不匹配：证据写 %r，任务包是 %r"
                          % (ev["handoff_id"], manifest.get("handoff_id")))
        if str(ev.get("task_id")) != str(manifest.get("task_id")):
            issues.append("task_id 不匹配：证据写 %r，任务包是 %r"
                          % (ev.get("task_id"), manifest.get("task_id")))

    status = ev.get("status")
    if status not in ALLOWED_STATUS:
        issues.append("status 非法：%r（应为 %s）" % (status, " / ".join(sorted(ALLOWED_STATUS))))

    if not str(ev.get("model") or "").strip():
        warnings.append("EVIDENCE.model 为空 —— 无法回溯是哪个模型执行的")
    if not str(ev.get("agent_app") or "").strip():
        warnings.append("EVIDENCE.agent_app 为空 —— 建议填 ZCode / WorkBuddy")

    files_changed = ev.get("files_changed")
    if not isinstance(files_changed, list):
        issues.append("files_changed 必须是数组")
        files_changed = []
    base_root = ((manifest or {}).get("allowed_roots") or [None])[0]
    for f in files_changed:
        if not isinstance(f, str) or not f.strip():
            warnings.append("files_changed 里有空或非字符串项：%r" % (f,))
            continue
        name = os.path.basename(f.rstrip("\\/")).lower()
        if name in HARD_FORBIDDEN_FILES:
            issues.append("声称改过正式台账 %s —— 台账只能走 pm_registry.py" % f)
            continue
        roots = (manifest or {}).get("allowed_roots") or []
        target = f if os.path.isabs(f) else (
            os.path.join(base_root, f) if base_root else f)
        if roots and os.path.isabs(target) and not is_within(target, roots):
            issues.append("改动超出授权范围：%s" % f)
        elif not roots and os.path.isabs(target):
            warnings.append("任务包未限定授权目录，改动 %s 需人工确认" % f)

    tests = ev.get("tests")
    if not isinstance(tests, list) or not tests:
        warnings.append("没有 tests 记录 —— 若确实无需测试，请在 RESULT.md 说明")
    else:
        for i, t in enumerate(tests, 1):
            if not isinstance(t, dict):
                issues.append("tests[%d] 不是对象" % i)
                continue
            outcome = str(t.get("outcome") or "").strip()
            if not str(t.get("command") or "").strip() and outcome not in ("未运行", "not_run"):
                warnings.append("tests[%d] 缺少 command" % i)
            if outcome in ("passed", "通过"):
                if not str(t.get("notes") or "").strip():
                    warnings.append("tests[%d] 自称 passed 但没有 notes/输出 —— "
                                    "不采信自称，需人工复核" % i)
            elif outcome not in ("failed", "未运行", "not_run", "failed_expected"):
                warnings.append("tests[%d].outcome 取值异常：%r" % (i, outcome))

    if ev.get("requires_approval"):
        warnings.append("执行方标记需要审批 —— 这条不能自动通过")

    result["ok"] = not issues
    return result


def import_result(pack_dir: str | Path, write_report: bool = True) -> dict:
    """导入一个交接包的结果：校验 + 落 VALIDATION.json。**不改台账**。"""
    report = validate_pack(pack_dir)
    if write_report:
        pack = Path(pack_dir)
        if pack.is_dir():
            target = pack / "VALIDATION.json"
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            report["report_path"] = str(target)
    return report


def list_packs(out_root: Path | None = None) -> list[dict]:
    """列出所有交接包及其状态（是否已写回结果）。"""
    root = handoff_root(out_root)
    if not root.is_dir():
        return []
    out = []
    for d in sorted(root.iterdir(), key=lambda x: x.name, reverse=True):
        if not d.is_dir():
            continue
        item = {
            "handoff_id": d.name,
            "pack_dir": str(d),
            "has_result": (d / "RESULT.md").exists(),
            "has_evidence": (d / "EVIDENCE.json").exists(),
            "validated": (d / "VALIDATION.json").exists(),
            "ok": None,
        }
        if item["validated"]:
            try:
                item["ok"] = bool(_read_json(d / "VALIDATION.json").get("ok"))
            except Exception:
                item["ok"] = None
        out.append(item)
    return out


# ---------------------------------------------------------------- CLI

def _find(projects: list[dict], pid: str):
    for p in projects:
        if p.get("id") == pid:
            return p
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PM-Hub 任务交接包（不调用任何模型 API）")
    ap.add_argument("--registry", help="台账路径，默认使用 PM-Hub 台账")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_exp = sub.add_parser("export", help="为一条任务生成交接包")
    p_exp.add_argument("--project", required=True, help="L2 小项目 id")
    p_exp.add_argument("--task", required=True, help="任务 id，例 t3")
    p_exp.add_argument("--operator", default=DEFAULT_OPERATOR)
    p_exp.add_argument("--out", help="交接包根目录，默认 .pmhub/handoffs")

    p_val = sub.add_parser("validate", help="只校验，不落报告")
    p_val.add_argument("--dir", required=True)
    p_imp = sub.add_parser("import", help="校验并写 VALIDATION.json")
    p_imp.add_argument("--dir", required=True)
    sub.add_parser("list", help="列出所有交接包")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        packs = list_packs()
        if not packs:
            print("还没有交接包。用 export 生成一个。")
            return 0
        for it in packs:
            mark = "已写回" if it["has_result"] and it["has_evidence"] else "待执行"
            verdict = {True: "校验通过", False: "校验未通过", None: "未校验"}[it["ok"]]
            print("%-32s %-8s %s" % (it["handoff_id"], mark, verdict))
        return 0

    if args.cmd in ("validate", "import"):
        rep = (import_result if args.cmd == "import" else validate_pack)(args.dir)
        print("包：%s" % rep["handoff_id"])
        print("结论：%s" % ("通过" if rep["ok"] else "未通过"))
        for it in rep["issues"]:
            print("  [阻断] " + it)
        for it in rep["warnings"]:
            print("  [注意] " + it)
        if rep.get("report_path"):
            print("报告：%s" % rep["report_path"])
        return 0 if rep["ok"] else 2

    # export
    from pm_registry import read_registry
    reg = read_registry(args.registry)
    projects = reg.get("projects") or []
    proj = _find(projects, args.project)
    if not proj:
        print("找不到项目 %r" % args.project)
        return 1
    task = next((t for t in (proj.get("tasks") or [])
                 if str(t.get("id")) == str(args.task)), None)
    if not task:
        print("项目 %s 下找不到任务 %r，现有任务：%s"
              % (args.project, args.task,
                 "、".join(str(t.get("id")) for t in (proj.get("tasks") or []))))
        return 1
    prog = _find(projects, proj.get("parent")) if proj.get("parent") else None
    name_map = {p["id"]: p.get("name", "") for p in projects if p.get("id")}
    info = export_pack(proj, task, prog, out_root=Path(args.out) if args.out else None,
                       operator=args.operator, name_map=name_map)
    print("交接包已生成：%s" % info["pack_dir"])
    print("文件：%s" % "、".join(info["files"]))
    print("把 %s\\HANDOFF.md 里那段指令贴进 ZCode / WorkBuddy 对话框即可。"
          % info["pack_dir"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
