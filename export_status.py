#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 registry.json 导出超大项目（L1）状态文档。

用途：让协作者（含 AI）在不接触台账原始数据的前提下，理解每个超大项目的
目标、进度、任务与既有关键决策。

安全边界：
  - 只导出 kind=program 的项目及其直接子项目
  - 剔除 dev_logs（本人私有日志）与 paths（本机绝对路径）
  - 所有文本里的盘符绝对路径统一脱敏为 `…`
  - 不导出独立小项目（含公司/客户类项目）

用法：python export_status.py [-o PROJECT-STATUS.md]
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"

# 盘符绝对路径：C:\a\b\c  →  …
WIN_PATH = re.compile(r"[A-Za-z]:\\[^\s，。；、）)\]】\"']*")

STATUS_LABEL = {
    "active": "进行中",
    "warm": "待推进",
    "cold": "暂停",
    "done": "已完成",
    "paused": "搁置",
}
HEALTH_LABEL = {"ok": "正常", "warn": "预警", "bad": "异常", "risk": "风险"}
TASK_LABEL = {
    "todo": "待办",
    "doing": "进行中",
    "done": "已完成",
    "blocked": "受阻",
    "archived": "已归档",
}


def scrub(text) -> str:
    """抹掉盘符绝对路径，只留可读描述。支持 str / list / dict / None。"""
    if text is None:
        return ""
    if isinstance(text, str):
        return WIN_PATH.sub("…", text).strip()
    if isinstance(text, (list, tuple, set)):
        return "、".join(scrub(x) for x in text if x is not None and scrub(x) != "")
    if isinstance(text, dict):
        return "；".join(f"{k}={scrub(v)}" for k, v in text.items())
    return WIN_PATH.sub("…", str(text)).strip()


def label(mapping: dict, key: str) -> str:
    if not key:
        return "—"
    return f"{mapping.get(key, key)}"


def render_program(prog: dict, children: list[dict]) -> list[str]:
    out: list[str] = []
    out.append(f"## {prog['name']}")
    out.append("")
    out.append(
        f"- **状态**：{label(STATUS_LABEL, prog.get('status'))}"
        f" ｜ **阶段**：{scrub(prog.get('stage') or '—')}"
        f" ｜ **健康度**：{label(HEALTH_LABEL, prog.get('health'))}"
        f" ｜ **进度**：{prog.get('progress') if prog.get('progress') is not None else '—'}%"
    )
    if prog.get("last_activity"):
        out.append(f"- **最近活动**：{prog['last_activity']}")
    out.append("")
    if prog.get("description"):
        out.append(scrub(prog["description"]))
        out.append("")

    goals = prog.get("goals") or []
    if goals:
        out.append("### 目标")
        out.append("")
        for g in goals:
            mark = "x" if g.get("done") else " "
            out.append(f"- [{mark}] {scrub(g.get('text', ''))}")
        out.append("")

    if prog.get("integration"):
        out.append(f"**体系串联**：{scrub(prog['integration'])}")
        out.append("")

    params = prog.get("params") or []
    if params:
        out.append("### 关键参数")
        out.append("")
        out.append("| 参数 | 取值 | 更新 |")
        out.append("|------|------|------|")
        for prm in params:
            out.append(
                f"| {scrub(prm.get('name',''))} | {scrub(str(prm.get('value','')))} "
                f"| {prm.get('updated','')} |"
            )
        out.append("")

    decisions = prog.get("decisions") or []
    if decisions:
        out.append("### 已定决策")
        out.append("")
        for dec in decisions:
            date = dec.get("date", "")
            text = scrub(dec.get("text", ""))
            note = scrub(dec.get("note", "") or "")
            out.append(f"- **{date}** {text}" + (f"\n  - 依据：{note}" if note else ""))
        out.append("")

    plog = prog.get("progress_log") or []
    if plog:
        out.append("### 进展记录")
        out.append("")
        for entry in plog:
            if isinstance(entry, dict):
                date = entry.get("date", "")
                text = scrub(str(entry.get("text", "")))
                out.append(f"- **{date}** {text}")
            else:
                out.append(f"- {scrub(str(entry))}")
        out.append("")

    if children:
        out.append("### 子项目一览")
        out.append("")
        out.append("| 子项目 | 状态 | 进度 | 说明 |")
        out.append("|--------|------|------|------|")
        for c in children:
            desc = scrub(c.get("description", "") or "")
            if len(desc) > 60:
                desc = desc[:60] + "…"
            out.append(
                f"| `{c['id']}` {c['name']} | {label(STATUS_LABEL, c.get('status'))} "
                f"| {c.get('progress') if c.get('progress') is not None else '—'}% | {desc} |"
            )
        out.append("")

    for c in children:
        out.extend(render_sub(c))
    return out


