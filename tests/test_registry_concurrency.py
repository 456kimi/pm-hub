import copy
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

import pm_registry


def _concurrent_write(path, ready, start, results, title):
    from pm_registry import read_registry, save_registry
    base = read_registry(path)
    changed = copy.deepcopy(base)
    changed["projects"][0]["tasks"].append({"id": "t1", "title": title, "status": "todo"})
    ready.put(True)
    start.wait(15)
    try:
        save_registry(base, changed, title, path=path)
        results.put(None)
    except Exception as exc:
        results.put(repr(exc))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.path = Path(self.temp.name) / "registry.json"
        self.data = {"projects": [{"id": "p", "name": "old", "tasks": [], "progress_log": []}], "apps": []}
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_two_processes_add_distinct_tasks(self):
        ctx = multiprocessing.get_context("spawn")
        ready, results, start = ctx.Queue(), ctx.Queue(), ctx.Event()
        workers = [ctx.Process(target=_concurrent_write, args=(str(self.path), ready, start, results, title)) for title in ("A", "B")]
        for worker in workers:
            worker.start()
        for _ in workers:
            ready.get(timeout=20)
        start.set()
        for worker in workers:
            worker.join(timeout=20)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual([results.get(timeout=2) for _ in workers], [None, None])
        tasks = pm_registry.read_registry(self.path)["projects"][0]["tasks"]
        self.assertEqual({t["title"] for t in tasks}, {"A", "B"})
        self.assertEqual(len({t["id"] for t in tasks}), 2)

    def test_same_field_conflict_preserves_first_update(self):
        base = copy.deepcopy(self.data)
        first, second = copy.deepcopy(base), copy.deepcopy(base)
        first["projects"][0]["name"] = "one"
        second["projects"][0]["name"] = "two"
        pm_registry.save_registry(base, first, "A", self.path)
        with self.assertRaises(pm_registry.RegistryConflict):
            pm_registry.save_registry(base, second, "B", self.path)
        self.assertEqual(pm_registry.read_registry(self.path)["projects"][0]["name"], "one")

    def test_identical_concurrent_new_task_ids_are_not_lost(self):
        a = copy.deepcopy(self.data)
        a["projects"][0]["tasks"].append({"id": "t1", "title": "same", "status": "todo"})
        pm_registry.save_registry(self.data, a, "A", self.path)
        pm_registry.save_registry(self.data, a, "B", self.path)
        tasks = pm_registry.read_registry(self.path)["projects"][0]["tasks"]
        self.assertEqual({t["id"] for t in tasks}, {"t1", "t2"})

    def test_concurrent_log_appends_survive(self):
        base = copy.deepcopy(self.data)
        a, b = copy.deepcopy(base), copy.deepcopy(base)
        a["projects"][0]["progress_log"].append({"text": "A"})
        b["projects"][0]["progress_log"].append({"text": "B"})
        pm_registry.save_registry(base, a, "A", self.path)
        pm_registry.save_registry(base, b, "B", self.path)
        logs = pm_registry.read_registry(self.path)["projects"][0]["progress_log"]
        self.assertEqual([entry["text"] for entry in logs], ["A", "B"])

    def test_identical_concurrent_log_events_are_both_preserved(self):
        a = copy.deepcopy(self.data)
        a["projects"][0]["progress_log"].append({"date": "2026-11-10", "text": "event"})
        pm_registry.save_registry(self.data, a, "A", self.path)
        pm_registry.save_registry(self.data, a, "B", self.path)
        events = pm_registry.read_registry(self.path)["projects"][0]["progress_log"]
        self.assertEqual(len(events), 2)

    def test_identical_concurrent_regular_list_values_are_not_duplicated(self):
        base = copy.deepcopy(self.data)
        base["projects"][0]["paths"] = {"data": []}
        self.path.write_text(json.dumps(base), encoding="utf-8")
        a = copy.deepcopy(base)
        a["projects"][0]["paths"]["data"].append("data-dir")
        pm_registry.save_registry(base, a, "A", self.path)
        pm_registry.save_registry(base, a, "B", self.path)
        paths = pm_registry.read_registry(self.path)["projects"][0]["paths"]["data"]
        self.assertEqual(paths, ["data-dir"])

    def test_guard_observes_latest_state_and_blocks_stale_decision_edit(self):
        base = copy.deepcopy(self.data)
        base["projects"][0]["decisions"] = [{"id": "d1", "status": "active", "text": "old"}]
        self.path.write_text(json.dumps(base), encoding="utf-8")
        revoked = copy.deepcopy(base)
        revoked["projects"][0]["decisions"][0]["status"] = "revoked"
        pm_registry.save_registry(base, revoked, "A", self.path)
        edited = copy.deepcopy(base)
        edited["projects"][0]["decisions"][0]["text"] = "new"
        def guard(current):
            if current["projects"][0]["decisions"][0]["status"] != "active":
                raise pm_registry.RegistryConflict("decision revoked")
        with self.assertRaises(pm_registry.RegistryConflict):
            pm_registry.save_registry(base, edited, "B", self.path, guard=guard)
        decision = pm_registry.read_registry(self.path)["projects"][0]["decisions"][0]
        self.assertEqual((decision["status"], decision["text"]), ("revoked", "old"))

    def test_export_failure_reports_commit(self):
        edited = copy.deepcopy(self.data)
        edited["projects"][0]["name"] = "saved"
        def fail(_):
            raise OSError("export failed")
        result = pm_registry.save_registry(self.data, edited, "A", self.path, fail)
        self.assertEqual(result.export_error, "export failed")
        self.assertEqual(pm_registry.read_registry(self.path)["projects"][0]["name"], "saved")

    def test_export_retry_reads_latest_without_changing_registry(self):
        updated = copy.deepcopy(self.data)
        updated["projects"][0]["name"] = "latest"
        pm_registry.save_registry(self.data, updated, "A", self.path)
        before = self.path.read_bytes()
        snapshots = []
        result = pm_registry.export_registry(snapshots.append, self.path)
        self.assertIsNone(result.export_error)
        self.assertEqual(snapshots[0]["projects"][0]["name"], "latest")
        self.assertEqual(self.path.read_bytes(), before)

    def test_replace_failure_keeps_original_and_backup(self):
        from unittest.mock import patch
        edited = copy.deepcopy(self.data)
        edited["projects"][0]["name"] = "new"
        with patch("pm_registry.os.replace", side_effect=OSError("failure")):
            with self.assertRaises(OSError):
                pm_registry.save_registry(self.data, edited, "A", self.path)
        self.assertEqual(pm_registry.read_registry(self.path), self.data)
        self.assertEqual(len(list((self.path.parent / "registry.backups").glob("*.json"))), 1)

    def test_static_export_failure_keeps_previous_page(self):
        from unittest.mock import patch
        import export_static
        target = self.path.parent / "index.html"
        target.write_text("previous page", encoding="utf-8")
        with patch.object(export_static, "HUB", self.path.parent), \
             patch.object(export_static, "PREFS_PATH", self.path.parent / "prefs.json"), \
             patch.object(export_static.os, "replace", side_effect=OSError("failure")):
            with self.assertRaises(OSError):
                export_static.export({"projects": [], "apps": [], "locations": []})
        self.assertEqual(target.read_text(encoding="utf-8"), "previous page")

    def test_static_export_success_replaces_page(self):
        from unittest.mock import patch
        import export_static
        target = self.path.parent / "index.html"
        target.write_text("previous page", encoding="utf-8")
        with patch.object(export_static, "HUB", self.path.parent), \
             patch.object(export_static, "PREFS_PATH", self.path.parent / "prefs.json"):
            export_static.export({"projects": [], "apps": [], "locations": []})
        self.assertIn("</html>", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
