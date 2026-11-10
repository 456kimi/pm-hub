# -*- coding: utf-8 -*-
"""PM-Hub 静态导出：registry.json → index.html（零依赖，双击即看）"""
import base64
import html
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from theme import THEMES, DEFAULT_THEME, THEME_NAMES, theme_vars_css, CSS
from pm_progress import progress_info

HUB = Path(__file__).resolve().parent
REG_PATH = HUB / "registry.json"
PREFS_PATH = HUB / "ui_prefs.json"

ACCENT = "var(--pm-accent)"
ACCENT_DEEP = "var(--pm-ink)"
STATUS_COLOR = {"active": "var(--pm-st-active)", "warm": "var(--pm-st-warm)",
                "cold": "var(--pm-st-cold)", "archived": "var(--pm-st-archived)"}


def _bg_data_uri():
    try:
        p = HUB / "assets" / "miku_bg.jpg"
        return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return ""
STATUS_CN = {"active": "活跃", "warm": "温", "cold": "冷", "archived": "归档"}
TASK_CN = {"todo": "待办", "doing": "进行中", "done": "已完成", "blocked": "受阻"}
TASK_COLOR = {"todo": "#9AAFB2", "doing": "#E0A458", "done": "#4E7A47", "blocked": "#C2575F"}
USAGE_CN = {"daily": "常用", "often": "常用", "rare": "偶尔", "unused": "闲置", "unknown": "—"}
CAT_CN = {"quant": "量化", "tool": "工具", "doc": "文档", "data": "数据", "infra": "设施",
          "ai": "AI 工具", "dev": "开发", "browser": "浏览器", "media": "媒体",
          "system": "系统", "office": "办公", "game": "游戏", "other": "其他",
          "security": "安全", "comm": "通讯", "download": "下载网盘",
          "finance": "金融", "input": "输入法"}


def esc(s):
    return html.escape(str(s or ""))


