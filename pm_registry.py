"""Cooperatively serialize registry updates across local processes."""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from pm_progress import progress_info

REGISTRY = Path(__file__).resolve().parent / "registry.json"
_MISSING = object()
_KEYED = {"projects", "apps", "locations", "tasks", "goals", "decisions", "relations"}


class RegistryConflict(Exception):
    """A value being edited has changed since it was read."""


class RegistryLockTimeout(Exception):
    """The registry lock was not available in time."""


@dataclass
class SaveResult:
    data: dict
    export_error: str | None = None


class _Lock:
    def __init__(self, path, timeout=20):
        self.path = Path(str(path) + ".lock")
        self.timeout = timeout
        self.file = None

    def __enter__(self):
        self.file = self.path.open("a+b")
        if self.file.seek(0, os.SEEK_END) == 0:
            self.file.write(b"0")
            self.file.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as exc:
                if time.monotonic() >= deadline:
                    self.file.close()
                    raise RegistryLockTimeout("台账正在被其他进程使用，请稍后重试") from exc
                time.sleep(0.05)

    def __exit__(self, *args):
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        self.file.close()


def read_registry(path=None):
    return json.loads(Path(path or REGISTRY).read_text(encoding="utf-8"))


def _clone(value):
    return value if value is _MISSING else copy.deepcopy(value)


def _keyed(items):
    return all(isinstance(x, dict) and x.get("id") is not None for x in items) and len({x["id"] for x in items}) == len(items)


def _merge_keyed(base, ours, current, path):
    old = {x["id"]: x for x in base}
    mine = {x["id"]: x for x in ours}
    theirs = {x["id"]: x for x in current}
    result = []
    for item in current:
        key = item["id"]
        if key not in old and key in mine:
            # Two additions independently chose the same generated ID.
            prefix = {"tasks": "t", "goals": "g", "decisions": "d"}.get(path[-1])
            if not prefix or not re.fullmatch(prefix + r"\d+", str(key)):
                raise RegistryConflict("新增项目 ID 冲突: " + "/".join(path + (str(key),)))
            continue
        merged = _merge(old.get(key, _MISSING), mine.get(key, _MISSING), item, path + (str(key),))
        if merged is not _MISSING:
            result.append(merged)
    for item in ours:
        key = item["id"]
        if key in old and key not in theirs:
            _merge(old[key], item, _MISSING, path + (str(key),))
        elif key not in theirs:
            result.append(copy.deepcopy(item))
        elif key not in old:
            # Keep both additions and give our generated ID the next free number.
            result.append(copy.deepcopy(theirs[key]))
            used = {str(x["id"]) for x in current + ours + result}
            prefix = {"tasks": "t", "goals": "g", "decisions": "d"}[path[-1]]
            number = max([int(s[1:]) for s in used if re.fullmatch(prefix + r"\d+", s)] or [0]) + 1
            addition = copy.deepcopy(item)
            addition["id"] = prefix + str(number)
            result.append(addition)
    return result


def _merge(base, ours, current, path=()):
    if ours == base:
        return _clone(current)
    if current == base:
        return _clone(ours)
    # Concurrent additions with a shared generated ID must both survive.
    if (path and path[-1] in _KEYED and all(isinstance(x, list) and _keyed(x) for x in (base, ours, current))):
        return _merge_keyed(base, ours, current, path)
    if all(isinstance(x, list) for x in (base, ours, current)) and ours[:len(base)] == base and current[:len(base)] == base:
        merged = copy.deepcopy(current)
        for value in ours[len(base):]:
            if path and path[-1] in {"progress_log", "ai_logs", "dev_logs"}:
                merged.append(copy.deepcopy(value))
            elif value not in merged:
                merged.append(copy.deepcopy(value))
        return merged
    if all(isinstance(x, dict) for x in (base, ours, current)):
        merged = {}
        for key in dict.fromkeys([*base, *current, *ours]):
            if not path and key in {"updated_at", "operator"}:
                continue
            if key in {"updated", "last_activity"} and all(isinstance(d.get(key), str) for d in (base, ours, current)):
                merged[key] = max(ours[key], current[key])
                continue
            if key == "progress" and path and path[0] == "projects" and (ours.get("tasks") or ours.get("goals") or current.get("tasks") or current.get("goals")):
                continue
            value = _merge(base.get(key, _MISSING), ours.get(key, _MISSING), current.get(key, _MISSING), path + (key,))
            if value is not _MISSING:
                merged[key] = value
        if len(path) == 2 and path[0] == "projects" and (merged.get("tasks") or merged.get("goals")):
            merged["progress"] = progress_info(merged)[0]
        return merged
    if ours == current:
        return _clone(ours)
    raise RegistryConflict("数据已被其他操作修改，请比较后重试: " + "/".join(path))


