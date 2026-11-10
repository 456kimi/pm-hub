# -*- coding: utf-8 -*-
"""
PM-Hub 只读扫描器（P0 盘点 / 日常巡检）
- 项目发现: 指纹文件识别（.git/pyproject.toml/...），扫 H:/ G:/ 指定深度
- 应用清点: 卸载注册表(HKLM/HKCU) + 开始菜单 .lnk + 便携目录（只读，绝不写注册表/卸载/移动）
- 产出: reports/scan-YYYY-MM-DD.md + reports/unregistered.json，并回填 registry.json 空缺路径
- 铁律: 本脚本对文件系统零写入（除 reports/ 与 registry.json 自身），不进入禁区
"""
import json
import copy
from collections import Counter
import os
import re
import time
import winreg
from datetime import datetime
from pathlib import Path
from pm_registry import apply_registry, read_registry

HUB = Path(__file__).resolve().parent
REG_PATH = HUB / "registry.json"
REPORTS = HUB / "reports"

EXCLUDE_NAMES = {
    "$recycle.bin", "system volume information", "node_modules", "__pycache__",
    ".git", ".venv", "venv", "venvs", ".idea", ".vs", ".vscode", "dist", "build",
    "site-packages", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "target", ".next", "vendor", "deriveddata", ".cache", "__macosx",
}
EXCLUDE_PATH_PREFIXES = [
    r"E:\play", "C:\\", r"G:\g", r"G:\SteamLibrary", r"G:\CloudMusic",
    r"G:\Youku Files", r"G:\动漫", r"G:\夸克", r"G:\照片", r"G:\相机来",
    r"G:\视频", r"G:\MOD", r"H:\WindowsApps", r"H:\Program Files", r"H:\XBOX",
]
FINGERPRINT_FILES = [
    ".git", "pyproject.toml", "requirements.txt", "package.json", "Cargo.toml",
    "go.mod", "docker-compose.yml", "CLAUDE.md", "AGENTS.md", "WORKLOG.md",
    "STATUS.md", "pom.xml", "environment.yml", "plugin.json",
]
SCAN_ROOTS = [  # (路径, 深度)
    (r"H:\github", 2), (r"H:\ai", 1), ("H:\\", 1),
    (r"H:\Claw_backup", 1), (r"H:\voi", 1), (r"H:\3#罐组智能系统", 1),
    ("G:\\", 1), (r"G:\agents", 2), (r"G:\a", 2), (r"G:\wechat-export", 1),
    (r"E:\software", 1),
]
APP_PORTABLE_DIRS = [r"E:\software", r"H:\ai", r"G:\venvs"]
TIME_BUDGET_S = 100
DIR_BUDGET = 40000
TOPFILE_CAP = 400

KB_PAT = re.compile(
    r"^(KB\d+|Update for|Security Update|Definition Update|Cumulative Update"
    r"|Windows\s?(KB|Malicious)|.*Redistributable.*|Microsoft Edge WebView"
    r"|Windows SDK|Microsoft Visual Studio Code Settings|Intel\(R\))", re.I)

CATEGORY_RULES = [
    ("ai", ["whisper", "ollama", "kimi", "gpt", "llm", "model", "chatglm", "comfy", "stable"]),
    ("quant", ["qlib", "quant", "trade", "stock", "tdx"]),
    ("dev", ["git", "code", "studio", "jdk", "python", "node", "docker", "wsl", "sdk", "posh"]),
    ("browser", ["chrome", "firefox", "edge", "browser"]),
    ("media", ["vlc", "pot", "obs", "mpv", "ffmpeg", "audio", "video", "image"]),
    ("system", ["everything", "wiztree", "7-zip", "7zip", "bandizip", "disk", "monitor", "agent", "driver"]),
]


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def norm(s):
    return re.sub(r"[-_ ]", "", (s or "").lower())


def is_excluded(path: Path):
    p = str(path).rstrip("\\").lower()
    for pref in EXCLUDE_PATH_PREFIXES:
        if p.startswith(pref.lower().rstrip("\\") + "\\") or p == pref.lower().rstrip("\\"):
            return True
    return path.name.lower() in EXCLUDE_NAMES


