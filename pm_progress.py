"""共享的只读进度计算，供实时看板与静态快照使用。"""


def progress_info(p):
    """按任务、目标、手动值的优先顺序计算进度及说明。"""
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
