# -*- coding: utf-8 -*-
"""PM-Hub 主题与样式（dashboard.py 与 export_static.py 共用）。

新增一套主题：往 THEMES 里加一条，并在 THEME_ORDER 里登记。
所有组件样式只认 CSS 变量（--pm-*），不再各自写死颜色。
"""

_FONT_SANS = ('"Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI",'
              '"Microsoft YaHei","PingFang SC",system-ui,sans-serif')
_FONT_SERIF = ('"Georgia","Songti SC","SimSun","Noto Serif SC",'
               '"Microsoft YaHei",serif')
_FONT_MONO = '"Cascadia Code","Consolas","SF Mono",ui-monospace,monospace'

# 每套主题的 vars 键必须齐全；缺键由 THEME_BASE_VARS 兜底
THEME_BASE_VARS = {
    "--pm-radius": "16px",
    "--pm-radius-sm": "10px",
    "--pm-display": _FONT_SANS,
    "--pm-body": _FONT_SANS,
    "--pm-mono": _FONT_MONO,
    "--pm-h1-weight": "720",
    "--pm-h1-track": "-0.022em",
    "--pm-noise": "0.035",
    "--pm-grid": "0.55",
    "--pm-grid-size": "32px",
    "--pm-card-blur": "0px",
    "--pm-sidebar": "rgba(255,255,255,.72)",
    "--pm-st-active": "#2BB3A9",
    "--pm-st-warm": "#E0A458",
    "--pm-st-cold": "#8FA3A6",
    "--pm-st-archived": "#B9C6C7",
}