def quick_stats(d: Path):
    n = size = 0
    mtime = 0.0
    try:
        with os.scandir(d) as it:
            for ch in it:
                n += 1
                if n > TOPFILE_CAP:
                    break
                try:
                    st = ch.stat()
                    mtime = max(mtime, st.st_mtime)
                    if ch.is_file():
                        size += st.st_size
                except OSError:
                    pass
    except OSError:
        pass
    return n, size, mtime


def fingerprints(d: Path):
    found = []
    for f in FINGERPRINT_FILES:
        if (d / f).exists():
            found.append(f)
    try:
        with os.scandir(d) as it:
            for ch in it:
                if ch.name.lower().endswith(".sln"):
                    found.append("*.sln")
                    break
    except OSError:
        pass
    return found


def scan_projects():
    found = {}
    all_dirs = []
    t0 = time.time()
    visited = 0

    def walk(d: Path, depth):
        nonlocal visited
        if visited >= DIR_BUDGET or time.time() - t0 > TIME_BUDGET_S:
            return
        if is_excluded(d):
            return
        visited += 1
        all_dirs.append(str(d).rstrip("\\"))
        pr = fingerprints(d)
        if pr:
            n, size, mt = quick_stats(d)
            found[str(d).rstrip("\\")] = {
                "path": str(d).rstrip("\\"), "name": d.name, "prints": pr,
                "top_files": n, "top_size": size, "mtime": mt,
            }
            return  # 项目目录内部不再下钻
        if depth > 0:
            try:
                with os.scandir(d) as it:
                    children = [e for e in it if e.is_dir()]
            except OSError:
                return
            for ch in children:
                walk(Path(ch.path), depth - 1)

    for root, depth in SCAN_ROOTS:
        rp = Path(root)
        if rp.is_dir():
            walk(rp, depth)
    return list(found.values()), visited, all_dirs


def registry_apps():
    out = {}
    hives = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, sub in hives:
        try:
            base = winreg.OpenKey(hive, sub)
        except OSError:
            continue
        with base:
            i = 0
            while True:
                try:
                    sk = winreg.EnumKey(base, i)
                    i += 1
                except OSError:
                    break
                try:
                    with winreg.OpenKey(base, sk) as kk:
                        def gv(n):
                            try:
                                v, _ = winreg.QueryValueEx(kk, n)
                                return v if isinstance(v, str) else ""
                            except OSError:
                                return ""
                        name = gv("DisplayName").strip()
                        if not name or KB_PAT.match(name):
                            continue
                        key = name.lower()
                        ver = gv("DisplayVersion")
                        loc = gv("InstallLocation").strip()
                        icon = gv("DisplayIcon")
                        exe = icon.split(",")[0].strip() if icon else ""
                        cur = out.get(key)
                        if cur is None:
                            out[key] = {"name": name, "version": ver, "exe": exe,
                                        "path": loc, "source": "registry"}
                        else:
                            cur["version"] = cur["version"] or ver
                            cur["exe"] = cur["exe"] or exe
                            cur["path"] = cur["path"] or loc
                except OSError:
                    continue
    return out


def startmenu_apps():
    out = {}
    sm_dirs = []
    pd = os.environ.get("ProgramData", r"C:\ProgramData")
    ad = os.environ.get("APPDATA", "")
    sm_dirs.append(Path(pd) / "Microsoft" / "Windows" / "Start Menu")
    if ad:
        sm_dirs.append(Path(ad) / "Microsoft" / "Windows" / "Start Menu")
    for base in sm_dirs:
        if not base.is_dir():
            continue
        for p in base.rglob("*.lnk"):
            name = p.stem
            if not name or "uninstall" in name.lower():
                continue
            key = name.lower()
            if key not in out:
                out[key] = {"name": name, "version": "", "exe": "",
                            "path": str(p), "source": "startmenu"}
    return out


def guess_category(text):
    t = text.lower()
    for cat, kws in CATEGORY_RULES:
        for kw in kws:
            if kw in t:
                return cat
    return "other"


def dedupe_apps(reg):
    """按 norm(name) 去重，保留信息最全的一条；合并非空字段"""
    seen = {}
    out = []
    for a in reg["apps"]:
        k = norm(a["name"])
        if k not in seen:
            seen[k] = a
            out.append(a)
            continue
        keep = seen[k]
        for f in ("path", "exe", "version", "purpose"):
            if not keep.get(f) and a.get(f):
                keep[f] = a[f]
        if a.get("desc_confirmed") and not keep.get("desc_confirmed"):
            keep["desc_confirmed"] = True
            keep["purpose"] = keep.get("purpose") or a.get("purpose", "")
    reg["apps"] = out


