"""共享的只读进度计算，供实时看板、静态快照与状态导出使用。

这是**唯一**的进度口径实现。三处必须都走这里，否则同一项目会出现两个百分比：
  - `dashboard.py`       实时看板
  - `export_static.py`   本地静态快照 index.html
  - `export_status.py`   可公开的 PROJECT-STATUS.md
"""


def progress_info(p):
    """L2 小项目 / L3 任务容器的进度：任务优先，其次目标，最后手填。

    返回 (百分比或 None, 口径说明)。
    """
    tasks = [t for t in (p.get("tasks") or []) if isinstance(t, dict)]
    if tasks:
        done = sum(1 for t in tasks if t.get("status") == "done")
        return round(done * 100 / len(tasks)), f"任务完成 {done}/{len(tasks)}"
    goals = [g for g in (p.get("goals") or []) if isinstance(g, dict)]
    if goals:
        done = sum(1 for g in goals if g.get("done"))
        return round(done * 100 / len(goals)), f"目标完成 {done}/{len(goals)}"
    value = p.get("progress")
    return (value, "手动填写") if isinstance(value, (int, float)) else (None, "未设定")


def child_projects(projects, pid):
    """L2：取某个 L1 下的小项目。"""
    return [p for p in projects if p.get("parent") == pid]


def program_rollup(projects, prog):
    """L1 聚合：子项目数、任务统计、进度（任务优先，无任务时取子项目均值）。

    L1 自己一般不挂任务，所以不能直接用 progress_info(prog) —— 那会读到空值或手填值，
    与看板显示的两个数打架。
    """
    kids = child_projects(projects, prog.get("id"))
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