def _write(path, data, original):
    backup_dir = path.parent / (path.stem + ".backups")
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex + ".json")
    with backup.open("xb") as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.stem + ".", suffix=".tmp", delete=False) as f:
            temp_path = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _commit(path, current, data, original, operator, export):
    data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["operator"] = operator
    _write(path, data, original)
    error = None
    if export is not None:
        try:
            export(copy.deepcopy(data))
        except Exception as exc:
            error = str(exc) or type(exc).__name__
    return SaveResult(data=data, export_error=error)


def save_registry(base, edited, operator, path=None, export=None, guard=None):
    path = Path(path or REGISTRY)
    with _Lock(path):
        original = path.read_bytes()
        current = json.loads(original.decode("utf-8"))
        if guard is not None:
            guard(copy.deepcopy(current))
        data = _merge(base, edited, current)
        return _commit(path, current, data, original, operator, export)


def apply_registry(operator, mutator, path=None, export=None):
    path = Path(path or REGISTRY)
    with _Lock(path):
        original = path.read_bytes()
        current = json.loads(original.decode("utf-8"))
        data = copy.deepcopy(current)
        mutator(data)
        return _commit(path, current, data, original, operator, export)


def export_registry(export, path=None):
    """Export the newest committed snapshot while holding the writer lock."""
    path = Path(path or REGISTRY)
    with _Lock(path):
        data = read_registry(path)
        try:
            export(copy.deepcopy(data))
        except Exception as exc:
            return SaveResult(data=data, export_error=str(exc) or type(exc).__name__)
        return SaveResult(data=data)


def main():
    parser = argparse.ArgumentParser(description="PM-Hub 台账安全读写")
    parser.add_argument("--registry", help="台账路径，默认使用 PM-Hub 台账")
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="保存一份编辑基准")
    snapshot.add_argument("--output", required=True)
    apply = sub.add_parser("apply", help="按基准合并已编辑的副本")
    apply.add_argument("--base", required=True)
    apply.add_argument("--edited", required=True)
    apply.add_argument("--operator", required=True)
    sub.add_parser("export", help="重新生成静态页")
    args = parser.parse_args()
    if args.command == "snapshot":
        target = Path(args.output).resolve()
        if target == Path(args.registry or REGISTRY).resolve():
            parser.error("快照输出不能覆盖台账")
        with target.open("x", encoding="utf-8") as f:
            json.dump(read_registry(args.registry), f, ensure_ascii=False, indent=2)
        print("快照已保存")
        return
    if args.command == "export":
        if Path(args.registry or REGISTRY).resolve() != REGISTRY.resolve():
            parser.error("自定义台账不能导出到正式静态页")
        import export_static
        result = export_registry(export_static.export, args.registry)
        if result.export_error:
            parser.exit(1, "静态页更新失败: " + result.export_error + "\n")
        print("静态页已更新")
        return
    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    edited = json.loads(Path(args.edited).read_text(encoding="utf-8"))
    try:
        import export_static
        callback = export_static.export if Path(args.registry or REGISTRY).resolve() == REGISTRY.resolve() else None
        result = save_registry(base, edited, args.operator, args.registry, callback)
    except (RegistryConflict, RegistryLockTimeout) as exc:
        parser.exit(2, str(exc) + "\n")
    print("台账已保存" + ("，静态页更新失败: " + result.export_error if result.export_error else ""))


if __name__ == "__main__":
    main()