def assign_unique_ids(existing_apps, new_apps):
    """给新应用分配唯一 id（就地修改并返回 new_apps）。

    id 由 `norm(name)[:40]` 生成，不同名字截断到 40 字符后会撞车；因此必须按
    **id** 判重，不能按 name。历史实现比对的是 name 集合，导致两个不同应用拿到
    同一个 id（2026-11-10 实测台账有 1 例 microsoft.net.workload.mono.toolchain.ne）。
    """
    have = {a.get("id") for a in existing_apps if a.get("id")}
    for a in new_apps:
        base = a.get("id") or norm(a.get("name", "")) or "app"
        nid, n = base, 2
        while nid in have:
            nid = "%s-%d" % (base, n)
            n += 1
        a["id"] = nid
        have.add(nid)
    return new_apps


def merge_apps(reg):
    dedupe_apps(reg)
    discovered = {}
    for src in (registry_apps(), startmenu_apps()):
        for key, app in src.items():
            if key not in discovered:
                discovered[key] = dict(app)
            else:
                cur = discovered[key]
                cur["version"] = cur["version"] or app["version"]
                cur["exe"] = cur["exe"] or app["exe"]
                cur["path"] = cur["path"] or app["path"]

    by_norm = {norm(a["name"]): a for a in reg["apps"]}
    new_apps, filled = [], []
    for key, disc in discovered.items():
        existing = by_norm.get(norm(disc["name"]))
        if existing:
            changed = False
            for f in ("path", "exe", "version"):
                if not existing.get(f) and disc.get(f):
                    existing[f] = disc[f]
                    changed = True
            if changed:
                filled.append(existing["name"])
        else:
            new_apps.append({
                "id": norm(disc["name"])[:40] or disc["name"],
                "name": disc["name"],
                "purpose": "",
                "category": guess_category(disc["name"] + " " + disc.get("path", "")),
                "path": disc.get("path", ""), "exe": disc.get("exe", ""),
                "version": disc.get("version", ""), "usage": "unknown",
                "source": disc.get("source", "scan"),
                "desc_confirmed": False, "related_projects": [],
            })
    # id 去重：按 id 判重（详见 assign_unique_ids 的说明）
    assign_unique_ids(reg["apps"], new_apps)
    reg["apps"].extend(new_apps)
    return new_apps, filled


def fmt_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}TB"


def top_level_dirs():
    """各盘根的直接子目录（顶层全景，供"文件放在哪里"与待整理清单）"""
    out = []
    roots = ["H:\\", "G:\\"]
    for root in roots:
        rp = Path(root)
        if not rp.is_dir():
            continue
        try:
            with os.scandir(rp) as it:
                for ch in it:
                    if not ch.is_dir() or is_excluded(Path(ch.path)):
                        continue
                    p = Path(ch.path)
                    if any(str(p).lower().startswith(x.lower().rstrip("\\") + "\\")
                           for x in EXCLUDE_PATH_PREFIXES):
                        continue
                    n, size, mt = quick_stats(p)
                    out.append({"path": str(p).rstrip("\\"), "name": p.name,
                                "prints": [], "top_files": n, "top_size": size,
                                "mtime": mt, "level": "top"})
        except OSError:
            pass
    return out