THEMES = {
    # ---------------- 1. 墨白 · Sora 极简 ----------------
    "sora": {
        "label": "墨白 · Sora",
        "note": "亮色 / 极简 / 大留白",
        "vars": {
            "--pm-bg": "#FAFAF8",
            "--pm-bg-2": "#F1F1EC",
            "--pm-surface": "#FFFFFF",
            "--pm-surface-2": "#F5F5F1",
            "--pm-surface-3": "#EDEDE7",
            "--pm-ink": "#0C0C0E",
            "--pm-ink-2": "#4C4C51",
            "--pm-ink-3": "#8B8B90",
            "--pm-ink-4": "#B8B8BC",
            "--pm-line": "#E2E2DA",
            "--pm-line-soft": "#EDEDE6",
            "--pm-accent": "#0C0C0E",
            "--pm-accent-2": "#3D3D44",
            "--pm-accent-soft": "rgba(12,12,14,.055)",
            "--pm-on-accent": "#FFFFFF",
            "--pm-halo-1": "rgba(122,132,255,.15)",
            "--pm-halo-2": "rgba(255,186,120,.14)",
            "--pm-halo-3": "rgba(120,200,190,.12)",
            "--pm-shadow": "0 1px 2px rgba(12,12,14,.06), 0 10px 28px rgba(12,12,14,.055)",
            "--pm-shadow-hover": "0 2px 6px rgba(12,12,14,.09), 0 26px 54px rgba(12,12,14,.15)",
            "--pm-sidebar": "rgba(255,255,255,.82)",
            "--pm-noise": "0.028",
            "--pm-grid": "0.7",
            "--pm-radius": "18px",
            "--pm-st-active": "#0C0C0E",
            "--pm-st-warm": "#8A6A34",
            "--pm-st-cold": "#9A9A9E",
            "--pm-st-archived": "#C4C4C8",
        },
    },
    # ---------------- 2. Runway · 暗夜影像 ----------------
    "runway": {
        "label": "Runway · 暗夜影像",
        "note": "深色 / 酸性绿 / 电影感",
        "vars": {
            "--pm-bg": "#07070A",
            "--pm-bg-2": "#0B0B10",
            "--pm-surface": "rgba(255,255,255,.045)",
            "--pm-surface-2": "rgba(255,255,255,.075)",
            "--pm-surface-3": "rgba(255,255,255,.11)",
            "--pm-ink": "#F4F4F1",
            "--pm-ink-2": "#AFAFAB",
            "--pm-ink-3": "#8E8E89",
            "--pm-ink-4": "#5E5E59",
            "--pm-line": "rgba(255,255,255,.11)",
            "--pm-line-soft": "rgba(255,255,255,.065)",
            "--pm-accent": "#D8FF3E",
            "--pm-accent-2": "#EEFF9C",
            "--pm-accent-soft": "rgba(216,255,62,.11)",
            "--pm-on-accent": "#08080A",
            "--pm-halo-1": "rgba(216,255,62,.22)",
            "--pm-halo-2": "rgba(90,220,255,.16)",
            "--pm-halo-3": "rgba(255,120,60,.12)",
            "--pm-shadow": "0 1px 0 rgba(255,255,255,.05) inset, 0 12px 32px rgba(0,0,0,.45)",
            "--pm-shadow-hover": "0 1px 0 rgba(255,255,255,.10) inset, 0 26px 60px rgba(0,0,0,.6), 0 0 40px rgba(216,255,62,.10)",
            "--pm-sidebar": "rgba(10,10,14,.72)",
            "--pm-noise": "0.055",
            "--pm-grid": "0.5",
            "--pm-card-blur": "14px",
            "--pm-radius": "16px",
            "--pm-st-active": "#D8FF3E",
            "--pm-st-warm": "#FF9A5C",
            "--pm-st-cold": "#8E8E89",
            "--pm-st-archived": "#5E5E59",
        },
    },
    # ---------------- 3. 可灵 · 幻彩极光 ----------------
    "kling": {
        "label": "可灵 · 幻彩极光",
        "note": "深色 / 紫粉极光 / 玻璃",
        "vars": {
            "--pm-bg": "#08060F",
            "--pm-bg-2": "#0C0918",
            "--pm-surface": "rgba(255,255,255,.052)",
            "--pm-surface-2": "rgba(255,255,255,.085)",
            "--pm-surface-3": "rgba(255,255,255,.12)",
            "--pm-ink": "#F2EFFF",
            "--pm-ink-2": "#B3ACD4",
            "--pm-ink-3": "#9A92B5",
            "--pm-ink-4": "#665F82",
            "--pm-line": "rgba(180,160,255,.16)",
            "--pm-line-soft": "rgba(180,160,255,.09)",
            "--pm-accent": "#8B6BFF",
            "--pm-accent-2": "#FF6FA8",
            "--pm-accent-soft": "rgba(139,107,255,.14)",
            "--pm-on-accent": "#FFFFFF",
            "--pm-halo-1": "rgba(124,92,255,.40)",
            "--pm-halo-2": "rgba(255,92,157,.30)",
            "--pm-halo-3": "rgba(77,201,255,.24)",
            "--pm-shadow": "0 1px 0 rgba(255,255,255,.06) inset, 0 14px 36px rgba(0,0,0,.42)",
            "--pm-shadow-hover": "0 1px 0 rgba(255,255,255,.12) inset, 0 30px 64px rgba(0,0,0,.55), 0 0 44px rgba(139,107,255,.22)",
            "--pm-sidebar": "rgba(14,11,26,.70)",
            "--pm-noise": "0.045",
            "--pm-grid": "0.35",
            "--pm-card-blur": "18px",
            "--pm-radius": "20px",
            "--pm-st-active": "#B79BFF",
            "--pm-st-warm": "#FF8FB8",
            "--pm-st-cold": "#9A92B5",
            "--pm-st-archived": "#665F82",
        },
    },
    # ---------------- 4. 暗金 · Midjourney ----------------
    "midnight": {
        "label": "暗金 · Midjourney",
        "note": "深色 / 暖金 / 衬线标题",
        "vars": {
            "--pm-bg": "#0B0906",
            "--pm-bg-2": "#120E09",
            "--pm-surface": "rgba(243,237,227,.042)",
            "--pm-surface-2": "rgba(243,237,227,.075)",
            "--pm-surface-3": "rgba(243,237,227,.11)",
            "--pm-ink": "#F3EDE3",
            "--pm-ink-2": "#B3A894",
            "--pm-ink-3": "#9C9180",
            "--pm-ink-4": "#665C4C",
            "--pm-line": "rgba(216,178,106,.20)",
            "--pm-line-soft": "rgba(216,178,106,.11)",
            "--pm-accent": "#D9B26A",
            "--pm-accent-2": "#F0D29A",
            "--pm-accent-soft": "rgba(217,178,106,.12)",
            "--pm-on-accent": "#120E09",
            "--pm-halo-1": "rgba(217,178,106,.24)",
            "--pm-halo-2": "rgba(150,90,40,.18)",
            "--pm-halo-3": "rgba(60,90,120,.13)",
            "--pm-shadow": "0 1px 0 rgba(255,255,255,.05) inset, 0 14px 34px rgba(0,0,0,.5)",
            "--pm-shadow-hover": "0 1px 0 rgba(255,255,255,.10) inset, 0 28px 62px rgba(0,0,0,.62), 0 0 38px rgba(217,178,106,.14)",
            "--pm-sidebar": "rgba(16,12,8,.74)",
            "--pm-noise": "0.06",
            "--pm-grid": "0.28",
            "--pm-card-blur": "10px",
            "--pm-radius": "14px",
            "--pm-display": _FONT_SERIF,
            "--pm-body": _FONT_SANS,
            "--pm-h1-weight": "600",
            "--pm-h1-track": "-0.012em",
            "--pm-st-active": "#D9B26A",
            "--pm-st-warm": "#C08A4A",
            "--pm-st-cold": "#9C9180",
            "--pm-st-archived": "#665C4C",
        },
    },
    # ---------------- 5. 高级 · Kimi（原版精修） ----------------
    "kimi": {
        "label": "高级 · Kimi",
        "note": "亮色 / 黑白 / 一点紫",
        "vars": {
            "--pm-bg": "#FAFAFB",
            "--pm-bg-2": "#F3F3F7",
            "--pm-surface": "rgba(255,255,255,.92)",
            "--pm-surface-2": "#F4F4F7",
            "--pm-surface-3": "#ECECF1",
            "--pm-ink": "#14141A",
            "--pm-ink-2": "#4A4A55",
            "--pm-ink-3": "#8A8A95",
            "--pm-ink-4": "#B8B8C2",
            "--pm-line": "#E6E6EA",
            "--pm-line-soft": "#EFEFF3",
            "--pm-accent": "#14141A",
            "--pm-accent-2": "#5B5BD6",
            "--pm-accent-soft": "rgba(20,20,26,.055)",
            "--pm-on-accent": "#FFFFFF",
            "--pm-halo-1": "rgba(122,126,255,.18)",
            "--pm-halo-2": "rgba(40,40,60,.06)",
            "--pm-halo-3": "rgba(150,200,255,.14)",
            "--pm-shadow": "0 6px 24px rgba(20,20,26,.06)",
            "--pm-shadow-hover": "0 20px 46px rgba(20,20,26,.14)",
            "--pm-sidebar": "rgba(255,255,255,.86)",
            "--pm-noise": "0.02",
            "--pm-grid": "0.25",
            "--pm-card-blur": "6px",
            "--pm-radius": "16px",
            "--pm-st-active": "#14141A",
            "--pm-st-warm": "#B5852E",
            "--pm-st-cold": "#8A8A95",
            "--pm-st-archived": "#B8B8C2",
        },
    },
    # ---------------- 6. 简约 · 编辑风 ----------------
    "editorial": {
        "label": "简约 · 编辑风",
        "note": "亮色 / 暖纸 / 克制动效",
        "vars": {
            "--pm-bg": "#F6F5F2",
            "--pm-bg-2": "#EFEDE7",
            "--pm-surface": "#FFFFFF",
            "--pm-surface-2": "#F4F3EF",
            "--pm-surface-3": "#ECE9E3",
            "--pm-ink": "#22201D",
            "--pm-ink-2": "#4A473F",
            "--pm-ink-3": "#9B978F",
            "--pm-ink-4": "#B4B0A8",
            "--pm-line": "#E7E4DE",
            "--pm-line-soft": "#F0EEE9",
            "--pm-accent": "#33536F",
            "--pm-accent-2": "#5C7A99",
            "--pm-accent-soft": "rgba(51,83,111,.07)",
            "--pm-on-accent": "#FFFFFF",
            "--pm-halo-1": "rgba(51,83,111,.07)",
            "--pm-halo-2": "rgba(180,160,120,.08)",
            "--pm-halo-3": "rgba(120,140,160,.05)",
            "--pm-shadow": "0 1px 3px rgba(0,0,0,.04)",
            "--pm-shadow-hover": "0 12px 30px rgba(45,71,94,.12)",
            "--pm-sidebar": "#FFFFFF",
            "--pm-noise": "0.03",
            "--pm-grid": "0",
            "--pm-radius": "10px",
            "--pm-h1-weight": "640",
        },
    },
    # ---------------- 7. 初音未来（彩蛋，保留原样） ----------------
    "miku": {
        "label": "初音未来",
        "note": "青绿 / 背景图 / 彩蛋",
        "vars": {
            "--pm-bg": "#EAF7F6",
            "--pm-bg-2": "#F4FBFA",
            "--pm-surface": "rgba(255,255,255,.82)",
            "--pm-surface-2": "rgba(234,247,246,.92)",
            "--pm-surface-3": "#E1F0EE",
            "--pm-ink": "#123C39",
            "--pm-ink-2": "#2E5A57",
            "--pm-ink-3": "#5C7A7E",
            "--pm-ink-4": "#9CC7C2",
            "--pm-line": "rgba(43,179,169,.26)",
            "--pm-line-soft": "rgba(43,179,169,.14)",
            "--pm-accent": "#2BB3A9",
            "--pm-accent-2": "#6FDAD1",
            "--pm-accent-soft": "rgba(43,179,169,.12)",
            "--pm-on-accent": "#FFFFFF",
            "--pm-halo-1": "rgba(43,179,169,.14)",
            "--pm-halo-2": "rgba(111,218,209,.12)",
            "--pm-halo-3": "rgba(120,220,255,.10)",
            "--pm-shadow": "0 2px 12px rgba(15,122,115,.06)",
            "--pm-shadow-hover": "0 18px 38px rgba(15,122,115,.20)",
            "--pm-sidebar": "rgba(255,255,255,.80)",
            "--pm-noise": "0.02",
            "--pm-grid": "0",
            "--pm-card-blur": "10px",
            "--pm-radius": "14px",
        },
    },
}