def card(p):
    color = STATUS_COLOR.get(p.get("status"), "var(--pm-ink-3)")
    prog, source = progress_info(p)
    bar = (
        '<span class="pmbar-wrap"><span class="pmbar">'
        f'<span class="pmfill" style="width:{int(prog)}%"></span></span>'
        f'<span class="pmpct">{int(prog)}%</span></span>'
    ) if isinstance(prog, (int, float)) else '<span style="font-size:12px;color:var(--pm-ink-3);">进度未定</span>'
    root = p.get("paths", {}).get("root", "")
    plats = " · ".join(p.get("platform", [])) or "—"
    goals = p.get("goals") or []
    tasks = p.get("tasks") or []
    if tasks:
        tdone = sum(1 for t in tasks if t.get("status") == "done")
        gsum = f'任务 {tdone}/{len(tasks)}'
    elif goals:
        gsum = f'目标 {sum(1 for g in goals if g.get("done"))}/{len(goals)}'
    else:
        gsum = '<span style="color:#B4B0A8;">任务与目标均未设定</span>'
    nf = len(p.get("files") or [])
    npar = len(p.get("params") or [])
    nai = len(p.get("ai_logs") or [])
    ndev = len(p.get("dev_logs") or [])
    ndec = len([d for d in (p.get("decisions") or []) if d.get("status", "active") == "active"])
    nrel = len(p.get("relations") or [])
    _parts = []
    if ndec:
        _parts.append(f'现行结论 {ndec}')
    if nrel:
        _parts.append(f'关系 {nrel}')
    if nf:
        _parts.append(f'文件 {nf}')
    if npar:
        _parts.append(f'参数 {npar}')
    if nai:
        _parts.append(f'AI 日志 {nai}')
    if ndev:
        _parts.append(f'我的日志 {ndev}')
    extra = " · ".join(_parts)
    tlist = ""
    if tasks:
        items = "".join(
            f'<div style="font-size:12px;color:var(--pm-ink-2);padding:2px 0;line-height:1.5;">'
            f'<span style="display:inline-block;width:5px;height:5px;border-radius:50%;'
            f'background:{TASK_COLOR.get(t.get("status"), "#9AAFB2")};margin-right:7px;vertical-align:middle;"></span>'
            f'{esc(t.get("title"))}'
            f'<span style="color:var(--pm-ink-3);font-size:11px;"> · {TASK_CN.get(t.get("status"), "")}'
            + (f' · {esc(t.get("batch"))}' if t.get("batch") else "") + '</span>'
            + (f'<div style="color:var(--pm-ink-3);font-size:11.5px;padding-left:12px;">验收：{esc(t.get("acceptance"))}</div>'
               if t.get("acceptance") else "")
            + '</div>'
            for t in tasks)
        tlist = ('<div style="border-top:1px dashed var(--pm-line-soft);margin-top:10px;padding-top:8px;">'
                 '<div style="font-size:11px;color:var(--pm-ink-3);letter-spacing:.4px;margin-bottom:4px;">'
                 f'任务清单（{sum(1 for t in tasks if t.get("status") == "done")}/{len(tasks)} 完成，第三级）</div>'
                 f'{items}</div>')
    dot = (f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{color};'
           f'margin:0 5px 0 9px;vertical-align:middle;"></span>')
    return f'''<div class="pmcard" style="padding:14px 16px;min-width:260px;flex:1;">
<div class="gloss"></div>
<div style="font-weight:600;font-size:14px;color:var(--pm-ink);">{esc(p['name'])}{dot}<span style="color:{color};font-size:11px;">{STATUS_CN.get(p.get('status'), p.get('status'))}</span></div>
<div style="color:var(--pm-ink-2);font-size:12.5px;line-height:1.6;margin:7px 0;">{esc(p.get('description'))}</div>
<div style="font-size:12px;color:var(--pm-ink-2);margin-bottom:4px;">阶段 {esc(p.get('stage'))}　·　{gsum}</div>
<div style="margin:6px 0 2px;">{bar} <span style="font-size:11px;color:var(--pm-ink-3);">{esc(source)}</span></div>
{f'<div style="font-size:12px;color:var(--pm-ink-2);margin-top:4px;">{esc(extra)}</div>' if extra else ''}
{tlist}
<div style="font-size:11.5px;color:var(--pm-ink-3);margin-top:11px;padding-top:10px;border-top:1px solid #F0EEE9;">更新 {esc(p.get('last_activity')) or '—'} · {esc(plats)}<br><code>{esc(root) or '路径待补'}</code></div>
</div>'''


def program_block(prog, kids, tag="超大项目 L1"):
    """L1 分组块：超大项目头 + 其下 L2 卡片；也用于「独立小项目」分组。"""
    color = STATUS_COLOR.get(prog.get("status"), "var(--pm-ink-3)")
    tot = sum(len(k.get("tasks") or []) for k in kids)
    dn = sum(1 for k in kids for t in (k.get("tasks") or []) if t.get("status") == "done")
    if tot:
        pct = round(dn * 100 / tot)
    else:
        vals = [v for k in kids for v in [progress_info(k)[0]] if isinstance(v, (int, float))]
        pct = round(sum(vals) / len(vals)) if vals else None
    covered = sum(bool(k.get("tasks")) for k in kids)
    source = (f"按子项目任务 {dn}/{tot} 计算 · {covered}/{len(kids)} 个小项目有任务" if tot
              else f"按 {len(vals)}/{len(kids)} 个有进度的小项目取均值" if vals
              else "暂无可计算的子项目进度")
    bar = ('<span class="pmbar-wrap"><span class="pmbar">'
           f'<span class="pmfill" style="width:{int(pct)}%"></span></span>'
           f'<span class="pmpct">{int(pct)}%</span></span>') if isinstance(pct, (int, float)) else ''
    body = ("".join(card(k) for k in kids)
            if kids else '<div style="color:var(--pm-ink-3);font-size:12.5px;">（还没有挂载小项目）</div>')
    cnt_label = "小项目" if tag.startswith("超大") else "独立项目"
    return f'''<div style="margin:0 0 26px;">
<div class="pmcard" style="padding:16px 18px;margin-bottom:12px;border-left:4px solid {color};">
<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;">
<span style="font-weight:700;font-size:16px;color:var(--pm-accent);">{esc(prog.get('name'))}</span>
<span style="font-size:12px;color:var(--pm-ink-3);">{esc(tag)}
<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{color};margin:0 4px 0 8px;vertical-align:middle;"></span>{STATUS_CN.get(prog.get('status'), '')}</span>
</div>
<div style="color:var(--pm-ink-2);font-size:12.5px;line-height:1.65;margin:8px 0 6px;">{esc(prog.get('description'))}</div>
<div style="font-size:12px;color:var(--pm-ink-2);margin-bottom:5px;">{cnt_label} {len(kids)}　·　任务 {tot}（完成 {dn}）</div>
{bar} <span style="font-size:11px;color:var(--pm-ink-3);">{esc(source)}</span>
</div>
<div style="display:flex;flex-wrap:wrap;gap:12px;">{body}</div>
</div>'''


