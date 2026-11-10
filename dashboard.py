# -*- coding: utf-8 -*-
"""PM-Hub 看板：streamlit run dashboard.py → localhost:8501"""
import base64
import copy
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

HUB = Path(__file__).resolve().parent
sys.path.insert(0, str(HUB))
from pm_progress import progress_info
from pm_registry import read_registry, save_registry, export_registry, RegistryConflict, RegistryLockTimeout
REG = HUB / "registry.json"
UNREG = HUB / "reports" / "unregistered.json"
IGNORED = HUB / "reports" / "ignored.json"
ASSETS = HUB / "assets"


def _bg_data_uri():
    """把背景图读成 base64 data URI（不落盘到代码里，运行时生成）。"""
    p = ASSETS / "miku_bg.jpg"
    try:
        return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return ""


BG_URI = _bg_data_uri()
TINY_PX = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
UI_PREFS = HUB / "ui_prefs.json"
# -*- coding: utf-8 -*-
# =====================================================================
# 主题体系（2026-10-24 重构）
# 每套主题只声明一组 CSS 变量；组件样式不再各自写死颜色。
# 新增主题 = 往 THEMES 里加一条，不需要再写 !important 覆盖层。
# =====================================================================

from theme import (THEMES, THEME_BASE_VARS, THEME_ORDER, THEME_NAMES,
                   DEFAULT_THEME, theme_vars_css, CSS, CSS_MIKU_EXTRA)