def main():
    reg = read_registry(REG_PATH)
    baseline = copy.deepcopy(reg)
    print("[1/4] 扫描项目指纹 ...")
    cands, visited, all_dirs = scan_projects()
    print(f"      发现 {len(cands)} 个候选目录（遍历 {visited} 个目录）")

    # 回填/匹配已知项目（先指纹候选，再全目录名匹配）
    matched, unregistered = [], []
    proj_by_root = {}
    for p in reg["projects"]:
        r = p["paths"].get("root", "")
        if r:
            proj_by_root[norm(r)] = p

    def try_link(p, cpath, cname):
        """按名字回填空缺 root，成功返回 True"""
        if p["paths"].get("root"):
            return False
        nid, ndir = norm(p["id"]), norm(cname)
        if ndir == nid or (len(nid) >= 8 and nid in ndir) or (len(ndir) >= 8 and ndir in nid):
            p["paths"]["root"] = cpath
            p["notes"] = (p.get("notes", "") + " | scanner 回填路径 " + cpath).strip(" |")
            return True
        return False

    for c in cands:
        nc = norm(c["path"])
        hit = proj_by_root.get(nc)
        if hit:
            matched.append((c, hit, "exact"))
            continue
        link = None
        for p in reg["projects"]:
            if try_link(p, c["path"], c["name"]):
                link = p
                break
        if link:
            md = datetime.fromtimestamp(c["mtime"]).strftime("%Y-%m-%d") if c["mtime"] else ""
            if md and md > (link.get("last_activity") or ""):
                link["last_activity"] = md
            matched.append((c, link, "name-link"))
            proj_by_root[nc] = link
        else:
            unregistered.append(c)

    # 无指纹的已知项目：从所有访问过的目录按名字找
    for p in reg["projects"]:
        if p["paths"].get("root"):
            continue
        for d in all_dirs:
            if try_link(p, d, Path(d).name):
                md = datetime.fromtimestamp(Path(d).stat().st_mtime).strftime("%Y-%m-%d")
                if md > (p.get("last_activity") or ""):
                    p["last_activity"] = md
                break
    # 仍无 root 的已知项目：从顶层目录找（覆盖无指纹数据目录，如 free-stockdb）
    tops = top_level_dirs()
    for p in reg["projects"]:
        if p["paths"].get("root"):
            continue
        for c in tops:
            if try_link(p, c["path"], c["name"]):
                break

    # 顶层目录进未登记清单（排除已登记项目 root 与文件地标）
    registered_roots = {norm(p["paths"].get("root", "")) for p in reg["projects"]}
    loc_paths = {norm(l.get("path", "")) for l in reg.get("locations", [])}
    for c in tops:
        if norm(c["path"]) in registered_roots or norm(c["path"]) in loc_paths:
            continue
        unregistered.append(c)
    print(f"      匹配已知项目 {len(matched)} 个，未登记候选 {len(unregistered)} 个")

    print("[2/4] 清点应用（注册表 + 开始菜单）...")
    new_apps, filled = merge_apps(reg)
    print(f"      新增应用 {len(new_apps)} 个，回填已知应用路径 {len(filled)} 个")

    print("[3/4] 更新台账与报告 ...")
    dedupe_stats = {"merged": 0, "skipped": 0}
    applied_new_apps = []
    applied_filled_apps = []

    def apply_scan(latest):
        # Recheck the original empty fields while holding the registry lock.
        # Concurrent manual edits always take precedence over scan candidates.
        before_projects = {p.get("id"): p for p in baseline["projects"]}
        candidates = {p.get("id"): p for p in reg["projects"]}
        before_project_counts = Counter(p.get("id") for p in baseline["projects"])
        current_project_counts = Counter(p.get("id") for p in latest["projects"])
        for current in latest["projects"]:
            old = before_projects.get(current.get("id"))
            candidate = candidates.get(current.get("id"))
            if (not old or not candidate or before_project_counts[current.get("id")] != 1
                    or current_project_counts[current.get("id")] != 1):
                continue
            root = candidate.get("paths", {}).get("root")
            if root and not old.get("paths", {}).get("root") and not current.get("paths", {}).get("root"):
                current.setdefault("paths", {})["root"] = root
                note = "scanner 回填路径 " + root
                current["notes"] = (current.get("notes", "") + " | " + note).strip(" |")
                current["last_activity"] = max(current.get("last_activity") or "", candidate.get("last_activity") or "")

        before_groups = {}
        current_groups = {}
        for app in baseline["apps"]:
            before_groups.setdefault(norm(app["name"]), []).append(app)
        for app in latest["apps"]:
            current_groups.setdefault(norm(app["name"]), []).append(app)
        removed = set()
        for key, group in current_groups.items():
            if len(group) < 2:
                continue
            if group != before_groups.get(key):
                dedupe_stats["skipped"] += 1
                continue
            deduped = {"apps": group}
            dedupe_apps(deduped)
            removed.update(id(a) for a in group[1:])
            dedupe_stats["merged"] += len(group) - 1
        latest["apps"] = [a for a in latest["apps"] if id(a) not in removed]

        app_key = lambda a: (a.get("id"), norm(a.get("name", "")))
        before_counts = Counter(app_key(a) for a in baseline["apps"])
        current_counts = Counter(app_key(a) for a in latest["apps"])
        before_apps = {app_key(a): a for a in baseline["apps"]}
        current_apps = {app_key(a): a for a in latest["apps"]}
        current_ids = {a.get("id") for a in latest["apps"]}
        current_names = {norm(a.get("name", "")) for a in latest["apps"]}
        for candidate in reg["apps"]:
            aid = candidate.get("id")
            key = app_key(candidate)
            old = before_apps.get(key)
            current = current_apps.get(key)
            if old and current and before_counts[key] == 1 and current_counts[key] == 1:
                changed = False
                for field in ("path", "exe", "version"):
                    if not old.get(field) and not current.get(field) and candidate.get(field):
                        current[field] = candidate[field]
                        changed = True
                if changed:
                    applied_filled_apps.append(current["name"])
            elif not old and aid not in current_ids and norm(candidate.get("name", "")) not in current_names:
                latest["apps"].append(copy.deepcopy(candidate))
                applied_new_apps.append(candidate)
                current_ids.add(aid)
                current_names.add(norm(candidate.get("name", "")))

    import export_static
    result = apply_registry("scanner", apply_scan, path=REG_PATH, export=export_static.export)
    committed = result.data
    print(f"      去重合并 {dedupe_stats['merged']} 项，跳过有并发变化的重复组 {dedupe_stats['skipped']} 组")
    print(f"      实际新增应用 {len(applied_new_apps)} 个，回填 {len(applied_filled_apps)} 个")

    # A project or landmark may have been registered during the long scan.
    registered_roots = {norm(p.get("paths", {}).get("root", "")) for p in committed["projects"]}
    loc_paths = {norm(loc.get("path", "")) for loc in committed.get("locations", [])}
    known_paths = registered_roots | loc_paths
    unregistered = [c for c in unregistered if norm(c["path"]) not in known_paths]

    REPORTS.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    # 按路径去重（指纹候选与顶层枚举可能重叠）
    dedup = {c["path"]: c for c in unregistered}
    unregistered = sorted(dedup.values(), key=lambda x: -x.get("top_size", 0))
    (REPORTS / "unregistered.json").write_text(
        json.dumps(unregistered, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# PM-Hub 盘点报告 {today}", "",
             f"- 扫描根: {', '.join(r for r, _ in SCAN_ROOTS)}（深度 1-2，只读）",
             f"- 遍历目录 {visited} 个；候选项目 {len(cands)}；已匹配 {len(matched)}；未登记 {len(unregistered)}",
             f"- 应用台账共 {len(committed['apps'])} 个（本次新增 {len(applied_new_apps)}，回填 {len(applied_filled_apps)}）", ""]
    lines += ["## 已匹配项目", "", "| 项目 | 路径 | 指纹 | 方式 |", "|---|---|---|---|"]
    for c, p, how in matched:
        lines.append(f"| {p['id']} | `{c['path']}` | {', '.join(c['prints'][:4])} | {how} |")
    lines += ["", "## 未登记候选（待裁决，只列不动）", "",
              "| 目录 | 指纹 | 顶层体积 | 顶层文件数 |", "|---|---|---|---|"]
    for c in sorted(unregistered, key=lambda x: -x["top_size"])[:60]:
        lines.append(f"| `{c['path']}` | {', '.join(c['prints'][:4]) or '-'} | {fmt_size(c['top_size'])} | {c['top_files']} |")
    lines += ["", "## 本次新增应用（用途待补，AI 可代拟后由老板确认）", ""]
    for a in applied_new_apps[:80]:
        lines.append(f"- **{a['name']}** `{a['path'] or a['exe'] or '?'}` [{a['category']}]")
    (REPORTS / f"scan-{today}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"      报告: reports/scan-{today}.md")

    print("[4/4] 导出静态 index.html ...")
    if result.export_error:
        print(f"      台账已保存，静态导出失败，请单独重导: {result.export_error}")
    else:
        print("      index.html 完成")
    print("完成。全程只读，未移动/删除任何文件。")


if __name__ == "__main__":
    main()