def app_row(a):
    conf = "" if a.get("desc_confirmed") else '<span style="color:var(--pm-ink-3);font-size:11px;"> · AI 代拟待确认</span>'
    return (f"<tr><td style='padding:7px 10px;font-weight:500;color:var(--pm-ink);'>{esc(a['name'])}</td>"
            f"<td style='padding:7px 10px;color:var(--pm-ink-2);font-size:12px;'>{esc(a.get('purpose')) or '<i>待补描述</i>'}{conf}</td>"
            f"<td style='padding:7px 10px;font-size:11.5px;color:var(--pm-ink-2);'>{esc(CAT_CN.get(a.get('category'), a.get('category')))}</td>"
            f"<td style='padding:7px 10px;font-size:11.5px;color:var(--pm-ink-2);'>{USAGE_CN.get(a.get('usage'), '—')}</td>"
            f"<td style='padding:7px 10px;'><code>{esc(a.get('path') or a.get('exe')) or '?'}</code></td></tr>")


def export(reg=None):
    if reg is None:
        reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
    allp = sorted(reg.get("projects", []), key=lambda x: x.get("last_activity") or "", reverse=True)
    progs = [p for p in allp if p.get("kind") == "program"]
    kidsmap = {pr["id"]: [p for p in allp if p.get("parent") == pr["id"]] for pr in progs}
    known = set(kidsmap)
    stands = [p for p in allp if p.get("kind") != "program" and p.get("parent") not in known]
    l2 = [p for p in allp if p.get("kind") != "program"]
    apps = reg.get("apps", [])
    locs = reg.get("locations", [])
    stats = {"active": 0, "warm": 0, "cold": 0, "archived": 0}
    for p in l2:
        stats[p.get("status")] = stats.get(p.get("status"), 0) + 1
    n_l3 = sum(len(p.get("tasks") or []) for p in allp)
    n_open = sum(1 for p in allp for t in (p.get("tasks") or []) if t.get("status") != "done")
    confirmed = sum(1 for a in apps if a.get("desc_confirmed"))
    bg = _bg_data_uri()
    sections = "\n".join(program_block(pr, kidsmap[pr["id"]]) for pr in progs)
    if stands:
        sections += "\n" + program_block(
            {"id": "_standalone", "name": "独立小项目", "status": "active",
             "description": "自成一体、不归属任何超大项目的独立项目（与超大项目平级）。"},
            stands, tag="独立小项目")
    cards = sections
    rows = "\n".join(app_row(a) for a in apps)
    loc_rows = "\n".join(
        f"<tr><td style='padding:6px 10px;font-weight:500;'>{esc(l['path'])}</td>"
        f"<td style='padding:6px 10px;color:var(--pm-ink-2);font-size:12px;'>{esc(l.get('purpose'))}</td></tr>"
        for l in locs)
    try:
        _theme = json.loads(PREFS_PATH.read_text(encoding="utf-8")).get("theme")
    except Exception:
        _theme = None
    if _theme not in THEMES:
        _theme = DEFAULT_THEME
    theme_css = theme_vars_css(_theme) + "\n" + CSS.replace("<style>", "").replace("</style>", "")
    if _theme == "miku" and bg:
        theme_css += ("\nbody{background-image:linear-gradient(100deg,rgba(244,251,250,.96) 0%,"
                      "rgba(244,251,250,.90) 30%,rgba(244,251,250,.60) 58%,"
                      "rgba(244,251,250,.22) 100%),url('" + bg + "') !important;"
                      "background-size:cover,cover !important;"
                      "background-position:center,right center !important;"
                      "background-attachment:fixed,fixed !important;}")
    _short = {"sora": "墨白", "runway": "Runway", "kling": "可灵",
              "midnight": "暗金", "kimi": "Kimi", "editorial": "编辑风", "miku": "初音"}
    _btns = "".join(
        '<button data-t="%s" onclick="pmTheme(\'%s\')">%s</button>' % (k, k, _short.get(k, k))
        for k in THEMES)
    _js = ("<div class=\"pmthemebar\">" + _btns + "</div>\n"
           "<script>var PMVARS=%s;"
           "function pmTheme(k){var v=PMVARS[k];if(!v)return;var r=document.documentElement;"
           "for(var a in v){r.style.setProperty(a,v[a]);}"
           "try{localStorage.setItem('pmhub_theme',k);}catch(e){}"
           "var bs=document.querySelectorAll('[data-t]');"
           "for(var i=0;i<bs.length;i++){bs[i].className=(bs[i].getAttribute('data-t')===k)?'on':'';}}"
           "(function(){try{var s=localStorage.getItem('pmhub_theme');if(s&&PMVARS[s]){pmTheme(s);}}catch(e){}})();"
           "</script>") % json.dumps({k: THEMES[k]["vars"] for k in THEMES}, ensure_ascii=False)

    doc = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>PM-Hub 项目中枢</title>