def render_sub(proj: dict) -> list[str]:
    out: list[str] = []
    out.append(f"#### {proj['name']}（`{proj['id']}`）")
    out.append("")
    out.append(
        f"- **状态**：{label(STATUS_LABEL, proj.get('status'))}"
        f" ｜ **进度**：{proj.get('progress') if proj.get('progress') is not None else '—'}%"
        f" ｜ **最近活动**：{proj.get('last_activity') or '—'}"
    )
    out.append("")
    if proj.get("description"):
        out.append(scrub(proj["description"]))
        out.append("")

    deps = proj.get("data_deps") or []
    if deps:
        out.append(f"**数据依赖**：{'、'.join(scrub(str(x)) for x in deps)}")
        out.append("")

    tasks = proj.get("tasks") or []
    if tasks:
        out.append("**任务**")
        out.append("")
        for t in tasks:
            title = scrub(t.get("title") or t.get("text") or t.get("name") or "")
            st = label(TASK_LABEL, t.get("status"))
            upd = t.get("updated", "")
            head = f"- **[{st}]** {title}"
            if upd:
                head += f"（{upd}）"
            out.append(head)
            detail = scrub(t.get("detail", "") or "")
            if detail:
                out.append(f"  - 详情：{detail}")
            accept = scrub(t.get("acceptance", "") or "")
            if accept:
                out.append(f"  - 验收：{accept}")
            inputs = scrub(t.get("inputs", "") or "")
            if inputs:
                out.append(f"  - 输入：{inputs}")
        out.append("")

    params = proj.get("params") or []
    if params:
        out.append("**关键参数**：" + "；".join(
            f"{scrub(p.get('name',''))}={scrub(str(p.get('value','')))}" for p in params
        ))
        out.append("")

    decisions = proj.get("decisions") or []
    if decisions:
        out.append("**已定决策**")
        out.append("")
        for dec in decisions:
            text = scrub(dec.get("text", ""))
            note = scrub(dec.get("note", "") or "")
            out.append(f"- {text}" + (f"（依据：{note}）" if note else ""))
        out.append("")

    notes = proj.get("notes")
    if notes:
        out.append("**备注**")
        out.append("")
        out.append(scrub(str(notes)))
        out.append("")

    ai_logs = proj.get("ai_logs") or []
    if ai_logs:
        out.append("**产出物**")
        out.append("")
        for a in ai_logs:
            name = scrub(a.get("name", ""))
            date = a.get("date", "")
            note = scrub(a.get("note", "") or "")
            out.append(f"- `{date}` {name}" + (f" —— {note}" if note else ""))
        out.append("")

    out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ROOT / "PROJECT-STATUS.md"))
    args = ap.parse_args()

    if not REGISTRY.exists():
        print(f"找不到台账：{REGISTRY}")
        return 1

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    projects = data.get("projects") or []
    byid = {p["id"]: p for p in projects}
    progs = [p for p in projects if p.get("kind") == "program"]

    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []
    lines.append("# 项目状态总览（量化线）")
    lines.append("")
    lines.append(
        "> 本文件由 PM-Hub 台账导出，供协作者（含 AI）快速理解各超大项目的目标、进度与约束。"
    )
    lines.append(
        "> 不含台账原始数据、本机路径与私人日志；完整台账保存在本地，未入库。"
    )
    lines.append("")
    lines.append(f"**导出时间**：{today} ｜ **超大项目**：{len(progs)} 个")
    lines.append("")

    total_children = sum(1 for p in projects if p.get("parent") in {g["id"] for g in progs})
    lines.append(
        f"项目体系为三级：**L1 超大项目**（{len(progs)} 个）→ **L2 子项目**"
        f"（{total_children} 个）→ **L3 任务**。"
    )
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 超大项目 | 状态 | 进度 | 子项目数 | 阶段 |")
    lines.append("|----------|------|------|----------|------|")
    for g in progs:
        kids = [p for p in projects if p.get("parent") == g["id"]]
        lines.append(
            f"| **{g['name']}** | {label(STATUS_LABEL, g.get('status'))} "
            f"| {g.get('progress') if g.get('progress') is not None else '—'}% "
            f"| {len(kids)} | {scrub(g.get('stage') or '—')} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    for g in progs:
        kids = [p for p in projects if p.get("parent") == g["id"]]
        lines.extend(render_program(g, kids))
        lines.append("---")
        lines.append("")

    unused = byid  # 保留引用，避免 linter 报未使用
    del unused

    out_path = Path(args.out)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"已导出 {out_path}（{len(lines)} 行，{out_path.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