def load_prefs():
    try:
        return json.loads(UI_PREFS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_prefs(prefs):
    try:
        UI_PREFS.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
# ---- 配色：二次元 / 初音风格（青绿主色 + 磨砂玻璃）----
ACCENT = "#2BB3A9"
ACCENT_DEEP = "#0F7A73"
STATUS_COLOR = {"active": "var(--pm-st-active)", "warm": "var(--pm-st-warm)",
                "cold": "var(--pm-st-cold)", "archived": "var(--pm-st-archived)"}
STATUS_CN = {"active": "活跃", "warm": "温", "cold": "冷", "archived": "归档"}
USAGE_CN = {"daily": "常用", "often": "常用", "rare": "偶尔", "unused": "闲置", "unknown": "未标注"}
CAT_CN = {"quant": "量化", "tool": "工具", "doc": "文档", "data": "数据", "infra": "设施",
          "ai": "AI 工具", "dev": "开发", "browser": "浏览器", "media": "媒体",
          "system": "系统", "office": "办公", "game": "游戏", "other": "其他",
          "security": "安全", "comm": "通讯", "download": "下载网盘",
          "finance": "金融", "input": "输入法"}

# ---- 三级体系：L1 超大项目 / L2 小项目 / L3 任务 ----
LEVEL_CN = {"program": "超大项目", "project": "小项目"}
TASK_STATUS_CN = {"todo": "待办", "doing": "进行中", "done": "已完成", "blocked": "受阻"}
TASK_STATUS_COLOR = {"todo": "#9AAFB2", "doing": "#E0A458", "done": "#4E7A47", "blocked": "#C2575F"}
TASK_STATUS_ORDER = ["todo", "doing", "done", "blocked"]


def strip_emoji(s):
    """去掉标题/导航项开头的 emoji 与前导符号，用于纯文字展示（去 AI 味）。"""
    return re.sub(r"^[^\w\u4e00-\u9fff]+\s*", "", str(s)).strip() or str(s)


def load_reg():
    return read_registry(REG)


def fresh_form_key(name):
    """Clear a successfully submitted form when it is rendered again."""
    pending = st.session_state.pop("_clear_form_" + name, None)
    if pending is not None:
        for key in pending:
            st.session_state.pop(key, None)
    return f"{name}-v{st.session_state.get('_form_version_' + name, 0)}"


def reset_form_after_save(name, keys=()):
    st.session_state["_clear_form_" + name] = list(keys)
    version = "_form_version_" + name
    st.session_state[version] = st.session_state.get(version, 0) + 1


_ABSENT = object()


def _apply_view_changes(raw, baseline, edited):
    """Apply UI changes to the raw snapshot without persisting display defaults."""
    if baseline == edited:
        return copy.deepcopy(raw) if raw is not _ABSENT else _ABSENT
    if isinstance(baseline, dict) and isinstance(edited, dict):
        result = copy.deepcopy(raw) if isinstance(raw, dict) else {}
        for key in baseline.keys() | edited.keys():
            value = _apply_view_changes(
                raw.get(key, _ABSENT) if isinstance(raw, dict) else _ABSENT,
                baseline.get(key, _ABSENT), edited.get(key, _ABSENT))
            if value is _ABSENT:
                result.pop(key, None)
            else:
                result[key] = value
        return result
    if isinstance(baseline, list) and isinstance(edited, list):
        def keyed(items):
            return (all(isinstance(x, dict) and x.get("id") is not None for x in items)
                    and len({x["id"] for x in items}) == len(items))
        raw_items = raw if isinstance(raw, list) else []
        if keyed(baseline) and keyed(edited) and keyed(raw_items):
            old = {x["id"]: x for x in baseline}
            original = {x["id"]: x for x in raw_items}
            return [_apply_view_changes(original.get(item["id"], _ABSENT),
                                        old.get(item["id"], _ABSENT), item)
                    for item in edited]
    return copy.deepcopy(edited) if edited is not _ABSENT else _ABSENT


def save_reg(reg, operator, base=None, guard=None):
    """Save changes against the snapshot originally displayed to this session."""
    try:
        import export_static
        view_base = base if base is not None else _reg_base
        raw_base = _apply_view_changes(_raw_reg_base, _reg_base, view_base)
        raw_edited = _apply_view_changes(_raw_reg_base, _reg_base, reg)
        result = save_registry(raw_base, raw_edited, operator,
                               path=REG, export=export_static.export, guard=guard)
    except (RegistryConflict, RegistryLockTimeout) as exc:
        st.error(f"保存未完成，台账已被修改或暂时被占用。请保留当前输入并核对后重试：{exc}")
        st.stop()
    except Exception as exc:
        st.error(f"保存未完成，输入仍保留：{exc}")
        st.stop()
    if result.export_error:
        st.session_state["_export_warning"] = result.export_error
        st.warning("台账已保存，但静态页面更新失败：" + result.export_error)
    return result


def form_base(key, record):
    """Keep the record as seen when a form was first displayed."""
    state_key = "_edit_base_" + key
    if state_key not in st.session_state:
        st.session_state[state_key] = copy.deepcopy(record)
    elif st.session_state[state_key] != record:
        st.warning("这条记录已更新，当前输入仍保留。可核对最新内容后重新载入。")
        old = st.session_state[state_key]
        changed_fields = [name for name in set(old) | set(record) if old.get(name) != record.get(name)]
        st.caption("变化字段：" + "、".join(sorted(changed_fields)))
        if st.button("载入最新记录（清空当前编辑内容）", key="_reload_" + key):
            st.session_state.pop(state_key, None)
            if key.startswith("app-"):
                st.session_state.pop("appdetail-purpose", None)
                st.session_state.pop("appdetail-usage", None)
            st.rerun()
    return st.session_state[state_key]


def save_form_record(key, collection, record_id, original, changed, *, parent_id=None):
    """Submit only this form's changes against its original record."""
    base = copy.deepcopy(_reg_base)
    if parent_id is not None:
        parent = next((p for p in base["projects"] if p.get("id") == parent_id), None)
        if parent is None:
            parent = copy.deepcopy(st.session_state.get("_project_cache_" + parent_id))
            if parent is None:
                st.error("项目已被删除，无法安全保存。请复制当前输入。")
                st.stop()
            base["projects"].append(parent)
        records = parent.setdefault(collection, [])
    else:
        records = base[collection]
    matches = [i for i, item in enumerate(records) if item.get("id") == record_id]
    if len(matches) > 1:
        st.error("该记录的 ID 不唯一，无法安全保存。请先检查重复记录。")
        st.stop()
    index = matches[0] if matches else None
    if index is None:
        records.append(copy.deepcopy(original))
        index = len(records) - 1
    else:
        records[index] = copy.deepcopy(original)
    edited = copy.deepcopy(base)
    target_records = edited[collection] if parent_id is None else next(
        p for p in edited["projects"] if p.get("id") == parent_id)[collection]
    if changed is None:
        target_records.pop(index)
    else:
        target_records[index] = copy.deepcopy(changed)
    guard = None
    if collection == "decisions" and parent_id is not None:
        def guard(current):
            project = next((p for p in current.get("projects", []) if p.get("id") == parent_id), None)
            decision = next((d for d in (project or {}).get("decisions", [])
                             if d.get("id") == record_id), None)
            if decision is None or decision.get("status", "active") != original.get("status", "active"):
                raise RegistryConflict("该结论已被推翻或删除，请先核对当前状态。")
    result = save_reg(edited, "owner(工作台)", base=base, guard=guard)
    st.session_state.pop("_edit_base_" + key, None)
    return result


def slug(name):
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", name.lower()).strip("-")
    return s or "untitled"


def badge(color, text):
    """极简状态标记：小圆点 + 同色淡文字（不用彩色胶囊）。"""
    if not text:
        return ""
    return (f'<span style="color:{color};font-size:11px;margin-left:8px;letter-spacing:.2px;white-space:nowrap;">'
            f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{color};'
            f'margin-right:5px;vertical-align:middle;"></span>{text}</span>')


def progress_html(prog):
    """进度条：弹簧填充 + 发光 + 流光扫过（样式见 CSS .pmbar）。"""
    if isinstance(prog, (int, float)):
        p = int(prog)
        return ('<span class="pmbar-wrap"><span class="pmbar">'
                f'<span class="pmfill" style="width:{p}%"></span></span>'
                f'<span class="pmpct">{p}%</span></span>')
    return '<span style="font-size:12px;color:#9B978F;">进度未定</span>'


# ---------- 目标 / 进度 ----------
def reconcile_goals(p):
    """确保 p['goals'] 是结构正确的列表，返回该列表。"""
    goals = p.get("goals")
    if not isinstance(goals, list):
        goals = []
        p["goals"] = goals
    for i, g in enumerate(goals):
        if not isinstance(g, dict):
            continue
        if not g.get("id"):
            g["id"] = "g%d" % (i + 1)
        g.setdefault("text", "")
        g["done"] = bool(g.get("done"))
    return goals


def norm_tasks(p):
    """确保 p['tasks'] 是结构正确的第三级任务列表，返回该列表。"""
    ts = p.get("tasks")
    if not isinstance(ts, list):
        ts = []
        p["tasks"] = ts
    for i, t in enumerate(ts):
        if not isinstance(t, dict):
            continue
        if not t.get("id"):
            t["id"] = "t%d" % (i + 1)
        t.setdefault("title", "")
        t.setdefault("detail", "")
        t.setdefault("acceptance", "")
        t.setdefault("inputs", "")
        t.setdefault("outputs", "")
        t.setdefault("batch", "")
        t.setdefault("prompt", "")
        t.setdefault("updated", "")
        if t.get("status") not in TASK_STATUS_CN:
            t["status"] = "todo"
    return ts


def recompute_progress(p):
    """进度自动重平衡：有第三级任务 → 按任务完成率；否则按目标完成率。"""
    tasks = norm_tasks(p)
    if tasks:
        done = sum(1 for t in tasks if t.get("status") == "done")
        p["progress"] = round(done * 100 / len(tasks))
        return p.get("progress")
    goals = reconcile_goals(p)
    if goals:
        done = sum(1 for g in goals if g.get("done"))
        p["progress"] = round(done * 100 / len(goals))
    return p.get("progress")


def ensure_project_fields(p):
    """补齐 goals / tasks / progress_log / files / params / ai_logs / dev_logs / decisions / 层级字段。"""
    reconcile_goals(p)
    for k in ("progress_log", "files", "params", "ai_logs", "dev_logs", "decisions"):
        if not isinstance(p.get(k), list):
            p[k] = []
    p.setdefault("kind", "project")
    p.setdefault("parent", None)
    norm_tasks(p)


def next_gid(goals):
    n = 0
    for g in goals:
        gid = str(g.get("id", ""))
        if gid.startswith("g") and gid[1:].isdigit():
            n = max(n, int(gid[1:]))
    return "g%d" % (n + 1)


def next_tid(tasks):
    n = 0
    for t in tasks:
        tid = str(t.get("id", ""))
        if tid.startswith("t") and tid[1:].isdigit():
            n = max(n, int(tid[1:]))
    return "t%d" % (n + 1)


def next_did(decs):
    n = 0
    for d in decs:
        did = str(d.get("id", ""))
        if did.startswith("d") and did[1:].isdigit():
            n = max(n, int(did[1:]))
    return "d%d" % (n + 1)


# ---------- 三级体系：查询与聚合 ----------
def child_projects(plist, pid):
    """L2：取某个 L1 下的小项目。"""
    return [p for p in plist if p.get("parent") == pid]


def program_list(plist):
    """L1：超大项目列表。"""
    return [p for p in plist if p.get("kind") == "program"]


def standalone_projects(plist):
    """独立小项目：不归属任何超大项目 —— 与 L1 并列的合法形态，不是「待归位」。

    判定：kind != program 且 parent 为空或指向不存在的 id。
    """
    ids = {p.get("id") for p in plist}
    return [p for p in plist
            if p.get("kind") != "program"
            and (not p.get("parent") or p.get("parent") not in ids)]


def task_stats(p):
    d = {"total": 0, "todo": 0, "doing": 0, "done": 0, "blocked": 0}
    for t in (p.get("tasks") or []):
        if not isinstance(t, dict):
            continue
        d["total"] += 1
        stt = t.get("status") if t.get("status") in TASK_STATUS_CN else "todo"
        d[stt] += 1
    return d


def rollup(plist, prog):
    """L1 聚合：子项目数、任务统计、进度（任务优先，无任务时取子项目均值）。"""
    kids = child_projects(plist, prog.get("id"))
    tot = done = doing = 0
    for k in kids:
        for t in (k.get("tasks") or []):
            if not isinstance(t, dict):
                continue
            tot += 1
            if t.get("status") == "done":
                done += 1
            elif t.get("status") == "doing":
                doing += 1
    if tot:
        pct = round(done * 100 / tot)
    else:
        vals = [v for k in kids for v in [progress_info(k)[0]] if isinstance(v, (int, float))]
        pct = round(sum(vals) / len(vals)) if vals else None
    covered = sum(bool(k.get("tasks")) for k in kids)
    source = (f"按子项目任务 {done}/{tot} 计算 · {covered}/{len(kids)} 个小项目有任务" if tot
              else f"按 {len(vals)}/{len(kids)} 个有进度的小项目取均值" if vals
              else "暂无可计算的子项目进度")
    return {"kids": kids, "n_kids": len(kids), "n_tasks": tot,
            "done": done, "doing": doing, "progress": pct, "progress_source": source}


def task_pack_text(prog, proj, task):
    """把一条任务渲染成"可交付 AI 的完整任务包"。上下文越全，AI 产出越不糊。"""
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
        _rels = prog.get("relations") or []
        if _rels:
            _nm = {k.get("id"): k.get("name", "") for k in projects}
            L.append("- 小项目之间的连接关系：")
            for _r in _rels:
                L.append("    · %s ──%s──▶ %s%s" % (
                    _nm.get(_r.get("from"), _r.get("from", "?")), _r.get("type", ""),
                    _nm.get(_r.get("to"), _r.get("to", "?")),
                    ("（%s）" % _r["note"]) if _r.get("note") else ""))
    L.append("- 小项目：%s —— %s" % (proj.get("name", ""), proj.get("description", "")))
    L.append("- 项目阶段：%s" % (proj.get("stage") or "—"))
    L.append("- 项目根目录：%s" % root)
    L.append("- 数据依赖：%s" % deps)
    if proj.get("notes"):
        L.append("- 项目备注：%s" % proj["notes"])
    decs = [d for d in (proj.get("decisions") or []) if d.get("status", "active") == "active"]
    if decs:
        L.append("")
        L.append("- 本项目**现行结论（必须遵守，不得违反）**：")
        for d in decs:
            L.append("    · [%s] %s%s" % (d.get("date", ""), d.get("text", ""),
                                         ("（依据：%s）" % d["note"]) if d.get("note") else ""))
    else:
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


def task_pack_markdown(prog, proj, only_todo=True):
    """整个 L2 项目的任务包（按批次分组），用于分批交给 AI。"""
    tasks = [t for t in norm_tasks(proj)
             if (not only_todo) or t.get("status") != "done"]
    head = ["# 任务包 · %s" % proj.get("name", ""),
            "",
            "- 生成时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
            "- 所属超大项目：%s" % (prog.get("name", "") if prog else "—"),
            "- 任务数：%d（%s）" % (len(tasks), "仅未完成" if only_todo else "全部"),
            ""]
    batches = {}
    for t in tasks:
        batches.setdefault(t.get("batch") or "未分批", []).append(t)
    for b in sorted(batches, key=lambda x: (x == "未分批", x)):
        head.append("## 批次 %s（%d 项）" % (b, len(batches[b])))
        head.append("")
        for t in batches[b]:
            head.append("---")
            head.append("")
            head.append(task_pack_text(prog, proj, t))
            head.append("")
    return "\n".join(head)


def goto_project(pid):
    """按钮回调：切到详情页并定位该项目（on_click 在控件实例化前执行）。"""
    st.session_state["nav"] = "🔍 项目详情"
    st.session_state["current_pid"] = pid


def goto_overview():
    """按钮回调：返回项目总览（顶层）。"""
    st.session_state["nav"] = "📊 项目总览"
    st.session_state.pop("sel_prog", None)
    st.session_state.pop("sel_pj", None)


def goto_program(pid):
    """按钮回调：进入某个 L1 超大项目。"""
    st.session_state["nav"] = "📊 项目总览"
    st.session_state["sel_prog"] = pid
    st.session_state.pop("sel_pj", None)


def open_subproject(pid):
    """按钮回调：在总览内下钻到某个 L2 小项目（第三级视图）。"""
    st.session_state["sel_pj"] = pid


def back_to_programs():
    """按钮回调：从 L1 回到超大项目列表。"""
    st.session_state.pop("sel_prog", None)
    st.session_state.pop("sel_pj", None)


def back_to_program():
    """按钮回调：从 L2 回到其所属 L1。"""
    st.session_state.pop("sel_pj", None)


def fmt_size(n):
    """文件大小自适应单位：≥1GB→GB，≥1MB→MB，否则 KB。"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024:.0f} KB"


def touch(p):
    p["last_activity"] = datetime.now().strftime("%Y-%m-%d")


# ---------- 应用启动 ----------
_EXEC_EXT = {".exe", ".lnk", ".bat", ".cmd", ".com", ".msi", ".appref-ms"}
_BLOCK_PAT = ("unins", "install", "setup", "installshield", "redist")


def _is_exec_file(p):
    try:
        return p.is_file() and p.suffix.lower() in _EXEC_EXT
    except OSError:
        return False


def _is_blocked(p):
    """疑似卸载/安装程序 → 阻止启动，避免误点。"""
    return any(w in p.stem.lower() for w in _BLOCK_PAT)


def _find_exe(d, name, depth=1):
    """在安装目录里找最像主程序的 .exe（按名称相似度打分）。"""
    cands = []
    try:
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() == ".exe":
                cands.append((f, 0))
            elif depth > 0 and f.is_dir():
                try:
                    for g in f.iterdir():
                        if g.is_file() and g.suffix.lower() == ".exe":
                            cands.append((g, 1))
                except OSError:
                    pass
    except OSError:
        return None
    if not cands:
        return None
    nm = (name or "").lower()

    def score(t):
        f, dep = t
        s = 0
        st_ = f.stem.lower()
        if nm and st_ == nm:
            s += 200
        elif nm and (nm in st_ or st_ in nm):
            s += 120
        if _is_blocked(f):
            s -= 150
        return s - dep * 30

    return sorted(cands, key=score, reverse=True)[0][0]


def resolve_launch(a):
    """解析可启动目标 → (path 或 None, 说明)。"""
    nm = a.get("name", "")
    for raw in ((a.get("exe") or "").strip().strip('"'), (a.get("path") or "").strip().strip('"')):
        if not raw:
            continue
        p = Path(raw)
        if _is_exec_file(p):
            return str(p), (".lnk 快捷方式" if p.suffix.lower() == ".lnk" else "可执行文件")
        if p.is_dir():
            r = _find_exe(p, nm)
            if r is not None:
                return str(r), "安装目录内识别到主程序"
    return None, "没有可启动的本地程序（可能已卸载，或只登记了图标/快捷入口）"


def open_app(aid):
    st.session_state["current_app"] = aid


def back_to_apps():
    st.session_state["current_app"] = None


st.set_page_config(page_title="PM-Hub 项目中枢", page_icon="🗂", layout="wide",
                   initial_sidebar_state="expanded")

_prefs = load_prefs()
if "theme" not in st.session_state:
    _saved = _prefs.get("theme")
    st.session_state["theme"] = _saved if _saved in THEMES else DEFAULT_THEME
THEME = st.session_state["theme"]
st.markdown("<style>" + theme_vars_css(THEME) + "</style>", unsafe_allow_html=True)
st.markdown(CSS, unsafe_allow_html=True)
if THEME == "miku":
    st.markdown(CSS_MIKU_EXTRA.replace("__BG__", BG_URI), unsafe_allow_html=True)

# 常驻装饰层（fixed，不受 Streamlit 重跑影响）
st.markdown('<div id="pmAurora"></div><div id="pmTopbar"></div>', unsafe_allow_html=True)

# 初音主题的漂浮音符
if THEME == "miku":
    _NOTES = "".join(
        f'<i style="left:{l}%;font-size:{s}px;animation-duration:{d}s;animation-delay:{dl}s">{c}</i>'
        for l, s, d, dl, c in [
            (6, 20, 16, 0, "\u266a"), (18, 14, 21, 3, "\u266b"), (33, 18, 18, 6, "\u266a"),
            (52, 13, 23, 1.5, "\u2669"), (68, 21, 17, 8, "\u266a"), (81, 15, 20, 4.5, "\u266c"),
            (92, 19, 19, 10, "\u266a"),
        ])
    st.markdown(f'<div id="pmNotes">{_NOTES}</div>', unsafe_allow_html=True)

CAT_COLOR = {"ai": "#5B8DD9", "quant": "#2BB3A9", "dev": "#7B6FE0", "browser": "#E08A5B",
             "media": "#D96BA1", "system": "#7C8B8E", "office": "#C79A3E", "game": "#9B6BE0",
             "tool": "#5FAFA6", "other": "#9AAFB2",
             "security": "#C2575F", "comm": "#3E93A8", "download": "#5B82C9",
             "finance": "#B5852E", "input": "#8A6FC8"}

reg = load_reg()
_raw_reg_base = copy.deepcopy(reg)
projects = sorted(reg.get("projects", []),
                  key=lambda x: x.get("last_activity") or "", reverse=True)
apps = reg.get("apps", [])
locs = reg.get("locations", [])
for _p in projects:            # 老项目补齐 goals / progress_log
    ensure_project_fields(_p)
_reg_base = copy.deepcopy(reg)
if st.session_state.get("_export_warning"):
    st.warning("台账已保存，但静态页面更新失败：" + st.session_state["_export_warning"])
    if st.button("重新生成静态页面"):
        try:
            import export_static
            retry = export_registry(export_static.export, path=REG)
            if retry.export_error:
                st.session_state["_export_warning"] = retry.export_error
                st.error("静态页面仍未更新：" + retry.export_error)
            else:
                st.session_state.pop("_export_warning", None)
                st.rerun()
        except (RegistryLockTimeout, OSError) as exc:
            st.error("静态页面暂时无法更新：" + str(exc))

with st.sidebar:
    st.markdown(
        '<div style="padding:4px 10px 2px;position:relative;z-index:1;">'
        '<div style="display:flex;align-items:center;gap:11px;">'
        '<div class="pmlogo" style="color:var(--pm-on-accent);">'
        '<svg width="21" height="21" viewBox="0 0 24 24" fill="none">'
        '<path d="M12 2.6 21 7.4v9.2L12 21.4 3 16.6V7.4L12 2.6Z" stroke="currentColor" '
        'stroke-width="1.5" stroke-linejoin="round" opacity=".95"/>'
        '<path d="M3 7.4 12 12.2l9-4.8M12 12.2v9.2" stroke="currentColor" '
        'stroke-width="1.5" stroke-linejoin="round" opacity=".5"/>'
        '</svg></div>'
        '<div style="min-width:0;">'
        '<div class="pmbrand">PM-Hub</div>'
        '<div style="font-size:10.5px;color:var(--pm-ink-3);letter-spacing:.12em;margin-top:5px;">'
        '个人项目台账</div>'
        '</div></div>'
        '<div class="pmrule"></div>'
        '</div>',
        unsafe_allow_html=True)
    if "nav" not in st.session_state:
        st.session_state["nav"] = "📊 项目总览"
    page = st.radio("导航",
                    ["📊 项目总览", "🔍 项目详情", "🧩 应用台账",
                     "➕ 新增登记", "🧹 待整理清单", "📍 文件地标"],
                    key="nav", label_visibility="collapsed", format_func=strip_emoji)
    st.divider()
    sc = {"active": 0, "warm": 0, "cold": 0, "archived": 0}
    for p in projects:
        if p.get("kind") == "program":
            continue
        sc[p.get("status")] = sc.get(p.get("status"), 0) + 1
    confirmed = sum(1 for a in apps if a.get("desc_confirmed"))
    _nl1 = len(program_list(projects))
    _nkid = sum(len(child_projects(projects, x.get("id"))) for x in program_list(projects))
    _nstand = len(standalone_projects(projects))
    _nl3 = sum(len(p.get("tasks") or []) for p in projects)
    _nopen = sum(1 for p in projects for t in (p.get("tasks") or [])
                 if t.get("status") != "done")
    st.markdown(
        f'<div style="font-size:11px;color:var(--pm-ink-2);line-height:1.95;padding:0 11px;'
        f'font-variant-numeric:tabular-nums;">'
        f'超大项目 {_nl1} <span style="color:var(--pm-ink-4);">/ 小项目 {_nkid}</span><br>'
        f'独立 {_nstand} · 任务 {_nl3}（未完成 {_nopen}）<br>'
        f'活跃小项目 {sc["active"]} · 活跃体系 {sum(1 for p in program_list(projects) if p.get("status") == "active")}<br>'
        f'小项目：温 {sc["warm"]} · 冷 {sc["cold"]} · 归档 {sc["archived"]}<br>'
        f'应用 {len(apps)} · 已确认 {confirmed}'
        f'</div>',
        unsafe_allow_html=True)

    # ---- 外观主题 ----
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:9.5px;letter-spacing:.18em;color:var(--pm-ink-4);'
                'padding:0 11px 7px;">外观主题</div>',
                unsafe_allow_html=True)
    st.selectbox("主题", THEME_ORDER, key="theme",
                 format_func=lambda k: THEME_NAMES.get(k, k),
                 label_visibility="collapsed")
    st.markdown(
        f'<div style="font-size:10.5px;color:var(--pm-ink-4);padding:7px 11px 0;line-height:1.6;">'
        f'{THEMES[st.session_state["theme"]]["note"]}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:10px;color:var(--pm-ink-4);padding:14px 11px 0;">'
        f'{reg.get("updated_at", "")} · {reg.get("operator", "")}</div>',
        unsafe_allow_html=True)

if _prefs.get("theme") != st.session_state["theme"]:
    _prefs["theme"] = st.session_state["theme"]
    try:
        UI_PREFS.write_text(json.dumps(_prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def project_label(pid):
    """选择器里的项目标签：带层级前缀 + 所属超大项目。"""
    x = next((y for y in projects if y.get("id") == pid), None)
    if x is None:
        return str(pid)
    pre = "超大项目" if x.get("kind") == "program" else "小项目"
    par = next((y.get("name") for y in projects if y.get("id") == x.get("parent")), "")
    return f'[{pre}] {x.get("name", "")}' + (f'  ·  {par}' if par else "")


# ================= 三级体系：渲染层 =================
def card_program_html(prog, agg):
    """L1 卡片：自己 + 子项目缩略清单 + 聚合进度。"""
    color = STATUS_COLOR.get(prog.get("status"), "var(--pm-ink-3)")
    kids = agg["kids"]
    rows = []
    for k in kids[:7]:
        ts = task_stats(k)
        kc = STATUS_COLOR.get(k.get("status"), "var(--pm-ink-3)")
        rr = (f'<div style="display:flex;justify-content:space-between;gap:10px;font-size:12px;'
              f'padding:3px 0;color:var(--pm-ink-2);">'
              f'<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
              f'<span style="display:inline-block;width:5px;height:5px;border-radius:50%;'
              f'background:{kc};margin-right:7px;vertical-align:middle;"></span>{k.get("name", "")}</span>'
              f'<span style="color:var(--pm-ink-3);white-space:nowrap;flex:0 0 auto;">'
              f'{ts["done"]}/{ts["total"]} 任务</span></div>')
        rows.append(rr)
    if len(kids) > 7:
        rows.append(f'<div style="font-size:11.5px;color:var(--pm-ink-3);padding:3px 0;">…还有 {len(kids) - 7} 个</div>')
    if not rows:
        rows.append('<div style="font-size:12px;color:var(--pm-ink-4);padding:3px 0;">还没有挂载小项目</div>')
    task_line = (f'小项目 {agg["n_kids"]} · 任务 {agg["n_tasks"]}'
                 f'（完成 {agg["done"]} · 进行中 {agg["doing"]}）')
    return (
        f'<div class="pmcard" style="padding:20px 22px 18px;height:100%;">'
        f'<div class="gloss"></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">'
        f'<span style="font-weight:700;font-size:16.5px;color:var(--pm-ink);letter-spacing:-.01em;line-height:1.35;">{prog.get("name", "")}</span>'
        f'{badge(color, STATUS_CN.get(prog.get("status"), ""))}</div>'
        f'<div style="color:var(--pm-ink-2);font-size:12.5px;line-height:1.65;margin:8px 0 6px;">{prog.get("description", "")}</div>'
        f'<div style="font-size:12px;color:var(--pm-ink-2);margin-bottom:5px;">{task_line}</div>'
        f'<div style="margin:5px 0 10px;">{progress_html(agg["progress"])}<br><span style="font-size:11px;color:var(--pm-ink-3);">{agg["progress_source"]}</span></div>'
        f'<div style="border-top:1px solid var(--pm-line-soft);padding-top:8px;">'
        f'<div style="font-size:11px;color:var(--pm-ink-3);letter-spacing:.4px;margin-bottom:3px;">小项目</div>'
        + "".join(rows) +
        f'</div>'
        f'<div style="font-size:11.5px;color:var(--pm-ink-3);margin-top:10px;padding-top:9px;'
        f'border-top:1px solid var(--pm-line-soft);">阶段 {prog.get("stage", "—")} · 更新 {prog.get("last_activity") or "—"}</div>'
        f'</div>')


def card_project_html(p):
    """L2 卡片：与旧总览卡一致，另加任务统计。"""
    color = STATUS_COLOR.get(p.get("status"), "var(--pm-ink-3)")
    root = (p.get("paths") or {}).get("root", "")
    plats = " · ".join(p.get("platform") or []) or "—"
    ts = task_stats(p)
    goals = reconcile_goals(p)
    if ts["total"]:
        gsum = f'任务 {ts["done"]}/{ts["total"]}'
    elif goals:
        gsum = '目标 %d/%d' % (sum(1 for g in goals if g.get("done")), len(goals))
    else:
        gsum = '<span style="color:var(--pm-ink-4);">任务与目标均未设定</span>'
    return (
        f'<div class="pmcard" style="padding:18px 20px 16px;height:100%;">'
        f'<div class="gloss"></div>'
        f'<div style="font-weight:600;font-size:14.5px;color:var(--pm-ink);">{p.get("name", "")}'
        f'{badge(color, STATUS_CN.get(p.get("status"), ""))}</div>'
        f'<div style="color:var(--pm-ink-2);font-size:12.5px;line-height:1.6;margin:7px 0;min-height:38px;">{p.get("description", "")}</div>'
        f'<div style="font-size:12px;color:var(--pm-ink-2);margin-bottom:4px;">阶段 {p.get("stage", "—")}　·　{gsum}</div>'
        f'<div style="margin:6px 0 2px;">{progress_html(progress_info(p)[0])} <span style="font-size:11px;color:var(--pm-ink-3);">{progress_info(p)[1]}</span></div>'
        f'<div style="font-size:11.5px;color:var(--pm-ink-3);margin-top:11px;padding-top:10px;border-top:1px solid var(--pm-line-soft);">'
        f'更新 {p.get("last_activity") or "—"} · {plats}<br>'
        f'<code>{root or "路径待补"}</code></div></div>')


def open_workbench_task(project, task_id):
    """从总览定位任务，保留所属体系以便返回。"""
    if project.get("kind") == "program":
        goto_program(project["id"])
    else:
        st.session_state["nav"] = "📊 项目总览"
        if project.get("parent"):
            st.session_state["sel_prog"] = project["parent"]
        else:
            st.session_state.pop("sel_prog", None)
        st.session_state["sel_pj"] = project["id"]
        st.session_state["focus_task_id"] = task_id
        st.session_state["focus_task_project_id"] = project["id"]


def render_workbench_queue():
    """汇总真实状态，不推断前置条件或虚构验收状态。"""
    buckets = {"doing": [], "todo": [], "blocked": []}
    for project in projects:
        if project.get("status") == "archived":
            continue
        for task in project.get("tasks") or []:
            if isinstance(task, dict) and task.get("status") in buckets:
                buckets[task["status"]].append((project, task))
    for items in buckets.values():
        items.sort(key=lambda item: item[1].get("updated") or "", reverse=True)

    st.markdown("#### 下一步工作")
    st.caption("按任务当前状态汇总；待办不代表前置条件已经满足。已归档项目不计入此处。")
    labels = {"doing": "进行中", "todo": "待办", "blocked": "受阻"}
    order = list(labels)
    first_nonempty = next((status for status in order if buckets[status]), None)
    if first_nonempty:
        order.remove(first_nonempty)
        order.insert(0, first_nonempty)
    tabs = st.tabs([f'{labels[status]} · {len(buckets[status])}' for status in order])
    for tab, status in zip(tabs, order):
        with tab:
            if not buckets[status]:
                st.caption(f'暂无{labels[status]}任务。')

            def show_queue_rows(items, start=0):
                for index, (project, task) in enumerate(items, start):
                    info, action = st.columns([6, 1])
                    info.write(f'**{task.get("title") or "未命名任务"}**')
                    info.caption(f'{project.get("name") or "未命名项目"} · 更新 {task.get("updated") or "未知"}')
                    action.button("查看任务", key=f'queue-{status}-{index}',
                                  on_click=open_workbench_task, args=(project, task.get("id")),
                                  width="stretch")

            items = buckets[status]
            show_queue_rows(items[:5])
            if len(items) > 5:
                with st.expander(f'展开其余 {len(items) - 5} 项'):
                    show_queue_rows(items[5:], start=5)


def render_program_overview():
    """顶层视图：超大项目（含小项目）+ 独立小项目，两类并列。"""
    progs = [p for p in program_list(projects) if p.get("status") != "archived"]
    stands = [p for p in standalone_projects(projects) if p.get("status") != "archived"]
    n_l3 = sum(len(p.get("tasks") or []) for p in projects)
    n_prog = len(program_list(projects))
    n_kid = sum(len(child_projects(projects, x.get("id"))) for x in program_list(projects))
    _nopen_all = sum(1 for _p in projects for _t in (_p.get("tasks") or [])
                     if _t.get("status") != "done")
    _nact = sum(1 for _p in projects if _p.get("status") == "active" and _p.get("kind") != "program")
    st.markdown(
        '<div class="pmhero">'
        '<div class="pmhero-eyebrow">Local Workspace · 资产台账</div>'
        '<div class="pmhero-title">项目总览</div>'
        '<div class="pmhero-sub">三层结构串成一条线：超大项目（体系）→ 小项目 → 任务。'
        '点卡片逐级下沉，所有判断以 registry.json 为准。</div>'
        '<div class="pmhero-stats">'
        f'<div class="pmstat is-accent"><b>{n_prog}</b><span>超大项目</span></div>'
        f'<div class="pmstat"><b>{n_kid}</b><span>下辖小项目</span></div>'
        f'<div class="pmstat"><b>{len(standalone_projects(projects))}</b><span>独立小项目</span></div>'
        f'<div class="pmstat"><b>{n_l3}</b><span>任务</span></div>'
        f'<div class="pmstat"><b>{_nopen_all}</b><span>未完成</span></div>'
        f'<div class="pmstat"><b>{_nact}</b><span>活跃小项目</span></div>'
        '</div></div>',
        unsafe_allow_html=True)

    render_workbench_queue()
    st.markdown("#### 超大项目")
    if progs:
        cols = st.columns(2)
        for i, prog in enumerate(progs):
            agg = rollup(projects, prog)
            with cols[i % 2]:
                st.markdown(card_program_html(prog, agg), unsafe_allow_html=True)
                st.button("查看小项目", key=f"openprog-{prog['id']}", width="stretch",
                          on_click=goto_program, args=(prog["id"],))
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    else:
        st.caption("还没有超大项目。要一次性开发由多个体系构成的大工程时，在「新增登记」里按超大项目登记。")

    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    st.markdown("#### 独立小项目")
    st.caption("独立项目与超大项目平级，同样是完整的项目；只有当你决定把某个大工程拆成多体系时才需要归入超大项目。")
    if stands:
        ocols = st.columns(3)
        for i, p in enumerate(stands):
            with ocols[i % 3]:
                st.markdown(card_project_html(p), unsafe_allow_html=True)
                st.button("查看详情与任务", key=f"stand-{p['id']}", width="stretch",
                          on_click=open_subproject, args=(p["id"],))
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    else:
        st.caption("当前所有小项目都归属在超大项目里。")

    with st.expander("全部小项目（扁平清单）"):
        rows = []
        for prog in sorted(program_list(projects), key=lambda x: x.get("name", "")):
            for k in child_projects(projects, prog["id"]):
                ts = task_stats(k)
                rows.append({"归属": prog.get("name", ""), "小项目": k.get("name", ""),
                             "状态": STATUS_CN.get(k.get("status"), k.get("status", "")),
                             "阶段": k.get("stage", ""), "任务": f'{ts["done"]}/{ts["total"]}',
                             "进度": (f'{progress_info(k)[0]}% · {progress_info(k)[1]}' if progress_info(k)[0] is not None else "—"),
                             "更新": k.get("last_activity") or ""})
        for p in stands:
            ts = task_stats(p)
            rows.append({"归属": "独立", "小项目": p.get("name", ""),
                         "状态": STATUS_CN.get(p.get("status"), p.get("status", "")),
                         "阶段": p.get("stage", ""), "任务": f'{ts["done"]}/{ts["total"]}',
                         "进度": (f'{progress_info(p)[0]}% · {progress_info(p)[1]}' if progress_info(p)[0] is not None else "—"),
                         "更新": p.get("last_activity") or ""})
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)


# ---------- 通用信息区块（L1 超大项目 / L2 小项目共用同一套渲染）----------

def ui_decisions_block(p):
    """结论与裁决：现行口径，AI 必须先读；老板可改 / 推翻 / 删。"""
    st.markdown("#### 结论与裁决")
    st.caption("这是本项目**当前生效的口径**。AI 动手前必须先读这里，按此执行；"
               "结论变了就在这里推翻——不要靠 AI 长期记忆去改。")
    decs = p.get("decisions") or []
    active = [d for d in decs if d.get("status", "active") == "active"]
    revoked = [d for d in decs if d.get("status") == "revoked"]
    if not decs:
        st.info("还没有结论。把「以后都按 X 做 / 已否决 Y」这类口径写一条，AI 每次进来都会先读。")
    for d in active:
        dc1, dc2, dc3 = st.columns([10, 1.2, 1.2])
        dc1.markdown(
            f'<div style="border-left:2px solid {ACCENT};padding:2px 0 2px 12px;margin:6px 0;">'
            f'<span style="font-size:11.5px;color:var(--pm-ink-3);">{d.get("date","")}</span>&nbsp;&nbsp;'
            f'<span style="font-size:12.5px;color:var(--pm-ink);">{d.get("text","")}</span>'
            + (f'<br><span style="font-size:11px;color:var(--pm-ink-3);">依据：{d.get("note","")}</span>' if d.get("note") else '')
            + '</div>', unsafe_allow_html=True)
        if dc2.button("推翻", key=f"drev-{p['id']}-{d['id']}", help="标记为已推翻（保留痕迹，AI 不再执行）"):
            d["status"] = "revoked"
            d["revoked_on"] = datetime.now().strftime("%Y-%m-%d")
            touch(p)
            save_reg(reg, "owner(工作台)")
            st.toast("已推翻该结论")
            st.rerun()
        if dc3.button("改", key=f"dedit-{p['id']}-{d['id']}", help="改这条结论的文字"):
            st.session_state[f"dedit_open_{p['id']}_{d['id']}"] = True
    _open_id = None
    for d in decs:
        if st.session_state.get(f"dedit_open_{p['id']}_{d['id']}"):
            _open_id = d["id"]
    if _open_id is None:
        _prefix = f"dedit_open_{p['id']}_"
        for _key in st.session_state:
            if _key.startswith(_prefix) and st.session_state[_key]:
                _open_id = _key[len(_prefix):]
                break
    if _open_id:
        _d = next((x for x in decs if x["id"] == _open_id), None)
        _form_key = f"decision-{p['id']}-{_open_id}"
        if _d is None:
            _form_key = f"decision-{p['id']}-{_open_id}"
            _d = st.session_state.get("_edit_base_" + _form_key)
            if _d is None:
                st.error("该结论已被删除，请返回后重新选择。")
                st.stop()
            st.warning("该结论已被其他操作删除，请先复制需要保留的草稿。")
        _original = form_base(_form_key, _d)
        with st.form(f"deditform-{p['id']}-{_d['id']}", border=False):
            e1 = st.text_input("结论内容", value=_original.get("text", ""))
            e2 = st.text_input("依据（可空）", value=_original.get("note", ""))
            fc1, fc2 = st.columns([1, 1])
            if fc1.form_submit_button("保存", type="primary", width="stretch"):
                _changed = copy.deepcopy(_original)
                _changed.update(text=e1.strip(), note=e2.strip(), updated=datetime.now().strftime("%Y-%m-%d"))
                save_form_record(_form_key, "decisions", _d["id"], _original, _changed, parent_id=p["id"])
                st.session_state[f"dedit_open_{p['id']}_{_d['id']}"] = False
                st.rerun()
            if fc2.form_submit_button("取消", width="stretch"):
                st.session_state.pop("_edit_base_" + _form_key, None)
                st.session_state[f"dedit_open_{p['id']}_{_d['id']}"] = False
                st.rerun()
    if revoked:
        with st.expander(f"已推翻的结论（{len(revoked)} 条，仅存档）"):
            for d in revoked:
                rc1, rc2 = st.columns([10, 1.2])
                rc1.markdown(
                    f'<div style="padding:2px 0 2px 12px;margin:4px 0;">'
                    f'<span style="font-size:11.5px;color:var(--pm-ink-3);text-decoration:line-through;">'
                    f'{d.get("date","")} {d.get("text","")}</span>'
                    f'<span style="font-size:11px;color:var(--pm-ink-3);"> （{d.get("revoked_on","")} 推翻）</span></div>',
                    unsafe_allow_html=True)
                if rc2.button("删除", key=f"ddel-{p['id']}-{d['id']}", help="彻底删除该条"):
                    p["decisions"] = [x for x in decs if x["id"] != d["id"]]
                    touch(p)
                    save_reg(reg, "owner(工作台)")
                    st.rerun()
    with st.form(fresh_form_key(f"adddec-{p['id']}"), clear_on_submit=False, border=False):
        ad1, ad2, ad3 = st.columns([7, 4, 1])
        nd_txt = ad1.text_input("新增结论", placeholder="例：数据源统一走 free-stockdb，不再直连新浪",
                                label_visibility="collapsed", key=f"ndtxt-{p['id']}")
        nd_note = ad2.text_input("依据", placeholder="依据 / 来源（可空）", label_visibility="collapsed",
                                 key=f"ndnote-{p['id']}")
        nd_add = ad3.form_submit_button("添加", width="stretch", key=f"ndadd-{p['id']}")
    if nd_add and nd_txt.strip():
        p.setdefault("decisions", [])
        p["decisions"].append({"id": next_did(p["decisions"]),
                               "date": datetime.now().strftime("%Y-%m-%d"),
                               "text": nd_txt.strip(),
                               "note": nd_note.strip(),
                               "status": "active"})
        touch(p)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"adddec-{p['id']}", [f"ndtxt-{p['id']}", f"ndnote-{p['id']}"])
        st.rerun()


def ui_progress_block(p):
    """主要进展（流水，只增；老板可逐条删）。"""
    st.markdown("#### 主要进展")
    with st.form(fresh_form_key(f"log-{p['id']}"), clear_on_submit=False, border=False):
        lg1, lg2 = st.columns([11, 1])
        entry = lg1.text_input("记录一条进展", placeholder="例：已跑通首轮回测，净值 +3.2%",
                               label_visibility="collapsed")
        logged = lg2.form_submit_button("记录", type="primary", width="stretch")
    if logged and entry.strip():
        p.setdefault("progress_log", []).append({"date": datetime.now().strftime("%Y-%m-%d"),
                                                "text": entry.strip()})
        touch(p)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"log-{p['id']}")
        st.rerun()
    logs = list(reversed(p.get("progress_log") or []))[:12]
    if logs:
        for e in logs:
            lc1, lc2 = st.columns([11, 1])
            lc1.markdown(
                f'<div style="border-left:1px solid var(--pm-line);padding:1px 0 1px 12px;margin:6px 0;">'
                f'<span style="font-size:11.5px;color:var(--pm-ink-3);">{e.get("date","")}</span>&nbsp;&nbsp;'
                f'<span style="font-size:12.5px;color:var(--pm-ink);">{e.get("text","")}</span></div>',
                unsafe_allow_html=True)
            if lc2.button("删", key=f"plogdel-{p['id']}-{e.get('date','')}-{abs(hash(e.get('text','')))%99999}",
                          help="删除这条进展"):
                p["progress_log"] = [x for x in p["progress_log"] if x is not e]
                touch(p)
                save_reg(reg, "owner(工作台)")
                st.rerun()
    else:
        st.caption("还没有进展记录。")


def ui_params_block(p):
    """关键参数当前值快照。"""
    st.markdown("#### 关键参数")
    params = p.get("params") or []
    if params:
        st.dataframe(
            [{"参数": q.get("name", ""), "当前值": q.get("value", ""), "更新": q.get("updated", "")}
             for q in params],
            width="stretch", hide_index=True)
    else:
        st.caption("还没有记录关键参数。")


def ui_files_block(p):
    """用到的文件（圆点表示路径是否存在）。"""
    st.markdown("#### 用到的文件")
    files = p.get("files") or []
    if files:
        for f in files:
            fp = f.get("path", "")
            ok = bool(fp) and Path(fp).exists()
            dot = "#4E7A47" if ok else "#B08A4A"
            miss = "" if ok else '<span style="color:#B08A4A;font-size:11px;">（缺失）</span>'
            st.markdown(
                f'<div style="margin:4px 0;font-size:12.5px;color:var(--pm-ink-2);">'
                f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
                f'background:{dot};margin-right:8px;vertical-align:middle;"></span>'
                f'<code>{fp}</code> {miss} '
                f'<span style="color:var(--pm-ink-3);">{f.get("note", "")}</span></div>',
                unsafe_allow_html=True)
    else:
        st.caption("还没有登记相关文件。")


def ui_ai_logs_block(p):
    """日志信息：AI 生成的日志文件清单。"""
    st.markdown("#### 日志信息")
    st.caption("AI 生成的日志文件清单（名称 / 地址 / 日期）。AI 可直接往本栏目追加。")
    ai_logs = p.get("ai_logs") or []
    if ai_logs:
        for g in ai_logs:
            nm = g.get("name", "")
            fp = g.get("path", "")
            dt = g.get("date", "")
            nt = g.get("note", "")
            ac1, ac2 = st.columns([11, 1])
            ac1.markdown(
                '<div style="margin:5px 0;font-size:12.5px;color:var(--pm-ink-2);">'
                '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
                f'background:{ACCENT};margin-right:8px;vertical-align:middle;"></span>'
                f'<b>{nm}</b>'
                + (f' <code>{fp}</code>' if fp else '')
                + (f' <span style="color:var(--pm-ink-3);">{dt}</span>' if dt else '')
                + (f' <span style="color:var(--pm-ink-3);">{nt}</span>' if nt else '')
                + '</div>', unsafe_allow_html=True)
            if ac2.button("删", key=f"ailogdel-{p['id']}-{abs(hash(nm+fp+dt))%99999}",
                          help="删除这条 AI 日志条目"):
                p["ai_logs"] = [x for x in p["ai_logs"] if x is not g]
                touch(p)
                save_reg(reg, "owner(工作台)")
                st.rerun()
    else:
        st.caption("还没有 AI 日志条目。")
    with st.form(fresh_form_key(f"addlog-{p['id']}"), clear_on_submit=False, border=False):
        l1, l2, l3, l4 = st.columns([3, 5, 2, 1])
        ln_name = l1.text_input("日志名称", placeholder="日志名称", label_visibility="collapsed",
                                key=f"lnname-{p['id']}")
        ln_path = l2.text_input("日志地址", placeholder=r"日志地址，如 H:\...\run.log",
                                label_visibility="collapsed", key=f"lnpath-{p['id']}")
        ln_note = l3.text_input("备注", placeholder="备注（可空）", label_visibility="collapsed",
                                key=f"lnnote-{p['id']}")
        ln_add = l4.form_submit_button("添加", width="stretch", key=f"lnadd-{p['id']}")
    if ln_add and (ln_name.strip() or ln_path.strip()):
        p.setdefault("ai_logs", [])
        p["ai_logs"].append({"name": ln_name.strip() or "(未命名)",
                             "path": ln_path.strip(),
                             "date": datetime.now().strftime("%Y-%m-%d"),
                             "note": ln_note.strip()})
        touch(p)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"addlog-{p['id']}", [f"lnname-{p['id']}", f"lnpath-{p['id']}", f"lnnote-{p['id']}"])
        st.rerun()


DEVLOGS_DIR = r"H:\github\pm-hub\devlogs"


def _devlog_write_file(pid, text):
    """把长文落盘成本地 md 文件，返回 (文件名, 绝对路径)。"""
    d = Path(DEVLOGS_DIR) / str(pid)
    d.mkdir(parents=True, exist_ok=True)
    nm = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".md"
    fp = d / nm
    fp.write_text(text, encoding="utf-8")
    return nm, str(fp)


def _open_local(pth, reveal=False):
    """用系统默认程序打开文件；reveal=True 则在资源管理器里定位它。"""
    try:
        if not pth or not Path(pth).exists():
            st.error("路径不存在，无法打开：" + str(pth))
            return False
        os.startfile(str(Path(pth).parent if reveal else pth))  # noqa
        return True
    except Exception as e:
        st.error(str(e))
        return False


def ui_dev_logs_block(p):
    """我的日志：仅老板本人可写，AI 只读。
    两种形态：① 短文字；② 长文 / 已有文件 —— 只记文件名 + 路径，点按钮在本地打开。"""
    st.markdown(
        '#### 我的日志 <span style="font-size:10.5px;color:#B06A3B;'
        'border:1px solid rgba(176,106,59,.45);border-radius:999px;padding:1px 9px;'
        'margin-left:8px;vertical-align:middle;letter-spacing:.3px;">仅本人可写</span>',
        unsafe_allow_html=True)
    st.caption("只有你本人能写；AI 不得读取后改写、更不得代写本栏目。"
               "内容多时用「记录长文 / 已有文件」存成文件，列表只留文件名与路径，界面不会变繁琐。")
    dev_logs = p.get("dev_logs") or []
    if dev_logs:
        for oi in range(len(dev_logs) - 1, -1, -1):
            e = dev_logs[oi]
            txt = e.get("text", "") or ""
            fp = e.get("file_path", "") or ""
            fn = e.get("file_name", "") or (Path(fp).name if fp else "")
            uid = oi  # 用索引做 key：稳定（hash() 跨进程会变）
            dc1, dc2, dc3 = st.columns([10, 2, 1])
            long_no_file = (not fn) and len(txt) > 300
            shown = (txt[:120] + "…") if long_no_file else txt
            with dc1:
                head = (f'<span style="font-size:11.5px;color:#B06A3B;white-space:nowrap;">'
                        f'{e.get("date", "")}</span>&nbsp;&nbsp;'
                        f'<span style="font-size:12.5px;color:var(--pm-ink);overflow-wrap:anywhere;">'
                        f'{html.escape(shown)}</span>')
                if fn:
                    okf = Path(fp).exists() if fp else False
                    dot = "#4E7A47" if okf else "#B08A4A"
                    head += (
                        f'<div style="margin-top:3px;font-size:12px;color:var(--pm-ink);">'
                        f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
                        f'background:{dot};margin-right:7px;vertical-align:middle;"></span>'
                        f'<b>{html.escape(fn)}</b>'
                        + ('<span style="color:#B08A4A;font-size:11px;">（路径不存在）</span>' if not okf else '')
                        + f'</div><div style="margin-left:13px;"><code style="font-size:11px;'
                          f'word-break:break-all;">'
                          f'{html.escape(fp)}</code></div>')
                st.markdown(
                    f'<div style="border-left:2px solid rgba(176,106,59,.45);padding:1px 0 1px 12px;margin:6px 0;">'
                    f'{head}</div>', unsafe_allow_html=True)
                if long_no_file:
                    st.caption("全文共 %d 字，已折叠。" % len(txt))
                    with st.expander("展开全文"):
                        st.markdown(
                            f'<div style="max-height:420px;overflow:auto;white-space:pre-wrap;'
                            f'font-size:12.5px;line-height:1.85;color:var(--pm-ink);">'
                            f'{html.escape(txt)}</div>', unsafe_allow_html=True)
            with dc2:
                if fn:
                    if st.button("打开", key=f"devlogopen-{p['id']}-{uid}", width="stretch",
                                 help="用系统默认程序打开该文件"):
                        _open_local(fp)
                    if st.button("目录", key=f"devlogdir-{p['id']}-{uid}", width="stretch",
                                 help="在资源管理器里定位该文件"):
                        _open_local(fp, reveal=True)
                elif long_no_file:
                    if st.button("存为文件", key=f"devlog2file-{p['id']}-{uid}", width="stretch",
                                 help="把这篇长文存成本地 md 文件，列表里只留摘要和链接"):
                        nm2, fp2 = _devlog_write_file(p["id"], txt)
                        e["file_name"] = nm2
                        e["file_path"] = fp2
                        e["text"] = txt[:60].replace("\n", " ") + ("…" if len(txt) > 60 else "")
                        touch(p)
                        save_reg(reg, "owner(工作台)")
                        st.toast("已存为文件：" + fp2)
                        st.rerun()
            with dc3:
                if st.button("删", key=f"devlogdel-{p['id']}-{uid}", help="删除这条我的日志"):
                    p["dev_logs"] = [x for x in p["dev_logs"] if x is not e]
                    touch(p)
                    save_reg(reg, "owner(工作台)")
                    st.rerun()
    else:
        st.caption("还没有你的日志。")

    with st.form(fresh_form_key(f"devlog-{p['id']}"), clear_on_submit=False, border=False):
        d1, d2 = st.columns([11, 1])
        dev_txt = d1.text_input("写一条我的日志", placeholder="短内容直接写这行，例：今天决定放弃 X 方案",
                                label_visibility="collapsed", key=f"devtxt-{p['id']}")
        dev_add = d2.form_submit_button("记录", type="primary", width="stretch", key=f"devadd-{p['id']}")
    if dev_add and dev_txt.strip():
        p.setdefault("dev_logs", [])
        p["dev_logs"].append({"date": datetime.now().strftime("%Y-%m-%d"), "text": dev_txt.strip()})
        touch(p)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"devlog-{p['id']}", [f"devtxt-{p['id']}"])
        st.rerun()

    with st.expander("记录长文 / 已有文件（内容多时用这个）"):
        st.caption("**已有文件**：只填「文件路径」即可 —— 不需要上传，只记文件名 + 路径，之后点「打开」在本地打开。"
                   "**没有文件但内容很长**：把全文粘到「长文内容」，保存时自动写成 md 文件，列表里只留摘要和链接。")
        with st.form(fresh_form_key(f"devfile-{p['id']}"), clear_on_submit=False, border=False):
            g1 = st.text_input("文件路径（可留空）", placeholder=r"例：H:\notes\骆驼祥子读书笔记.md",
                               key=f"devfp-{p['id']}")
            g2 = st.text_area("长文内容（仅在未填文件路径时使用）", height=130,
                              placeholder="把长文粘贴到这里，保存时会写成文件，界面只显示摘要",
                              key=f"devft-{p['id']}")
            g3, g4 = st.columns([5, 1])
            g3s = g3.text_input("摘要（列表里显示这一行）",
                                placeholder="例：骆驼祥子读书笔记 —— 祥子的三次起落",
                                label_visibility="collapsed", key=f"devfs-{p['id']}")
            okf = g4.form_submit_button("记录", type="primary", width="stretch", key=f"devfok-{p['id']}")
        if okf:
            fp_in = g1.strip().strip('"')
            body = g2.strip()
            summ = g3s.strip()
            if not fp_in and body:
                nm, fp_in = _devlog_write_file(p["id"], body)
                summ = summ or body[:60].replace("\n", " ")
                st.success("已自动存为文件：" + fp_in)
            elif fp_in and not Path(fp_in).exists():
                st.warning("该路径当前不存在，仍会记录；之后点「打开」会失败，请核对路径。")
            if fp_in or body:
                p.setdefault("dev_logs", []).append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "text": summ or (Path(fp_in).name if fp_in else ""),
                    "file_name": (Path(fp_in).name if fp_in else ""),
                    "file_path": fp_in})
                touch(p)
                save_reg(reg, "owner(工作台)")
                reset_form_after_save(f"devfile-{p['id']}", [f"devfp-{p['id']}", f"devft-{p['id']}", f"devfs-{p['id']}"])
                st.rerun()


REL_TYPES = ["数据供给", "接口调用", "顺序依赖（前者须先完成）", "共享配置", "产出汇入", "其他"]


def next_rid(rels):
    n = 0
    for r in rels:
        rid = str(r.get("id", ""))
        if rid.startswith("r") and rid[1:].isdigit():
            n = max(n, int(rid[1:]))
    return "r%d" % (n + 1)


def _svg_text_w(s, size=11):
    return sum(size if ord(ch) > 127 else size * 0.56 for ch in str(s)) + 10


def _clip_display(s, max_units=26):
    """按显示宽度截断（中文算 2 个单位），避免中文名被切得过早。"""
    out, used = "", 0
    for ch in str(s):
        u = 2 if ord(ch) > 127 else 1
        if used + u > max_units:
            return out + "…"
        out += ch
        used += u
    return out


def _order_nodes(kids, rels):
    """按关系做稳定拓扑排序：没有入边的（数据源）排前面。"""
    ids = [k["id"] for k in kids]
    indeg = {i: 0 for i in ids}
    out = {i: [] for i in ids}
    for r in rels:
        a, b = r.get("from"), r.get("to")
        if a in indeg and b in indeg and a != b:
            out[a].append(b)
            indeg[b] += 1
    queue = [i for i in ids if indeg[i] == 0]
    order, seen = [], set()
    while queue:
        n = queue.pop(0)
        if n in seen:
            continue
        seen.add(n)
        order.append(n)
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    for i in ids:
        if i not in seen:
            order.append(i)
    return order


def relations_svg(kids, rels):
    """把小项目之间的关系画成连线图。返回 SVG 字符串。"""
    n = len(kids)
    if n == 0:
        return ""
    kids = sorted(kids, key=lambda k: _order_nodes(kids, rels).index(k["id"]))
    cols = 3 if n >= 3 else n
    rows = (n + cols - 1) // cols
    w, h, gx, gy, pad = 186, 46, 42, 62, 14
    W = pad * 2 + cols * w + (cols - 1) * gx
    H = pad * 2 + rows * h + (rows - 1) * gy
    pos = {}
    for i, k in enumerate(kids):
        r, c = divmod(i, cols)
        x = pad + c * (w + gx)
        y = pad + r * (h + gy)
        pos[k["id"]] = (x, y, x + w / 2, y + h / 2)
    name = {k["id"]: (k.get("name") or "") for k in kids}
    out = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx;" '
           'xmlns="http://www.w3.org/2000/svg" role="img">' % (W, H, W),
           '<title>小项目关系图</title>',
           '<defs><marker id="reArrow" viewBox="0 0 10 10" refX="8" refY="5" '
           'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
           '<path d="M2 1L8 5L2 9" fill="none" stroke="var(--pm-ink-3)" stroke-width="1.5" '
           'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>']
    # 先算每条边的路径与标签位置
    edges = []
    for r in rels:
        a, b = r.get("from"), r.get("to")
        if a not in pos or b not in pos:
            continue
        if a == b:
            x, y, cx, cy = pos[a]
            edges.append(("M %d %d C %d %d, %d %d, %d %d"
                          % (cx - 14, y, cx - 26, y - 32, cx + 26, y - 32, cx + 14, y),
                          cx - 4, y - 40, r.get("type", "")))
            continue
        _, _, x1, y1 = pos[a]
        _, _, x2, y2 = pos[b]
        dx, dy = x2 - x1, y2 - y1
        L = max((dx * dx + dy * dy) ** 0.5, 1)
        off = 30
        cxp, cyp = (x1 + x2) / 2 - dy / L * off, (y1 + y2) / 2 + dx / L * off
        # 二次贝塞尔的真实中点，标签落在这上面才贴住线
        qx, qy = (x1 + 2 * cxp + x2) / 4, (y1 + 2 * cyp + y2) / 4
        edges.append(("M %d %d Q %d %d %d %d" % (x1, y1, cxp, cyp, x2, y2),
                      qx, qy, r.get("type", "")))
    # 1) 连线（两端会被节点盖住）
    for d, _, _, _ in edges:
        out.append('<path d="%s" fill="none" stroke="var(--pm-ink-3)" stroke-width="1.5" '
                   'marker-end="url(#reArrow)"/>' % d)
    # 2) 节点
    for k in kids:
        x, y, cx, cy = pos[k["id"]]
        nm = name[k["id"]]
        shown = _clip_display(nm, 26)
        out.append('<g><rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#FFFFFF" '
                   'stroke="%s" stroke-width="1"/>' % (x, y, w, h, ACCENT))
        out.append('<text x="%d" y="%d" font-size="12.5" fill="var(--pm-ink)" font-family="sans-serif" '
                   'text-anchor="middle" dominant-baseline="central">%s</text>' % (cx, cy, shown))
        out.append('</g>')
    # 3) 关系标签（不透明底 + 居中压在线上，最上层）
    for _, lx, ly, lbl in edges:
        if not lbl:
            continue
        tw = _svg_text_w(lbl)
        out.append('<rect x="%d" y="%d" width="%d" height="17" rx="3" fill="#FFFFFF"/>'
                   % (lx - tw / 2, ly - 8.5, tw))
        out.append('<text x="%d" y="%d" font-size="11" fill="var(--pm-ink-2)" font-family="sans-serif" '
                   'text-anchor="middle" dominant-baseline="central">%s</text>' % (lx, ly, lbl))
    out.append('</svg>')
    return "".join(out)


def ui_relations_block(prog):
    """小项目关系（整合）：连线图 + 关系清单 + 整合说明。仅在 L1 超大项目页使用。"""
    st.markdown("#### 小项目关系（整合）")
    st.caption("这几个小项目是怎么串起来的：谁给谁供数据、谁等谁先完成、谁的产出汇到哪里。"
               "AI 读本项目时会看到这张表。")
    kids = child_projects(projects, prog["id"])
    rels = prog.get("relations") or []

    integration = prog.get("integration") or ""
    if integration:
        st.markdown(
            f'<div class="pmcard" style="padding:12px 14px;margin:6px 0 12px;">'
            f'<div class="gloss"></div>'
            f'<div style="font-size:12.5px;color:var(--pm-ink-2);line-height:1.8;">{integration}</div></div>',
            unsafe_allow_html=True)
    else:
        st.caption("（还没有整合说明，可在下面补一段「整体怎么串起来」）")

    if kids:
        svg = relations_svg(kids, [r for r in rels if r.get("from") in
                                   {k["id"] for k in kids} and r.get("to") in {k["id"] for k in kids}])
        if svg and rels:
            st.markdown(svg, unsafe_allow_html=True)
        elif svg:
            st.markdown(svg, unsafe_allow_html=True)
            st.caption("还没有连线的说明——用下面的表单加一条关系。")
    else:
        st.caption("还没有小项目，无法建立关系。先在下面新建小项目。")

    # 关系清单
    kid_name = {k["id"]: (k.get("name") or k["id"]) for k in kids}
    if rels:
        for r in rels:
            rc1, rc2 = st.columns([11, 1])
            rc1.markdown(
                f'<div style="margin:4px 0;font-size:12.5px;color:var(--pm-ink);">'
                f'<b>{kid_name.get(r.get("from"), r.get("from", "?"))}</b>'
                f' <span style="color:{ACCENT};">──{r.get("type","")}──▶</span> '
                f'<b>{kid_name.get(r.get("to"), r.get("to", "?"))}</b>'
                + (f' <span style="color:var(--pm-ink-3);">{r.get("note","")}</span>' if r.get("note") else '')
                + '</div>', unsafe_allow_html=True)
            if rc2.button("删", key=f"reldel-{prog['id']}-{r['id']}", help="删除这条关系"):
                prog["relations"] = [x for x in rels if x["id"] != r["id"]]
                touch(prog)
                save_reg(reg, "owner(工作台)")
                st.rerun()
    # 新增关系
    if len(kids) >= 1:
        with st.form(fresh_form_key(f"addrel-{prog['id']}"), clear_on_submit=False, border=False):
            f1, f2, f3 = st.columns([3, 3, 3])
            opts = [k["id"] for k in kids]
            rf = f1.selectbox("从", opts, format_func=lambda x: kid_name.get(x, x),
                              key=f"relfrom-{prog['id']}")
            rt = f2.selectbox("到", opts, format_func=lambda x: kid_name.get(x, x),
                              key=f"relto-{prog['id']}")
            rty = f3.selectbox("关系", REL_TYPES, key=f"reltype-{prog['id']}")
            f4, f5 = st.columns([11, 1])
            rnote = f4.text_input("说明", placeholder="例：纸浆价格表由前者产出，后者直接读",
                                  label_visibility="collapsed", key=f"relnote-{prog['id']}")
            radd = f5.form_submit_button("添加关系", width="stretch", key=f"reladd-{prog['id']}")
        if radd:
            prog.setdefault("relations", [])
            prog["relations"].append({"id": next_rid(prog["relations"]),
                                      "from": rf, "to": rt,
                                      "type": rty, "note": rnote.strip()})
            touch(prog)
            save_reg(reg, "owner(工作台)")
            reset_form_after_save(f"addrel-{prog['id']}", [f"relfrom-{prog['id']}", f"relto-{prog['id']}", f"reltype-{prog['id']}", f"relnote-{prog['id']}"])
            st.rerun()
    # 整合说明编辑
    with st.expander("编辑整合说明"):
        _form_key = f"integration-{prog['id']}"
        _original = form_base(_form_key, prog)
        with st.form(f"integ-{prog['id']}", border=False):
            it = st.text_area("整合说明", value=_original.get("integration") or "", height=110,
                              placeholder="用一段话说明这几个小项目如何构成一个大工程、数据怎么流、先后顺序是什么。")
            if st.form_submit_button("保存", type="primary"):
                _changed = copy.deepcopy(_original)
                _changed["integration"] = it.strip()
                save_form_record(_form_key, "projects", prog["id"], _original, _changed)
                st.rerun()


def render_program_detail(pid):
    """L1 详情：战略目标 + 小项目关系（整合）+ 第二级列表 + 通用信息区块。"""
    prog = next((x for x in projects if x.get("id") == pid), None)
    if prog is None:
        back_to_programs()
        st.rerun()
    ensure_project_fields(prog)
    agg = rollup(projects, prog)
    color = STATUS_COLOR.get(prog.get("status"), "var(--pm-ink-3)")

    st.markdown(
        f'<div style="font-size:12px;color:var(--pm-ink-3);margin-bottom:6px;">'
        f'<a href="javascript:void(0)" style="color:var(--pm-accent);text-decoration:none;">项目总览</a>'
        f' <span style="color:var(--pm-ink-4);">/</span> '
        f'<span style="color:var(--pm-ink-2);">{prog.get("name", "")}</span></div>',
        unsafe_allow_html=True)
    st.button("← 返回超大项目列表", on_click=back_to_programs)

    st.markdown(
        f'<div class="pmcard" style="padding:18px 20px;margin-top:8px;">'
        f'<div class="gloss"></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'<span style="font-weight:800;font-size:21px;color:var(--pm-ink);">{prog.get("name", "")}</span>'
        f'{badge(color, STATUS_CN.get(prog.get("status"), ""))}</div>'
        f'<div style="color:var(--pm-ink-2);font-size:13.5px;line-height:1.75;margin-top:10px;">{prog.get("description", "")}</div>'
        f'<div style="margin-top:13px;font-size:12.5px;color:var(--pm-ink-2);">'
        f'阶段 {prog.get("stage", "—")}　·　小项目 {agg["n_kids"]}　·　'
        f'任务 {agg["n_tasks"]}（完成 {agg["done"]} · 进行中 {agg["doing"]}）</div>'
        f'<div style="margin:9px 0 4px;">{progress_html(agg["progress"])}<br><span style="font-size:11px;color:var(--pm-ink-3);">{agg["progress_source"]}</span></div>'
        f'{("<div style=\'font-size:12px;color:var(--pm-ink-2);margin-top:8px;\'>" + str(prog.get("notes")) + "</div>") if prog.get("notes") else ""}'
        f'</div>', unsafe_allow_html=True)

    # ---- 战略目标 ----
    goals = reconcile_goals(prog)
    st.markdown("#### 战略目标")
    st.caption("超大项目层面的验收线；小项目任务是它的拆解。")
    if not goals:
        st.caption("还没有战略目标。")
    for g in list(goals):
        gc1, gc2 = st.columns([11, 1])
        ck = gc1.checkbox(g.get("text") or "(未命名目标)", value=bool(g.get("done")),
                          key=f"pgoal-{prog['id']}-{g['id']}")
        if ck != bool(g.get("done")):
            g["done"] = ck
            recompute_progress(prog)
            touch(prog)
            save_reg(reg, "owner(工作台)")
            st.rerun()
        if gc2.button("删除", key=f"pdel-{prog['id']}-{g['id']}"):
            prog["goals"] = [x for x in goals if x.get("id") != g["id"]]
            recompute_progress(prog)
            touch(prog)
            save_reg(reg, "owner(工作台)")
            st.rerun()
    with st.form(fresh_form_key(f"paddgoal-{prog['id']}"), clear_on_submit=False, border=False):
        a1, a2 = st.columns([11, 1])
        ng = a1.text_input("新增战略目标", placeholder="例：数据底座恢复日更",
                           label_visibility="collapsed")
        ok = a2.form_submit_button("添加", width="stretch")
    if ok and ng.strip():
        goals.append({"id": next_gid(goals), "text": ng.strip(), "done": False})
        recompute_progress(prog)
        touch(prog)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"paddgoal-{prog['id']}")
        st.rerun()

    # ---- 小项目关系（整合）----
    ui_relations_block(prog)

    # ---- 第二级：小项目列表 ----
    st.markdown("#### 小项目（第二级）")
    st.caption("点「查看详情与任务」进入第三级。")
    kids = child_projects(projects, prog["id"])
    if not kids:
        st.info("本超大项目还没有小项目。用下面的表单新建一个；已经存在的独立小项目也可以在它的详情页里改归属到这里。")
    kcols = st.columns(3)
    for i, k in enumerate(kids):
        with kcols[i % 3]:
            st.markdown(card_project_html(k), unsafe_allow_html=True)
            st.button("查看详情与任务", key=f"openkid-{k['id']}", width="stretch",
                      on_click=open_subproject, args=(k["id"],))
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # ---- 跨项目任务总览 ----
    rows = []
    for k in kids:
        for t in (k.get("tasks") or []):
            rows.append({"小项目": k.get("name", ""), "任务": t.get("title", ""),
                         "状态": TASK_STATUS_CN.get(t.get("status"), t.get("status", "")),
                         "批次": t.get("batch", ""), "验收": t.get("acceptance", ""),
                         "更新": t.get("updated", "")})
    if rows:
        st.markdown("#### 本超大项目全部任务")
        st.dataframe(rows, width="stretch", hide_index=True)

    st.divider()
    st.caption("以下为超大项目层面的信息（与小项目同一套栏目）。")

    # ---- 结论与裁决 ----
    ui_decisions_block(prog)

    # ---- 主要进展 ----
    ui_progress_block(prog)

    # ---- 关键参数 ----
    ui_params_block(prog)

    # ---- 用到的文件 ----
    ui_files_block(prog)

    # ---- 日志信息（AI 生成）----
    ui_ai_logs_block(prog)

    # ---- 我的日志（仅本人可写）----
    ui_dev_logs_block(prog)

    st.divider()

    # ---- 新建小项目 ----
    with st.expander("新建小项目并挂到本超大项目"):
        with st.form(fresh_form_key(f"newkid-{prog['id']}"), clear_on_submit=False, border=False):
            n1, n2 = st.columns([2, 3])
            nn = n1.text_input("小项目名称", placeholder="例：数据底座修复")
            nd = n2.text_input("一句话说明", placeholder="这个项目要解决什么")
            n3, n4, n5 = st.columns(3)
            ncat = n3.selectbox("类别", list(CAT_CN), index=list(CAT_CN).index(prog.get("category", "tool"))
                                if prog.get("category") in CAT_CN else 0,
                                format_func=lambda x: CAT_CN.get(x, x))
            nst = n4.selectbox("状态", ["active", "warm", "cold"], format_func=lambda x: STATUS_CN[x])
            nroot = n5.text_input("根目录（可空）", placeholder=r"G:\...")
            nsub = st.form_submit_button("创建", type="primary")
        if nsub and nn.strip():
            nid = slug(nn)
            if any(x.get("id") == nid for x in projects):
                st.error("已存在同名项目 id：%s" % nid)
            else:
                np_ = {"id": nid, "name": nn.strip(), "kind": "project", "parent": prog["id"],
                       "category": ncat, "status": nst, "stage": "新建",
                       "description": nd.strip(), "paths": {"root": nroot.strip(), "data": [], "wsl": []},
                       "platform": [], "data_deps": [], "entry_points": [], "docs": [],
                       "notes": "", "health": "ok", "para": "project",
                       "last_activity": datetime.now().strftime("%Y-%m-%d"),
                       "goals": [], "progress_log": [], "files": [], "params": [],
                       "ai_logs": [], "dev_logs": [], "tasks": [], "progress": None}
                projects.append(np_)
                reg["projects"] = projects
                touch(prog)
                save_reg(reg, "owner(工作台)")
                reset_form_after_save(f"newkid-{prog['id']}")
                st.toast("已创建小项目：" + nn.strip())
                st.rerun()


def set_task_status(pid, tid, status):
    """按钮回调：改第三级任务状态，并重算项目进度。"""
    for p in projects:
        if p.get("id") != pid:
            continue
        for t in norm_tasks(p):
            if t.get("id") == tid:
                t["status"] = status
                t["updated"] = datetime.now().strftime("%Y-%m-%d")
        recompute_progress(p)
        touch(p)
        save_reg(reg, "owner(工作台)")
        break


def render_task_block(prog, p):
    """第三级：任务清单。每条任务 = 一份可交付 AI 的任务单。"""
    st.markdown("#### 任务清单（第三级）")
    st.caption("项目状态即任务状态。每条任务都带「输入 / 交付物 / 验收标准」，"
               "导出后即是一份完整指令，不要用一句话去指挥 AI。")
    tasks = sorted(norm_tasks(p), key=lambda x: (
        int(str(x.get("id", "t0"))[1:]) if str(x.get("id", "t0"))[1:].isdigit() else 999))
    _task_ids = {item.get("id") for item in tasks}
    _orphaned = []
    _prefix = f"_edit_base_task-{p['id']}-"
    for _key in list(st.session_state):
        if _key.startswith(_prefix):
            _record = st.session_state[_key]
            if _record.get("id") not in _task_ids:
                _orphaned.append(_record)
    ts = task_stats(p)
    dots = "　".join(
        f'<span style="color:{TASK_STATUS_COLOR[k]};font-size:12px;">'
        f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{TASK_STATUS_COLOR[k]};'
        f'margin-right:5px;vertical-align:middle;"></span>{TASK_STATUS_CN[k]} {ts[k]}</span>'
        for k in TASK_STATUS_ORDER if ts[k])
    st.markdown(
        f'<div style="font-size:12.5px;color:var(--pm-ink-2);margin:2px 0 10px;">共 {ts["total"]} 条'
        + ("　·　" + dots if dots else "") + '</div>', unsafe_allow_html=True)

    if not tasks:
        st.info("还没有任务。先在下面把这件事拆成 3–8 条可以独立交付的任务，"
                "每条都写清验收标准，再分批交给 AI。")
        visible_tasks = _orphaned
    else:
        view_key = f"task-view-{p['id']}"
        focused_key = f"focused-task-{p['id']}"
        if st.session_state.get("focus_task_project_id") == p["id"]:
            focused_id = st.session_state.pop("focus_task_id", None)
            st.session_state.pop("focus_task_project_id", None)
            if focused_id:
                st.session_state[focused_key] = focused_id
                st.session_state[view_key] = "指定任务"
        options = ["未完成", "全部", "已完成"]
        if st.session_state.get(focused_key):
            options.append("指定任务")
        task_view = st.radio("任务筛选", options, horizontal=True, key=view_key)
        visible_tasks = [t for t in tasks if task_view == "全部" or
                         (task_view == "指定任务" and t.get("id") == st.session_state.get(focused_key)) or
                         (task_view == "已完成" and t.get("status") == "done") or
                         (task_view == "未完成" and t.get("status") != "done")]
        visible_tasks += [t for t in _orphaned if task_view in ("全部", "未完成", "指定任务")]
        if not visible_tasks:
            st.caption("此筛选条件下没有任务。")

    for t in visible_tasks:
        stt = t.get("status") if t.get("status") in TASK_STATUS_CN else "todo"
        with st.container(border=True):
            if t in _orphaned:
                st.warning("该任务已被其他操作删除，以下内容是本会话的原记录。请先复制需要保留的草稿。")
            c1, c2 = st.columns([8, 4])
            with c1:
                ck = st.checkbox(t.get("title") or "(未命名任务)", value=(stt == "done"),
                                 key=f"tk-{p['id']}-{t.get('id')}-{stt}",
                                 help="勾选 = 已完成（等价于把状态置为「已完成」）")
                if ck != (stt == "done"):
                    t["status"] = "done" if ck else "todo"
                    t["updated"] = datetime.now().strftime("%Y-%m-%d")
                    recompute_progress(p)
                    touch(p)
                    save_reg(reg, "owner(工作台)")
                    st.rerun()
            with c2:
                st.markdown(
                    badge(TASK_STATUS_COLOR[stt], TASK_STATUS_CN[stt])
                    + f'<span style="color:var(--pm-ink-3);font-size:11.5px;margin-left:8px;">{t.get("id", "")}'
                    + (f'　批次 {t.get("batch")}' if t.get("batch") else "") + '</span>',
                    unsafe_allow_html=True)

            meta = []
            for lab, key in (("说明", "detail"), ("验收", "acceptance"),
                             ("输入", "inputs"), ("交付物", "outputs")):
                v = (t.get(key) or "").strip()
                if v:
                    meta.append(f'<div style="font-size:12.5px;color:var(--pm-ink-2);line-height:1.7;">'
                                f'<span style="color:var(--pm-ink-3);">{lab}</span>　{v}</div>')
            if meta:
                st.markdown("".join(meta), unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:12px;color:#B08A4A;">'
                            '这条任务还没有验收标准 —— 交给 AI 前务必补上，否则产出无法判定。</div>',
                            unsafe_allow_html=True)

            bc = st.columns([1, 1, 1, 1, 2])
            for i, s in enumerate(TASK_STATUS_ORDER):
                bc[i].button(TASK_STATUS_CN[s], key=f"ts-{p['id']}-{t.get('id')}-{s}",
                             disabled=(s == stt), width="stretch",
                             on_click=set_task_status, args=(p["id"], t.get("id"), s),
                             help="点击切换状态")
            with bc[4]:
                st.markdown(
                    f'<div style="font-size:11px;color:var(--pm-ink-4);text-align:right;padding-top:6px;">'
                    f'更新 {t.get("updated") or "—"}</div>', unsafe_allow_html=True)

            with st.expander("AI 任务指令（复制后直接交给 AI）"):
                txt = task_pack_text(prog, p, t)
                st.code(txt, language=None)
                st.download_button("下载本任务包 .md", data=txt,
                                   file_name=f"taskpack-{p['id']}-{t.get('id')}.md",
                                   key=f"dl-{p['id']}-{t.get('id')}")
            with st.expander("编辑 / 删除这条任务"):
                _form_key = f"task-{p['id']}-{t.get('id')}"
                _original = form_base(_form_key, t)
                with st.form(f"edt-{p['id']}-{t.get('id')}", border=False):
                    e1 = st.text_input("标题", value=_original.get("title") or "")
                    e2 = st.text_area("说明", value=_original.get("detail") or "", height=68)
                    e3 = st.text_input("验收标准", value=_original.get("acceptance") or "")
                    e4, e5, e6 = st.columns(3)
                    e4 = e4.text_input("输入", value=_original.get("inputs") or "")
                    e5 = e5.text_input("交付物", value=_original.get("outputs") or "")
                    e6 = e6.text_input("批次", value=_original.get("batch") or "")
                    f1, f2 = st.columns([1, 1])
                    saved = f1.form_submit_button("保存", type="primary", width="stretch")
                    killed = f2.form_submit_button("删除任务", width="stretch")
                if saved:
                    _changed = copy.deepcopy(_original)
                    _changed.update({"title": e1.strip(), "detail": e2.strip(), "acceptance": e3.strip(),
                                     "inputs": e4.strip(), "outputs": e5.strip(), "batch": e6.strip(),
                                     "updated": datetime.now().strftime("%Y-%m-%d")})
                    save_form_record(_form_key, "tasks", t.get("id"), _original, _changed, parent_id=p["id"])
                    st.toast("已保存")
                    st.rerun()
                if killed:
                    save_form_record(_form_key, "tasks", t.get("id"), _original, None, parent_id=p["id"])
                    st.toast("已删除任务")
                    st.rerun()

    # ---- 新增任务 ----
    with st.expander("新增任务（建议一次拆 3–8 条）", expanded=not tasks):
        with st.form(fresh_form_key(f"addtask-{p['id']}"), clear_on_submit=False, border=False):
            a1, a2 = st.columns([3, 3])
            nt_title = a1.text_input("任务标题", placeholder="动词开头，例：修复 free-stockdb 日更任务")
            nt_batch = a2.text_input("批次（可空）", placeholder="例：B1")
            nt_detail = st.text_area("说明（为什么做、做到什么程度）", height=68)
            nt_acc = st.text_input("验收标准（必须可判定）",
                                   placeholder="例：连续 3 个交易日收盘后数据自动更新，日志无报错")
            b1, b2 = st.columns(2)
            nt_in = b1.text_input("输入（要读的文件/数据）", placeholder=r"G:\free-stockdb\...")
            nt_out = b2.text_input("交付物", placeholder="例：修复后的 collector.py + 运行日志")
            nt_ok = st.form_submit_button("添加任务", type="primary")
        if nt_ok and nt_title.strip():
            norm_tasks(p).append({"id": next_tid(norm_tasks(p)), "title": nt_title.strip(),
                          "detail": nt_detail.strip(), "acceptance": nt_acc.strip(),
                          "inputs": nt_in.strip(), "outputs": nt_out.strip(),
                          "batch": nt_batch.strip(), "prompt": "", "status": "todo",
                          "updated": datetime.now().strftime("%Y-%m-%d")})
            recompute_progress(p)
            touch(p)
            save_reg(reg, "owner(工作台)")
            reset_form_after_save(f"addtask-{p['id']}")
            st.toast("已添加任务")
            st.rerun()

        with st.form(fresh_form_key(f"bulktask-{p['id']}"), clear_on_submit=False, border=False):
            raw = st.text_area("批量粘贴（每行一条：标题 | 说明 | 验收标准 | 批次）", height=100,
                               placeholder="修复数据日更 | collector 定时任务未生效 | 连续 3 日自动更新 | B1")
            bulk_ok = st.form_submit_button("批量添加")
        if bulk_ok and raw.strip():
            n_add = 0
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [x.strip() for x in line.split("|")]
                norm_tasks(p).append({"id": next_tid(norm_tasks(p)), "title": parts[0],
                              "detail": parts[1] if len(parts) > 1 else "",
                              "acceptance": parts[2] if len(parts) > 2 else "",
                              "inputs": "", "outputs": "",
                              "batch": parts[3] if len(parts) > 3 else "",
                              "prompt": "", "status": "todo",
                              "updated": datetime.now().strftime("%Y-%m-%d")})
                n_add += 1
            recompute_progress(p)
            touch(p)
            save_reg(reg, "owner(工作台)")
            reset_form_after_save(f"bulktask-{p['id']}")
            st.toast("已批量添加 %d 条" % n_add)
            st.rerun()

    # ---- 任务包导出 ----
    if tasks:
        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
        d1, d2 = st.columns([3, 3])
        stamp = datetime.now().strftime("%Y%m%d")
        with d1:
            if st.button("导出任务包（仅未完成，按批次分组）", key=f"expack-{p['id']}",
                         width="stretch"):
                md = task_pack_markdown(prog, p, only_todo=True)
                fp = HUB / "reports" / f"taskpack-{p['id']}-{stamp}.md"
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(md, encoding="utf-8")
                st.session_state["last_pack"] = str(fp)
                st.toast("已导出：" + str(fp))
        with d2:
            lp = st.session_state.get("last_pack")
            if lp and Path(lp).exists() and Path(lp).stem.endswith(f"{p['id']}-{stamp}"):
                st.download_button("下载刚导出的任务包", data=Path(lp).read_bytes(),
                                   file_name=Path(lp).name, key=f"dlpack-{p['id']}",
                                   width="stretch")


def render_project_page(pid, in_overview=False):
    """L2 详情（含第三级任务清单）。in_overview=True 时带面包屑与返回。"""
    p = next((x for x in projects if x.get("id") == pid), None)
    if p is None:
        p = copy.deepcopy(st.session_state.get("_project_cache_" + pid))
        if p is None:
            st.error("项目已被删除，无法打开。")
            return
        st.warning("该项目已被其他操作删除，当前显示本会话的原记录，请先复制需要保留的草稿。")
    else:
        st.session_state.setdefault("_project_cache_" + pid, copy.deepcopy(p))
    ensure_project_fields(p)
    prog = next((x for x in projects if x.get("id") == p.get("parent")), None)
    color = STATUS_COLOR.get(p.get("status"), "var(--pm-ink-3)")

    if in_overview:
        crumb = ('项目总览 <span style="color:var(--pm-ink-4);">/</span> '
                 + (f'{prog.get("name", "")} <span style="color:var(--pm-ink-4);">/</span> ' if prog else "")
                 + f'{p.get("name", "")}')
        st.markdown(f'<div style="font-size:12px;color:var(--pm-ink-2);margin-bottom:6px;">{crumb}</div>',
                    unsafe_allow_html=True)
        b1, b2 = st.columns([2, 8])
        with b1:
            st.button("← 返回" + ("小项目列表" if prog else "总览"),
                      key="back-from-l2",
                      on_click=(back_to_program if prog else back_to_programs))
    # 非 in_overview 时（🔍 项目详情页）标题与返回按钮由调用方渲染，避免重复元素。

    st.markdown(f"### {p.get('name')} {badge(color, STATUS_CN.get(p.get('status'), ''))}",
                unsafe_allow_html=True)
    if prog:
        st.caption("所属超大项目：" + prog.get("name", ""))
    st.write(p.get("description") or "（无描述）")

    # ---- 第三级：任务清单 ----
    render_task_block(prog, p)

    goals = reconcile_goals(p)
    gd = sum(1 for g in goals if g.get("done"))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("阶段", p.get("stage") or "—")
    _pct, _source = progress_info(p)
    m2.metric("进度", f"{_pct}%" if _pct is not None else "未定", help="按任务优先、其次目标、最后手动填写的口径计算。")
    m2.caption(_source)
    m3.metric("目标", f"{gd}/{len(goals)} 完成" if goals else "未设定")
    m4.metric("最近更新", p.get("last_activity") or "—")

    # ---- 目标清单 ----
    st.markdown("#### 目标清单")
    st.caption("勾选即完成；有任务时进度按任务计算，否则按目标计算。")
    if not goals:
        st.info("还没有目标。在下面添加第一条，进度就会随目标完成情况自动计算。")
    for g in list(goals):
        gc1, gc2 = st.columns([11, 1])
        checked = gc1.checkbox(g.get("text") or "(未命名目标)", value=bool(g.get("done")),
                               key=f"goal-{p['id']}-{g['id']}")
        if checked != bool(g.get("done")):
            g["done"] = checked
            recompute_progress(p)
            touch(p)
            save_reg(reg, "owner(工作台)")
            st.rerun()
        if gc2.button("删除", key=f"del-{p['id']}-{g['id']}", help="删除该目标，进度自动重平衡"):
            p["goals"] = [x for x in goals if x.get("id") != g["id"]]
            recompute_progress(p)
            touch(p)
            save_reg(reg, "owner(工作台)")
            st.toast("已删除目标，进度已重算")
            st.rerun()
    with st.form(fresh_form_key(f"addgoal-{p['id']}"), clear_on_submit=False, border=False):
        ag1, ag2 = st.columns([11, 1])
        newg = ag1.text_input("新增目标", placeholder="写一条可验收的目标，例：打通 free-stockdb 读取",
                              label_visibility="collapsed")
        added = ag2.form_submit_button("添加", width="stretch")
    if added and newg.strip():
        goals.append({"id": next_gid(goals), "text": newg.strip(), "done": False})
        recompute_progress(p)
        touch(p)
        save_reg(reg, "owner(工作台)")
        reset_form_after_save(f"addgoal-{p['id']}")
        st.rerun()

    # ---- 结论与裁决（现行口径，AI 必须先读；可随时推翻）----
    ui_decisions_block(p)

    # ---- 主要进展 ----
    ui_progress_block(p)

    # ---- 关键参数 ----
    ui_params_block(p)

    # ---- 用到的文件 ----
    ui_files_block(p)

    # ---- 日志信息（AI 生成）----
    ui_ai_logs_block(p)

    # ---- 我的日志（仅本人可写）----
    ui_dev_logs_block(p)

    st.divider()
    root = (p.get("paths") or {}).get("root", "")
    d1, d2 = st.columns([3, 2])
    with d1:
        st.markdown("**路径**")
        st.code(root or "（待补）", language=None)
        for dp in (p.get("paths") or {}).get("data", []):
            st.code("数据: " + dp, language=None)
        for wp in (p.get("paths") or {}).get("wsl", []):
            st.code("WSL: " + wp, language=None)
        if root and Path(root).is_dir():
            if st.button("打开目录"):
                try:
                    os.startfile(root)  # noqa
                    st.toast("已打开 " + root)
                except Exception as e:
                    st.error(str(e))
        if p.get("notes"):
            st.caption("备注: " + p["notes"])
    with d2:
        st.markdown("**数据依赖**")
        for d in (p.get("data_deps") or ["—"]):
            st.write("· " + d)
        st.markdown("**使用平台**")
        for pl in (p.get("platform") or ["—"]):
            st.write("· " + pl)
        st.markdown("**层级归属**")
        st.write("· " + (prog.get("name", "") if prog else "独立小项目（不归属任何超大项目）"))
    # 目录速览
    st.markdown("#### 目录速览（顶层）")
    if root and Path(root).is_dir():
        rows = []
        try:
            for ch in sorted(Path(root).iterdir(), key=lambda x: x.name.lower())[:60]:
                try:
                    if ch.is_dir():
                        n = sum(1 for _ in ch.iterdir()) if ch.is_dir() else 0
                        rows.append({"名称": ch.name + "/", "类型": "目录", "顶层条目": str(n), "大小": "—"})
                    else:
                        rows.append({"名称": ch.name, "类型": "文件", "顶层条目": "—",
                                     "大小": fmt_size(ch.stat().st_size)})
                except OSError:
                    pass
        except OSError:
            pass
        if rows:
            st.dataframe(rows, width="stretch", height=260)
        else:
            st.caption("（空目录）")
    else:
        st.caption("路径无效或待补")
    # WORKLOG
    st.markdown("#### WORKLOG（最近动态）")
    wl = Path(root) / "WORKLOG.md" if root else None
    if wl and wl.exists():
        lines = wl.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
        st.code("\n".join(lines[-15:]) or "（空）", language=None)
    else:
        st.caption("该项目还没有 WORKLOG.md（P1 试点时补建）")


# ---------------- 项目总览（三级下钻） ----------------
if page == "📊 项目总览":
    _ids = {x.get("id") for x in projects}
    for _k in ("sel_prog", "sel_pj"):
        if (st.session_state.get(_k) and st.session_state[_k] not in _ids
                and not st.session_state.get("_project_cache_" + st.session_state[_k])):
            st.session_state.pop(_k, None)
    if st.session_state.get("sel_pj"):
        render_project_page(st.session_state["sel_pj"], in_overview=True)
    elif st.session_state.get("sel_prog"):
        render_program_detail(st.session_state["sel_prog"])
    else:
        render_program_overview()
# ---------------- 项目详情 ----------------
elif page == "🔍 项目详情":
    st.title("项目详情")
    st.button("← 返回项目总览", key="back-from-detail", on_click=goto_overview)
    _current = st.session_state.get("current_pid")
    if (_current and not any(p.get("id") == _current for p in projects)
            and st.session_state.get("_project_cache_" + _current)):
        render_project_page(_current, in_overview=False)
    elif not projects:
        st.info("台账为空")
    else:
        ids = [x.get("id") for x in projects]
        cur = st.session_state.get("current_pid")
        idx = ids.index(cur) if cur in ids else 0
        pid = st.selectbox("选择项目", ids, index=idx, format_func=project_label)
        st.session_state["current_pid"] = pid
        render_project_page(pid, in_overview=False)
# ---------------- 应用台账 ----------------
elif page == "🧩 应用台账":
    # ================= 应用详情（点进来后的大页面）=================
    _cur = st.session_state.get("current_app")
    if _cur:
        _a = next((x for x in apps if x.get("id") == _cur), None)
        if _a is None:
            st.session_state["current_app"] = None
            st.rerun()
        st.title("应用详情")
        st.button("← 返回应用列表", on_click=back_to_apps)
        _cc = CAT_COLOR.get(_a.get("category"), "var(--pm-ink-3)")
        _purpose = _a.get("purpose") or "（无用途描述）"
        st.markdown(
            '<div class="pmcard" style="padding:20px 22px;margin-top:6px;">'
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
            f'<span style="font-size:23px;font-weight:800;color:var(--pm-ink);">{_a.get("name","")}</span>'
            f'{badge(_cc, CAT_CN.get(_a.get("category"), _a.get("category","")))}'
            '</div>'
            f'<div style="margin-top:12px;font-size:14px;color:var(--pm-ink-2);line-height:1.75;">{_purpose}</div>'
            '<div style="margin-top:14px;font-size:12.5px;color:var(--pm-ink-2);line-height:1.9;">'
            f'<div>地址：<code>{_a.get("path") or "—"}</code></div>'
            f'<div>可执行：<code>{_a.get("exe") or "—"}</code></div>'
            f'<div style="margin-top:6px;">类别 {CAT_CN.get(_a.get("category"), _a.get("category",""))}'
            f'　·　常用度 {USAGE_CN.get(_a.get("usage"), "未标注")}'
            f'　·　来源 {_a.get("source","—")}　·　版本 {_a.get("version") or "—"}</div>'
            '</div></div>', unsafe_allow_html=True)

        _tgt, _why = resolve_launch(_a)
        _blocked = bool(_tgt) and _is_blocked(Path(_tgt))
        b1, b2, _ = st.columns([1.2, 1.3, 3.5])
        if _tgt and not _blocked:
            if b1.button("▶ 启动应用", type="primary", width="stretch", key="app-launch"):
                try:
                    os.startfile(_tgt)  # noqa
                    st.toast("已启动：" + _tgt)
                except Exception as e:
                    st.error(str(e))
        else:
            b1.button("▶ 启动应用", disabled=True, width="stretch", key="app-launch-dis")
        _dir = None
        for _c in (_tgt, _a.get("exe") or "", _a.get("path") or ""):
            if not _c:
                continue
            if Path(_c).is_dir():
                _dir = _c
                break
            if Path(_c).is_file():
                _dir = str(Path(_c).parent)
                break
        if _dir and Path(_dir).is_dir():
            if b2.button("打开所在目录", width="stretch", key="app-opendir"):
                try:
                    os.startfile(str(_dir))  # noqa
                except Exception as e:
                    st.error(str(e))
        if _tgt and _blocked:
            st.caption(f"启动目标：{_tgt}　⚠️ 疑似安装/卸载程序，已阻止启动")
        elif _tgt:
            st.caption(f"启动目标（{_why}）：{_tgt}")
        else:
            st.caption("⚠️ " + _why)
        st.caption("首次启动可能被系统 SmartScreen / 杀软拦截，属正常。")

        with st.expander("编辑用途 / 常用度"):
            _form_key = f"app-{_a['id']}"
            _original = form_base(_form_key, _a)
            _np = st.text_area("这个应用是干什么用的？", value=_original.get("purpose", ""), key="appdetail-purpose")
            _us = ["daily", "often", "rare", "unused", "unknown"]
            _cu = _original.get("usage") if _original.get("usage") in _us else "unknown"
            _nu = st.selectbox("常用度", _us, index=_us.index(_cu), key="appdetail-usage")
            if st.button("保存", type="primary", key="appdetail-save"):
                _changed = copy.deepcopy(_original)
                _changed.update(purpose=_np, usage=_nu, desc_confirmed=True)
                save_form_record(_form_key, "apps", _a["id"], _original, _changed)
                st.toast("已保存")
                st.rerun()
        st.stop()   # 详情模式下不渲染下面的列表

    st.title("应用台账")
    st.caption("发现渠道：开始菜单快捷方式 + 卸载注册表 + winget + 便携目录扫描（只读）")
    kw = st.text_input("搜索", placeholder="搜应用名或用途，如：转写 / 磁盘 / git…", label_visibility="collapsed")
    c1, c2, c3 = st.columns([3.2, 1.6, 1.6])
    cats = ["全部", "ai", "quant", "dev", "browser", "media", "system", "office",
            "game", "security", "comm", "download", "finance", "input", "tool", "other"]
    cat = c1.radio("类别", cats, format_func=lambda x: "全部" if x == "全部" else CAT_CN.get(x, x),
                   horizontal=True, label_visibility="collapsed")
    usage_f = c2.selectbox("常用度", ["全部", "daily", "often", "rare", "unused"])
    sort_by = c3.selectbox("排序", ["名称", "类别", "常用度"])
    show_unconfirmed = st.toggle("包含待补描述应用", value=False)

    def app_visible(a):
        if not show_unconfirmed and not a.get("desc_confirmed"):
            return False
        if kw and kw.lower() not in (a.get("name", "") + " " + a.get("purpose", "")).lower():
            return False
        if cat != "全部" and a.get("category") != cat:
            return False
        if usage_f != "全部" and a.get("usage") != usage_f:
            return False
        return True

    view = [a for a in apps if app_visible(a)]
    if sort_by == "类别":
        view.sort(key=lambda a: (a.get("category", ""), a.get("name", "")))
    elif sort_by == "常用度":
        view.sort(key=lambda a: (a.get("usage", ""), a.get("name", "")))
    else:
        view.sort(key=lambda a: a.get("name", "").lower())
    PAGE_SIZE = 24
    sig = f"{kw}|{cat}|{usage_f}|{show_unconfirmed}|{sort_by}"
    if st.session_state.get("app_sig") != sig:
        st.session_state["app_sig"] = sig
        st.session_state["app_page"] = 0
    total_pages = max(1, (len(view) + PAGE_SIZE - 1) // PAGE_SIZE)
    # 页码唯一状态源 = session_state["app_page"]；必须在 selectbox 实例化之前夹取
    st.session_state["app_page"] = max(0, min(int(st.session_state.get("app_page", 0)), total_pages - 1))
    pg = st.session_state["app_page"]

    def _go_page(p):
        # 回调在控件实例化前运行，避免"改 widget 状态"报错，也不会被下拉框旧值覆盖
        st.session_state["app_page"] = max(0, min(int(p), total_pages - 1))

    nav1, nav2, nav3, nav4 = st.columns([1, 1.6, 1, 5])
    nav1.button("◀ 上一页", disabled=(pg == 0), width="stretch",
                on_click=_go_page, args=(pg - 1,), key="page_prev")
    nav2.selectbox("页码", list(range(total_pages)), key="app_page",
                   format_func=lambda i: f"第 {i + 1} / {total_pages} 页",
                   label_visibility="collapsed")
    nav3.button("下一页 ▶", disabled=(pg >= total_pages - 1), width="stretch",
                on_click=_go_page, args=(pg + 1,), key="page_next")
    nav4.markdown(f'<div style="font-size:12px;color:#888780;padding-top:10px;">共 {len(view)} 个应用</div>',
                  unsafe_allow_html=True)
    pg = st.session_state["app_page"]          # 回调可能已翻页，重新读取
    page_items = view[pg * PAGE_SIZE:(pg + 1) * PAGE_SIZE]
    cols = st.columns(3)
    for i, a in enumerate(page_items):
        color = CAT_COLOR.get(a.get("category"), "var(--pm-ink-3)")
        usage_dot = "#4E7A47" if a.get("usage") in ("daily", "often") else ("#B08A4A" if a.get("usage") == "rare" else "#C6C2BA")
        purpose = a.get("purpose") or '<i style="color:var(--pm-ink-3);">待补描述</i>'
        conf = "" if a.get("desc_confirmed") else '<span style="font-size:11px;color:var(--pm-ink-3);"> · AI 代拟待确认</span>'
        card = (
            f'<div class="pmcard" style="padding:13px 15px;height:100%;">'
            f'<div class="gloss"></div>'
            f'<div style="font-weight:600;font-size:13.5px;color:var(--pm-ink);">{a.get("name","")}'
            f'{badge(color, CAT_CN.get(a.get("category"), a.get("category","")))}</div>'
            f'<div style="color:var(--pm-ink-2);font-size:12px;line-height:1.55;margin:6px 0;min-height:32px;">{purpose}</div>'
            f'<div style="margin:6px 0;"><code>{a.get("path") or a.get("exe") or "?"}</code></div>'
            f'<div style="font-size:11.5px;color:var(--pm-ink-3);">'
            f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{usage_dot};margin-right:6px;vertical-align:middle;"></span>'
            f'{USAGE_CN.get(a.get("usage"),"—")} · {a.get("source","—")}{conf}</div></div>')
        with cols[i % 3]:
            st.markdown(card, unsafe_allow_html=True)
            st.button("详情 / 启动", key=f"app-open-{a['id']}", width="stretch",
                      on_click=open_app, args=(a["id"],))
            st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    st.caption(f"本页 {pg * PAGE_SIZE + 1}–{pg * PAGE_SIZE + len(page_items)} 条 · 共 {len(view)} 个应用")
    # 补描述编辑器：放侧栏，随选随改
    with st.sidebar:
        st.divider()
        unconf_n = sum(1 for a in apps if not a.get("desc_confirmed"))
        st.markdown("**补全 / 确认应用描述**")
        st.caption(f"待确认 {unconf_n} 个 · 保存即写入台账")
        order = ([a["name"] for a in apps if not a.get("desc_confirmed")]
                 + sorted(a["name"] for a in apps if a.get("desc_confirmed")))
        target = st.selectbox("选择应用", order)
        a = next(x for x in apps if x["name"] == target)
        _form_key = f"sidebar-app-{a['id']}"
        _original = form_base(_form_key, a)
        np_ = st.text_input("这个应用是干什么用的？", value=_original.get("purpose", ""))
        usages = ["daily", "often", "rare", "unused", "unknown"]
        cur_usage = _original.get("usage") if _original.get("usage") in usages else "unknown"
        nu = st.selectbox("常用度", usages, index=usages.index(cur_usage))
        if st.button("保存描述", type="primary", width="stretch"):
            _changed = copy.deepcopy(_original)
            _changed.update(purpose=np_, usage=nu, desc_confirmed=True)
            save_form_record(_form_key, "apps", a["id"], _original, _changed)
            st.toast(f"已保存：{target}")
            st.rerun()

# ---------------- 新增登记 ----------------
elif page == "➕ 新增登记":
    st.title("新增登记")
    t1, t2 = st.tabs(["登记项目", "登记应用"])
    with t1:
        _lvl = st.radio("登记层级", ["小项目（挂到超大项目下）", "超大项目（L1，可再挂小项目）"],
                        horizontal=True, label_visibility="collapsed")
        with st.form("f_proj", border=True):
            name = st.text_input("项目名称 *")
            root = st.text_input("根路径", placeholder=r"如 H:\github\xxx")
            desc = st.text_area("一句话说明 *", placeholder="这个项目是干什么的、现在做到哪一步")
            c1, c2, c3 = st.columns(3)
            cat = c1.selectbox("类别", ["quant", "tool", "doc", "data", "infra", "other"])
            stage = c2.text_input("阶段", value="调研")
            prog = c3.number_input("进度 %（有任务/目标时自动算）", 0, 100, value=0)
            if _lvl.startswith("小项目"):
                _plist = [("", "独立小项目（不归属任何超大项目）")] + [
                    (x["id"], x["name"]) for x in program_list(projects)]
                par_id = st.selectbox("归属超大项目", [k for k, _ in _plist],
                                      format_func=lambda k: dict(_plist)[k])
            else:
                par_id = None
                st.caption("将以超大项目（L1）登记；登记后可在它的详情页里新建小项目。")
            para = st.selectbox("PARA", ["project", "area", "resource"])
            st.caption("以下三项可选，用于一次性建立完整结构：")
            goals_txt = st.text_area("初始目标（每行一条）",
                                     placeholder="完成需求调研\n跑通首版原型")
            files_txt = st.text_area("相关文件路径（每行一条，可用 | 附用途）",
                                     placeholder=r"H:\proj\main.py | 主程序" + "\n" + r"H:\proj\data.csv | 数据")
            params_txt = st.text_area("关键参数（每行 名称=值）",
                                      placeholder="版本=v1.2\n平均耗时=3.4s")
            if st.form_submit_button("登记到台账", type="primary"):
                if not name or not desc:
                    st.error("名称与说明必填")
                else:
                    sid = slug(name)
                    if any(x["id"] == sid for x in reg["projects"]):
                        sid += "-2"
                    goals = [{"id": "g%d" % (i + 1), "text": ln.strip(), "done": False}
                             for i, ln in enumerate(goals_txt.splitlines()) if ln.strip()]
                    files = []
                    for ln in files_txt.splitlines():
                        if not ln.strip():
                            continue
                        a, _, b = ln.partition("|")
                        files.append({"path": a.strip(), "note": b.strip()})
                    params = []
                    for ln in params_txt.splitlines():
                        if "=" in ln:
                            k, v = ln.split("=", 1)
                            if k.strip():
                                params.append({"name": k.strip(), "value": v.strip(),
                                               "updated": datetime.now().strftime("%Y-%m-%d")})
                    prog_val = (round(sum(1 for g in goals if g["done"]) * 100 / len(goals))
                                if goals else (int(prog) if prog else None))
                    _is_prog = _lvl.startswith("超大")
                    reg["projects"].append({
                        "id": sid, "name": name, "description": desc,
                        "category": cat, "para": para, "status": "warm",
                        "stage": stage, "progress": prog_val,
                        "kind": "program" if _is_prog else "project",
                        "parent": None if _is_prog else (par_id or None),
                        "tasks": [],
                        "paths": {"root": root.strip(), "data": [], "wsl": []},
                        "platform": ["workbuddy"], "entry_points": [], "data_deps": [],
                        "docs": [], "last_activity": datetime.now().strftime("%Y-%m-%d"),
                        "health": "ok", "notes": "", "goals": goals,
                        "progress_log": [], "files": files, "params": params,
                        "ai_logs": [], "dev_logs": []})
                    save_reg(reg, "owner(工作台)")
                    _where = "独立小项目"
                    if not _is_prog and par_id:
                        _where = "→ " + dict(_plist).get(par_id, "独立小项目")
                    st.success(f"已登记 {name} → {sid}"
                               f"（{'超大项目 L1' if _is_prog else '小项目 L2'} {_where} · "
                               f"目标 {len(goals)} · 文件 {len(files)} · 参数 {len(params)}）")
    with t2:
        with st.form("f_app", border=True):
            name = st.text_input("应用名称 *")
            purpose = st.text_area("干什么用的 *")
            c1, c2 = st.columns(2)
            path = c1.text_input("位置", placeholder=r"如 E:\software\xxx")
            cat = c2.selectbox("类别", ["ai", "quant", "dev", "browser", "media", "system", "office", "other"])
            usage = st.selectbox("常用度", ["daily", "often", "rare", "unused"])
            if st.form_submit_button("登记到台账", type="primary"):
                if not name or not purpose:
                    st.error("名称与用途必填")
                else:
                    sid = slug(name)
                    if any(x["id"] == sid for x in reg["apps"]):
                        sid += "-2"
                    reg["apps"].append({
                        "id": sid, "name": name, "purpose": purpose, "category": cat,
                        "path": path.strip(), "exe": "", "version": "", "usage": usage,
                        "source": "manual", "desc_confirmed": True, "related_projects": []})
                    save_reg(reg, "owner(工作台)")
                    st.success(f"已登记 {name} → {sid}")

# ---------------- 待整理清单 ----------------
elif page == "🧹 待整理清单":
    st.title("待整理清单")
    st.caption("scanner 只读发现的身份不明目录。登记/忽略只改台账，不动任何文件。")
    items = json.loads(UNREG.read_text(encoding="utf-8")) if UNREG.exists() else []
    seen = set()
    uniq = []
    for x in items:
        if x["path"] in seen:
            continue
        seen.add(x["path"])
        uniq.append(x)
    items = uniq
    ignored = set(json.loads(IGNORED.read_text(encoding="utf-8"))) if IGNORED.exists() else set()
    registered_roots = {p.get("paths", {}).get("root", "").rstrip("\\").lower() for p in reg["projects"]}
    items = [x for x in items if x["path"] not in ignored
             and x["path"].rstrip("\\").lower() not in registered_roots]
    st.caption(f"待裁决 {len(items)} 项（按顶层体积排序，最多显示 25）")
    for x in sorted(items, key=lambda v: -v.get("top_size", 0))[:25]:
        size = x.get("top_size", 0)
        size_s = fmt_size(size)
        c1, c2, c3, c4 = st.columns([4, 1.4, 1, 1])
        c1.markdown(f"**`{x['path']}`**")
        c2.write(size_s + "（顶层）")
        if c3.button("登记", key="reg-" + x["path"]):
            sid = slug(x["name"])
            if any(y["id"] == sid for y in reg["projects"]):
                sid += "-2"
            reg["projects"].append({
                "id": sid, "name": x["name"],
                "description": "（从待整理清单登记，描述待补）",
                "category": "other", "para": "project", "status": "warm",
                "stage": "待定", "progress": None,
                "paths": {"root": x["path"], "data": [], "wsl": []},
                "platform": ["workbuddy"], "entry_points": [], "data_deps": [],
                "docs": [],
                "last_activity": datetime.fromtimestamp(x.get("mtime") or 0).strftime("%Y-%m-%d") if x.get("mtime") else "",
                "health": "ok", "goals": [], "progress_log": [],
                "notes": f"指纹: {', '.join(x.get('prints', [])) or '无'}"})
            save_reg(reg, "owner(工作台)")
            st.toast(f"已登记 {x['name']}")
            st.rerun()
        if c4.button("忽略", key="ign-" + x["path"]):
            ignored.add(x["path"])
            IGNORED.write_text(json.dumps(sorted(ignored), ensure_ascii=False), encoding="utf-8")
            st.rerun()

# ---------------- 文件地标 ----------------
elif page == "📍 文件地标":
    st.title("文件地标")
    st.caption("独立于项目的关键位置：数据集 / 缓存 / 输出 / 模型")
    for l in locs:
        st.container(border=True).markdown(
            f'<span style="font-size:13px;color:var(--pm-ink);"><code>{l.get("path")}</code></span>'
            f'{badge(ACCENT, l.get("kind",""))}<br>'
            f'<span style="font-size:12.5px;color:var(--pm-ink-2);">{l.get("purpose","")}</span>'
            + (f'<br><span style="font-size:11.5px;color:var(--pm-ink-3);">{l.get("size_note","")}</span>' if l.get("size_note") else ""),
            unsafe_allow_html=True)