THEME_ORDER = ["sora", "runway", "kling", "midnight", "kimi", "editorial", "miku"]
THEME_NAMES = {k: THEMES[k]["label"] for k in THEME_ORDER}
DEFAULT_THEME = "sora"


def theme_vars_css(key):
    """把选中主题的变量渲染成 :root{...}。缺键用 base 补齐。"""
    t = THEMES.get(key) or THEMES[DEFAULT_THEME]
    merged = dict(THEME_BASE_VARS)
    merged.update(t["vars"])
    body = "\n".join("  %s: %s;" % (k, v) for k, v in merged.items())
    return ":root{\n%s\n}" % body


CSS = """
<style>
/* =====================================================================
   PM-Hub 视觉层 v3
   1) 变量：全部来自选中主题的 :root
   2) 材质：底色 → 极光光团 → 网格 → 噪点（自下而上四层）
   3) 动效：位移+模糊消散的入场、滚动渐显、悬停流光
   ===================================================================== */

/* ---------- 0. 基础 ---------- */
/* 接管 Streamlit 自己的全局变量，控件文字/底色随主题走 */
:root, .stApp, [data-testid="stAppViewContainer"] {
  --primary-color: var(--pm-accent);
  --background-color: var(--pm-bg);
  --secondary-background-color: var(--pm-surface);
  --text-color: var(--pm-ink);
  --font: var(--pm-display);
}
html, body, .stApp, [data-testid="stAppViewContainer"] {
  background-color: var(--pm-bg) !important;
}
.stApp {
  color: var(--pm-ink-2);
  font-family: var(--pm-body);
  background-image:
    radial-gradient(78% 30% at 50% 0%, var(--pm-halo-1) 0%, transparent 74%),
    radial-gradient(60% 22% at 88% 4%, var(--pm-halo-2) 0%, transparent 76%),
    linear-gradient(180deg, var(--pm-bg) 0%, var(--pm-bg) 46%, var(--pm-bg-2) 100%) !important;
  background-size: auto, auto, auto !important;
  background-position: center center, center !important;
  background-repeat: no-repeat, no-repeat !important;
  background-attachment: fixed, fixed !important;
}
/* 光团：故意压在内容区而不是页边，让卡片透出色来 */
.stApp::after {
  content: ""; position: fixed; inset: -12%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(44% 40% at 17% 26%, var(--pm-halo-1) 0%, transparent 64%),
    radial-gradient(40% 36% at 85% 30%, var(--pm-halo-2) 0%, transparent 62%),
    radial-gradient(52% 46% at 50% 100%, var(--pm-halo-3) 0%, transparent 68%);
  filter: blur(26px);
  animation: pmDriftA 38s ease-in-out infinite alternate;
}
@keyframes pmDriftA {
  0%   { transform: translate3d(0,0,0) scale(1); }
  50%  { transform: translate3d(-2.4%, 1.6%, 0) scale(1.07); }
  100% { transform: translate3d(2%, -2%, 0) scale(1.03); }
}
/* 网格 + 噪点：往上压一层，制造"底片"质感 */
.stApp::before {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    linear-gradient(to right, var(--pm-line-soft) 1px, transparent 1px),
    linear-gradient(to bottom, var(--pm-line-soft) 1px, transparent 1px),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
  background-size:
    var(--pm-grid-size) var(--pm-grid-size),
    var(--pm-grid-size) var(--pm-grid-size),
    180px 180px;
  opacity: var(--pm-noise);
  background-blend-mode: normal, normal, overlay;
  -webkit-mask-image: radial-gradient(ellipse 92% 72% at 50% 0%, #000 18%, transparent 82%);
  mask-image: radial-gradient(ellipse 92% 72% at 50% 0%, #000 18%, transparent 82%);
}
/* 光团 B：反向漂移的第二层，避免整页色斑"整块移动" */
#pmAurora {
  position: fixed; inset: -20%; z-index: 0; pointer-events: none;
  background: radial-gradient(30% 26% at 70% 62%, var(--pm-halo-2) 0%, transparent 70%);
  filter: blur(30px); opacity: .75;
  animation: pmDriftB 52s ease-in-out infinite alternate;
}
@keyframes pmDriftB {
  from { transform: translate3d(1.5%, -1%, 0) scale(1.02); }
  to   { transform: translate3d(-3%, 2.5%, 0) scale(1.10); }
}
/* 顶部滚动进度：纯 CSS，不依赖 JS */
#pmTopbar {
  position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 99999;
  transform-origin: 0 50%; pointer-events: none;
  background: linear-gradient(90deg, var(--pm-accent), var(--pm-accent-2));
  opacity: .85;
}
@supports (animation-timeline: scroll()) {
  #pmTopbar { transform: scaleX(0); animation: pmScrollX linear both; animation-timeline: scroll(root block); }
  @keyframes pmScrollX { to { transform: scaleX(1); } }
}

/* ---------- 1. 布局 ---------- */
.block-container {
  padding-top: 1.9rem !important; padding-bottom: 4rem !important;
  max-width: 1240px; position: relative; z-index: 1;
}
[data-testid="stMain"] { background: transparent !important; }
[data-testid="stHorizontalBlock"] { gap: 1.4rem !important; }
[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stMainMenuButton"] { visibility: hidden; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] { display: none !important; }

/* ---------- 2. 排版 ---------- */
h1, h2, h3, h4, h5 { font-family: var(--pm-display) !important; }
h1 {
  font-size: clamp(1.62rem, 2.1vw, 2.05rem) !important;
  font-weight: var(--pm-h1-weight) !important;
  letter-spacing: var(--pm-h1-track) !important;
  line-height: 1.08 !important;
  color: var(--pm-ink) !important;
  margin: 0 0 .35rem !important;
}
h2 { font-size: 1.16rem !important; font-weight: 650 !important; color: var(--pm-ink) !important; letter-spacing: -.01em !important; }
h3 { font-size: 1rem !important;   font-weight: 650 !important; color: var(--pm-ink) !important; }
h4 {
  position: relative !important; display: flex; align-items: center; gap: 11px;
  font-size: .82rem !important; font-weight: 640 !important;
  color: var(--pm-ink) !important; letter-spacing: .06em !important;
  text-transform: none; margin: 1.9rem 0 .68rem !important; padding-left: 12px !important;
}
h4::after {
  content: ""; flex: 1 1 auto; height: 1px;
  background: linear-gradient(90deg, var(--pm-line), transparent 74%);
}
h4::before {
  content: ""; position: absolute; left: 0; top: .18em; bottom: .18em; width: 2px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--pm-accent), var(--pm-accent-2));
}
p { color: var(--pm-ink-2); }
hr { border: 0 !important; border-top: 1px solid var(--pm-line-soft) !important; margin: 1.1rem 0 !important; }
[data-testid="stCaptionContainer"] p, .stCaption {
  color: var(--pm-ink-3) !important; font-size: 11.5px !important; line-height: 1.7 !important;
}
::selection { background: var(--pm-accent-soft); color: var(--pm-ink); }
b, strong { color: var(--pm-ink); font-weight: 650; }

/* ---------- 3. Hero ---------- */
.pmhero { position: relative; margin: 2px 0 36px; }
.pmhero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 10.5px; font-weight: 600; letter-spacing: .19em; text-transform: uppercase;
  color: var(--pm-ink-3); margin-bottom: 12px;
}
.pmhero-eyebrow::before {
  content: ""; width: 18px; height: 1px; background: var(--pm-accent);
  display: inline-block; opacity: .8;
}
.pmhero-title {
  font-size: clamp(1.86rem, 2.5vw, 2.32rem); font-weight: var(--pm-h1-weight);
  letter-spacing: var(--pm-h1-track); line-height: 1.06; color: var(--pm-ink);
  margin: 0 0 11px; font-family: var(--pm-display);
  animation: pmRiseIn .62s cubic-bezier(.22,1,.36,1) both;
}
.pmhero-sub {
  font-size: 13.5px; line-height: 1.65; color: var(--pm-ink-3);
  max-width: 720px; margin: 0 0 20px; font-weight: 400;
  animation: pmRiseIn .62s cubic-bezier(.22,1,.36,1) .06s both;
}
.pmhero-stats {
  display: flex; flex-wrap: wrap; align-items: flex-end; gap: 0;
  padding-top: 16px; border-top: 1px solid var(--pm-line-soft);
  animation: pmRiseIn .62s cubic-bezier(.22,1,.36,1) .12s both;
}
.pmstat { padding: 0 30px; border-left: 1px solid var(--pm-line); line-height: 1.15; }
.pmstat:first-child { padding-left: 0; border-left: 0; }
.pmstat b {
  display: block; font-size: 25px; font-weight: 620; color: var(--pm-ink);
  letter-spacing: -.035em; font-variant-numeric: tabular-nums; font-feature-settings: "tnum";
}
.pmstat span {
  display: block; font-size: 10.5px; color: var(--pm-ink-3);
  letter-spacing: .09em; margin-top: 5px; text-transform: uppercase;
}
.pmstat.is-accent b { color: var(--pm-accent); }
@keyframes pmRiseIn {
  from { opacity: 0; transform: translateY(14px); filter: blur(7px); }
  to   { opacity: 1; transform: none; filter: none; }
}

/* ---------- 4. 侧栏 ---------- */
section[data-testid="stSidebar"] {
  background: var(--pm-sidebar) !important;
  backdrop-filter: blur(22px) saturate(150%) !important;
  -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
  border-right: 1px solid var(--pm-line) !important;
  transform: none !important; visibility: visible !important; margin-left: 0 !important;
  width: 268px !important; min-width: 268px !important; max-width: 268px !important;
  flex: 0 0 268px !important;
  padding-top: 1.15rem;
  position: relative; z-index: 2;
}
section[data-testid="stSidebar"] > div { background: transparent !important; }
section[data-testid="stSidebar"] hr { visibility: hidden; margin: 2px 0; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label {
  position: relative; background: transparent; border: 0; border-radius: 9px;
  padding: 7px 11px; cursor: pointer; width: 100%;
  transition: background .18s ease, padding-left .26s cubic-bezier(.22,1,.36,1);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
  content: ""; position: absolute; left: 0; top: 50%; width: 2px; height: 0;
  border-radius: 2px; background: var(--pm-accent);
  transform: translateY(-50%); transition: height .26s cubic-bezier(.22,1,.36,1);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label div { font-size: 13px !important; color: var(--pm-ink-2); font-weight: 450; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: var(--pm-accent-soft); }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover::before { height: 14px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: var(--pm-surface-3);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before { height: 18px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div {
  color: var(--pm-ink) !important; font-weight: 620;
}
section[data-testid="stSidebar"] div[role="radiogroup"] input { opacity: 0; position: absolute; }
/* 隐去单选圆圈，只留文字 */
section[data-testid="stSidebar"] div[role="radiogroup"] label div:has(+ [data-testid="stMarkdownContainer"]),
[data-testid="stMain"] div[role="radiogroup"] label div:has(+ [data-testid="stMarkdownContainer"]) { display: none !important; }

/* 侧栏字标 */
.pmlogo {
  flex: 0 0 38px; width: 38px; height: 38px; border-radius: 12px;
  background: linear-gradient(150deg, var(--pm-accent-2), var(--pm-accent));
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 20px var(--pm-accent-soft);
  animation: pmBreathe 6s ease-in-out infinite;
}
@keyframes pmBreathe {
  0%,100% { box-shadow: 0 5px 16px var(--pm-accent-soft); }
  50%     { box-shadow: 0 8px 28px var(--pm-accent-soft); }
}
.pmbrand {
  font-weight: 750; font-size: 19px; letter-spacing: -.03em; line-height: 1;
  color: var(--pm-ink); font-family: var(--pm-display);
}
.pmrule { height: 1px; margin: 15px 0 6px; border-radius: 2px;
  background: linear-gradient(90deg, var(--pm-line), transparent); }

/* ---------- 5. 主区筛选胶囊 ---------- */
[data-testid="stMain"] div[role="radiogroup"] { gap: 6px; flex-wrap: wrap; }
[data-testid="stMain"] div[role="radiogroup"] label {
  background: var(--pm-surface); border: 1px solid var(--pm-line); border-radius: 99px;
  padding: 4px 13px; cursor: pointer;
  transition: transform .34s cubic-bezier(.34,1.56,.64,1), box-shadow .26s, background .2s, border-color .2s;
}
[data-testid="stMain"] div[role="radiogroup"] label div { font-size: 12px !important; color: var(--pm-ink-2); }
[data-testid="stMain"] div[role="radiogroup"] label:hover {
  border-color: var(--pm-accent); transform: translateY(-2px);
  box-shadow: 0 6px 16px var(--pm-accent-soft);
}
[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) {
  background: var(--pm-accent); border-color: var(--pm-accent);
}
[data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) div {
  color: var(--pm-on-accent) !important; font-weight: 620;
}
[data-testid="stMain"] div[role="radiogroup"] input { opacity: 0; position: absolute; }

/* ---------- 6. 卡片 ---------- */
.pmcard {
  position: relative; overflow: hidden; height: 100%;
  background: var(--pm-surface) !important;
  border: 1px solid var(--pm-line) !important;
  border-radius: var(--pm-radius) !important;
  box-shadow: var(--pm-shadow) !important;
  backdrop-filter: blur(var(--pm-card-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--pm-card-blur)) saturate(140%);
  animation: pmCardIn .58s cubic-bezier(.22,1,.36,1) backwards;
  transition:
    transform .5s cubic-bezier(.22,1,.36,1),
    box-shadow .38s ease, border-color .38s ease, background .38s ease;
}
@keyframes pmCardIn {
  from { opacity: 0; transform: translateY(12px); filter: blur(5px); }
  to   { opacity: 1; transform: none; filter: none; }
}
/* 顶部 1px 内高光：玻璃材质的关键细节 */
.pmcard::after {
  content: ""; position: absolute; top: 0; left: 12%; right: 12%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--pm-line), transparent);
  opacity: .9; pointer-events: none;
}
.pmcard:hover {
  transform: translateY(-5px) !important;
  border-color: var(--pm-accent) !important;
  box-shadow: var(--pm-shadow-hover) !important;
}
/* 悬停时的旋转流光描边 */
.pmcard::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1.2px;
  pointer-events: none; opacity: 0;
  background: conic-gradient(from var(--pma), transparent 0 58%,
              var(--pm-accent-2) 74%, var(--pm-accent) 84%, transparent 94%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  transition: opacity .3s ease;
}
.pmcard:hover::before { opacity: .85; animation: pmSpin 3.2s linear infinite; }
@property --pma { syntax: '<angle>'; inherits: false; initial-value: 0deg; }
@keyframes pmSpin { to { --pma: 360deg; } }
.pmcard .gloss {
  position: absolute; top: 0; bottom: 0; left: 0; width: 70px; pointer-events: none;
  background: linear-gradient(90deg, transparent, var(--pm-accent-soft), transparent);
  transform: translateX(-160px) skewX(-16deg); opacity: .9;
}
.pmcard:hover .gloss { animation: pmGloss 1.15s cubic-bezier(.3,.7,.4,1); }
@keyframes pmGloss { to { transform: translateX(760px) skewX(-16deg); } }

/* ---------- 7. 进度条 / 状态 ---------- */
.pmbar-wrap { display: inline-flex; align-items: center; gap: 9px; vertical-align: middle; }
.pmbar {
  display: inline-block; position: relative; width: 110px; height: 6px;
  border-radius: 99px; background: var(--pm-surface-3); overflow: hidden; vertical-align: middle;
}
.pmbar .pmfill {
  display: block; height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, var(--pm-accent), var(--pm-accent-2));
  animation: pmFill 1.15s cubic-bezier(.22,1,.36,1) backwards;
}
@keyframes pmFill { from { width: 0 !important; } }
.pmbar::after {
  content: ""; position: absolute; top: 0; bottom: 0; width: 54px; border-radius: 99px;
  background: linear-gradient(90deg, transparent, var(--pm-accent-soft), transparent);
  transform: translateX(-70px); animation: pmSweep 3.4s ease-in-out infinite;
}
@keyframes pmSweep { 0% { transform: translateX(-70px); } 62%,100% { transform: translateX(190px); } }
.pmpct { font-size: 11.5px; color: var(--pm-ink-3); font-variant-numeric: tabular-nums; }
.pmdot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px;
  vertical-align: middle; animation: pmPulse 2.8s ease-in-out infinite; }
@keyframes pmPulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .42; transform: scale(.86); } }

/* ---------- 8. 控件 token 化 ---------- */
/* 原生控件文字兜底：Streamlit 默认把文字色写死在 config 主题里，深色主题会看不见 */
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-baseweb="select"] div, [data-baseweb="select"] input, [data-baseweb="select"] span,
[data-baseweb="menu"] div, [role="listbox"] div {
  color: var(--pm-ink-2);
}
[data-baseweb="select"] svg, [data-testid="stSelectbox"] svg { fill: var(--pm-ink-3); }
/* Streamlit 1.4x 起 selectbox 换成 react-aria ComboBox：文字在 input.value 里 */
[data-testid="stSelectbox"] input, .react-aria-ComboBox input,
[data-testid="stMultiSelect"] input {
  color: var(--pm-ink) !important;
  -webkit-text-fill-color: var(--pm-ink) !important;
  font-size: 12.5px !important;
}
[data-testid="stSelectbox"] input::placeholder { color: var(--pm-ink-4) !important; -webkit-text-fill-color: var(--pm-ink-4) !important; }
[data-testid="stSelectbox"] button, [data-testid="stSelectbox"] [role="group"] { color: var(--pm-ink-3) !important; }
/* 所有输入类控件的"根壳"：Streamlit 默认把它画成纯白，深色主题下必须接管 */
[data-testid^="st"][data-testid$="RootElement"],
[data-testid="stNumberInputContainer"] {
  background: var(--pm-surface) !important;
  border-color: var(--pm-line) !important;
  border-radius: var(--pm-radius-sm) !important;
}
[data-testid^="st"][data-testid$="RootElement"]:focus-within {
  border-color: var(--pm-accent) !important;
  box-shadow: 0 0 0 3px var(--pm-accent-soft) !important;
}
.stTextInput input, .stTextArea textarea, [data-baseweb="input"], [data-baseweb="base-input"],
[data-testid="stTextInputField"], [data-testid="stNumberInputField"] {
  background: transparent !important; color: var(--pm-ink) !important;
  border: 0 !important; border-radius: var(--pm-radius-sm) !important;
  font-size: 13px !important;
}
[data-testid="stNumberInput"] button {
  background: var(--pm-surface-2) !important; color: var(--pm-ink-2) !important;
  border-color: var(--pm-line) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--pm-accent) !important;
  box-shadow: 0 0 0 3px var(--pm-accent-soft) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--pm-ink-4) !important; }
[data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div,
[data-baseweb="select"] > div {
  background: var(--pm-surface) !important; color: var(--pm-ink) !important;
  border: 1px solid var(--pm-line) !important; border-radius: var(--pm-radius-sm) !important;
  font-size: 12.5px !important;
}
[data-baseweb="select"] svg { fill: var(--pm-ink-3) !important; color: var(--pm-ink-3) !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul,
[data-baseweb="menu"], [data-baseweb="popover"] > div > div {
  background: var(--pm-surface) !important; border-color: var(--pm-line) !important;
  color: var(--pm-ink) !important;
}
[data-baseweb="popover"] li, [role="option"] {
  background: var(--pm-surface) !important; color: var(--pm-ink-2) !important; font-size: 12.5px !important;
}
[data-baseweb="popover"] li:hover, [role="option"]:hover {
  background: var(--pm-accent-soft) !important; color: var(--pm-ink) !important;
}
/* 侧栏里的主题下拉：做成"设置项"的样子 */
[data-testid="stSelectbox"] [role="group"] {
  background: var(--pm-surface) !important;
  border: 1px solid var(--pm-line) !important;
  border-radius: var(--pm-radius-sm) !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] {
  background: var(--pm-accent-soft) !important; border-color: transparent !important;
}

/* 按钮 */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  border: 1px solid var(--pm-line) !important; border-radius: var(--pm-radius-sm) !important;
  background: var(--pm-surface) !important; color: var(--pm-ink) !important;
  font-size: 12.5px !important; font-weight: 520 !important; box-shadow: none !important;
  transition: transform .34s cubic-bezier(.34,1.56,.64,1), box-shadow .26s, background .2s, border-color .2s, color .2s !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--pm-accent) !important; color: var(--pm-ink) !important;
  background: var(--pm-surface) !important; transform: translateY(-1px);
  box-shadow: 0 6px 18px var(--pm-accent-soft) !important;
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(0) scale(.985); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--pm-accent) !important; border-color: var(--pm-accent) !important;
  color: var(--pm-on-accent) !important; font-weight: 620 !important;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  filter: brightness(1.08); color: var(--pm-on-accent) !important;
  box-shadow: 0 10px 26px var(--pm-accent-soft) !important;
}

/* metric / code / 表格 / tabs / 提示 */
[data-testid="stMetric"] { background: transparent; border: 0; padding: 0; }
[data-testid="stMetricValue"] {
  font-size: 1.12rem !important; font-weight: 620 !important;
  color: var(--pm-ink) !important; font-variant-numeric: tabular-nums;
}
[data-testid="stMetricLabel"] p { font-size: 11px !important; color: var(--pm-ink-3) !important; letter-spacing: .05em; }
code {
  background: var(--pm-surface-2) !important; border: 0 !important;
  border-radius: 5px !important; color: var(--pm-ink-2) !important;
  padding: 1px 5px !important; font-size: 11.5px !important; font-family: var(--pm-mono) !important;
}
div[data-testid="stCodeBlock"] pre {
  background: var(--pm-surface-2) !important; border: 1px solid var(--pm-line) !important;
  border-radius: var(--pm-radius-sm) !important; color: var(--pm-ink-2) !important;
}
div[data-testid="stDataFrame"] {
  border: 1px solid var(--pm-line) !important; border-radius: var(--pm-radius-sm) !important;
  overflow: hidden; background: var(--pm-surface);
}
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--pm-line) !important; }
.stTabs [data-baseweb="tab"] {
  background: transparent; border: 0; border-bottom: 2px solid transparent; border-radius: 0;
  padding: 7px 13px; color: var(--pm-ink-3); font-size: 12.5px;
}
.stTabs [aria-selected="true"] {
  background: transparent !important; color: var(--pm-ink) !important;
  border-bottom-color: var(--pm-accent) !important; font-weight: 620;
}
[data-baseweb="notification"], [data-testid="stAlertContainer"] {
  background: var(--pm-surface-2) !important; border: 1px solid var(--pm-line) !important;
  border-radius: var(--pm-radius-sm) !important; color: var(--pm-ink-2) !important;
}
[data-baseweb="notification"] p, [data-testid="stAlertContainer"] p { color: var(--pm-ink-2) !important; font-size: 12.5px !important; }
[data-baseweb="notification"] svg { color: var(--pm-accent) !important; fill: var(--pm-accent) !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--pm-line) !important; border-radius: var(--pm-radius-sm) !important; }
[data-testid="stExpander"] details, [data-testid="stExpander"] > details > summary {
  background: var(--pm-surface) !important; border-color: var(--pm-line) !important;
  border-radius: var(--pm-radius-sm) !important; color: var(--pm-ink-2) !important;
}
[data-testid="stTooltipContent"], [data-baseweb="tooltip"] {
  background: var(--pm-ink) !important; color: var(--pm-bg) !important;
  border-radius: 8px !important; font-size: 11.5px !important;
}
/* 滚动条 */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--pm-line); border-radius: 8px; border: 3px solid transparent;
  background-clip: padding-box;
}
::-webkit-scrollbar-thumb:hover { background: var(--pm-ink-4); background-clip: padding-box; border: 3px solid transparent; }

/* ---------- 9. 滚动渐显（Chrome/Edge 115+ 原生 scroll-driven） ---------- */
@supports (animation-timeline: view()) {
  .pmcard { animation: pmReveal linear both; animation-timeline: view(); animation-range: entry 0% entry 42%; }
  @keyframes pmReveal { from { opacity: 0; } to { opacity: 1; } }
}

/* ---------- 10. 尊重系统"减少动态效果" ---------- */
@media (prefers-reduced-motion: reduce) {
  .stApp::after, #pmAurora, .pmdot, .pmbar::after, .pmlogo, #pmTopbar { animation: none !important; }
  .pmcard, .pmhero-title, .pmhero-sub, .pmhero-stats { animation: none !important; }
  * { transition-duration: .01ms !important; }
}
</style>
"""