<style>
{theme_css}
/* ---- 静态页专属：把 .stApp 的那几层材质搬到 body 上 ---- */
body {{
  margin:0; background-color:var(--pm-bg); color:var(--pm-ink-2);
  font-family:var(--pm-body); -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(78% 30% at 50% 0%, var(--pm-halo-1) 0%, transparent 74%),
                   radial-gradient(60% 22% at 88% 4%, var(--pm-halo-2) 0%, transparent 76%),
                   linear-gradient(180deg, var(--pm-bg) 0%, var(--pm-bg-2) 100%);
  background-attachment:fixed; background-repeat:no-repeat;
}}
body::before {{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background-image:
    linear-gradient(to right, var(--pm-line-soft) 1px, transparent 1px),
    linear-gradient(to bottom, var(--pm-line-soft) 1px, transparent 1px);
  background-size:var(--pm-grid-size) var(--pm-grid-size);
  opacity:var(--pm-noise);
  -webkit-mask-image:radial-gradient(ellipse 92% 72% at 50% 0%, #000 18%, transparent 82%);
  mask-image:radial-gradient(ellipse 92% 72% at 50% 0%, #000 18%, transparent 82%);
}}
body::after {{
  content:""; position:fixed; inset:-12%; z-index:0; pointer-events:none;
  background:radial-gradient(44% 40% at 17% 26%, var(--pm-halo-1) 0%, transparent 64%),
             radial-gradient(40% 36% at 85% 30%, var(--pm-halo-2) 0%, transparent 62%),
             radial-gradient(52% 46% at 50% 100%, var(--pm-halo-3) 0%, transparent 68%);
  filter:blur(26px);
}}
h1 {{ font-family:var(--pm-display); font-weight:var(--pm-h1-weight); letter-spacing:var(--pm-h1-track); color:var(--pm-ink); }}
h2 {{ font-family:var(--pm-display); color:var(--pm-ink); letter-spacing:.02em; }}
table td, table th {{ color:var(--pm-ink-2); }}
.pmthemebar {{ position:fixed; top:16px; right:18px; z-index:99; display:flex; gap:5px;
  padding:5px; border-radius:99px; background:var(--pm-surface); border:1px solid var(--pm-line);
  backdrop-filter:blur(14px); box-shadow:var(--pm-shadow); }}
.pmthemebar button {{ border:0; background:transparent; color:var(--pm-ink-3); cursor:pointer;
  font-family:var(--pm-body); font-size:11px; padding:5px 11px; border-radius:99px;
  transition:background .18s, color .18s; }}
.pmthemebar button:hover {{ background:var(--pm-accent-soft); color:var(--pm-ink); }}
.pmthemebar button.on {{ background:var(--pm-accent); color:var(--pm-on-accent); font-weight:600; }}
</style></head>
<body>
{_js}
<div style="position:relative;z-index:1;max-width:1140px;margin:0 auto;padding:34px 22px 70px;">
<h1 style="font-size:20px;font-weight:650;margin:0 0 4px;letter-spacing:.2px;">PM-Hub 项目中枢</h1>
<div style="color:var(--pm-ink-3);font-size:11.5px;margin-bottom:16px;">静态快照 · 生成于 {esc(reg.get('updated_at'))} · 操作者 {esc(reg.get('operator'))} · 实时看板: <code>streamlit run {esc(HUB / 'dashboard.py')}</code></div>
<div style="font-size:12.5px;color:var(--pm-ink-2);margin-bottom:6px;">
超大项目 {len(progs)}（其下小项目 {len(l2) - len(stands)}） &nbsp;·&nbsp; 独立小项目 {len(stands)} &nbsp;·&nbsp; 任务 L3 {n_l3}（未完成 {n_open}）</div>
<div style="font-size:12.5px;color:var(--pm-ink-2);margin-bottom:18px;">
<span style="color:{STATUS_COLOR['active']};">●</span> 活跃小项目 {stats['active']} · 活跃体系 {sum(1 for p in progs if p.get('status') == 'active')} &nbsp;&nbsp;小项目：温 {stats['warm']} · 冷 {stats['cold']} · 归档 {stats['archived']} &nbsp;&nbsp;<span style="color:var(--pm-line);">|</span>&nbsp;&nbsp;应用 {len(apps)}（已确认 {confirmed}）</div>
<h2 style="font-size:15px;font-weight:600;color:var(--pm-accent);">项目（三级体系：超大项目 → 小项目 → 任务）</h2>
{cards}
<h2 style="font-size:15px;font-weight:600;color:var(--pm-accent);margin-top:30px;">应用台账（{len(apps)}）</h2>
<table style="border-collapse:collapse;background:var(--pm-surface);border:1px solid var(--pm-line);border-radius:8px;width:100%;font-size:12px;overflow:hidden;">
<tr style="color:var(--pm-ink-2);text-align:left;"><th style="padding:8px 10px;font-weight:500;">应用</th><th style="padding:8px 10px;font-weight:500;">用途</th><th style="padding:8px 10px;font-weight:500;">类别</th><th style="padding:8px 10px;font-weight:500;">常用度</th><th style="padding:8px 10px;font-weight:500;">位置</th></tr>{rows}</table>
<h2 style="font-size:15px;font-weight:600;color:var(--pm-accent);margin-top:30px;">文件地标（{len(locs)}）</h2>
<table style="border-collapse:collapse;background:var(--pm-surface);border:1px solid var(--pm-line);border-radius:8px;width:100%;font-size:12px;overflow:hidden;">
<tr style="color:var(--pm-ink-2);text-align:left;"><th style="padding:8px 10px;font-weight:500;">位置</th><th style="padding:8px 10px;font-weight:500;">用途</th></tr>{loc_rows}</table>
<div style="color:var(--pm-ink-3);font-size:11px;margin-top:26px;">规则见 AGENTS.md · 物理归档/删除必须逐条确认 · registry.json 变更自动重新导出本页</div>
</div></body></html>"""
    target = HUB / "index.html"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=HUB,
                                         prefix="index.", suffix=".tmp", delete=False) as f:
            temp_path = Path(f.name)
            f.write(doc)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return target


if __name__ == "__main__":
    from pm_registry import export_registry
    result = export_registry(export)
    if result.export_error:
        raise SystemExit("静态页更新失败: " + result.export_error)
    print("导出:", HUB / "index.html")