# 初音主题专属：背景插画 + 漂浮音符（其它主题不加载，避免拖慢首屏）
CSS_MIKU_EXTRA = """
<style>
.stApp {
  background-image:
    linear-gradient(100deg, rgba(244,251,250,.96) 0%, rgba(244,251,250,.90) 30%,
                    rgba(244,251,250,.60) 58%, rgba(244,251,250,.22) 100%),
    url("__BG__") !important;
  background-size: cover, cover !important;
  background-position: center center, right center !important;
  background-attachment: fixed, fixed !important;
}
#pmNotes { position: fixed; inset: 0; overflow: hidden; pointer-events: none; z-index: 0; }
.pmhero-title {
  background-image: linear-gradient(92deg,#0F7A73 0%,#2BB3A9 62%,#6FDAD1 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
#pmNotes i { position: absolute; bottom: -40px; font-style: normal;
  color: rgba(43,179,169,.38); text-shadow: 0 0 10px rgba(43,179,169,.45);
  animation: pmRise linear infinite; }
@keyframes pmRise {
  0% { transform: translateY(0) rotate(0) scale(.9); opacity: 0; }
  12% { opacity: .9; }
  100% { transform: translateY(-112vh) rotate(240deg) scale(1.1); opacity: 0; }
}
</style>
"""
