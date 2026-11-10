"""Dashboard regressions exercised with a synthetic, isolated registry."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import export_static
import pm_handoff
import pm_registry


ROOT = Path(__file__).resolve().parents[1]


class DashboardConcurrencyTests(unittest.TestCase):
    def setUp(self):
        main_module = sys.modules["__main__"]
        main_file = getattr(main_module, "__file__", None)
        argv = sys.argv[:]
        self.tmp = tempfile.TemporaryDirectory(prefix="pmhub-test-", dir=ROOT / "tests")
        self.addCleanup(self.tmp.cleanup)
        def restore_process_state():
            sys.modules["__main__"] = main_module
            if main_file is None:
                main_module.__dict__.pop("__file__", None)
            else:
                main_module.__file__ = main_file
            sys.argv[:] = argv
        self.addCleanup(restore_process_state)
        self.root = Path(self.tmp.name)
        # AppTest shares sys.modules with this process; never let the cached
        # production exporter write its default output during fixture saves.
        exporter_root = patch.object(export_static, "HUB", self.root)
        exporter_root.start()
        self.addCleanup(exporter_root.stop)
        # Same hazard for the handoff module: its default root is the real repo's
        # .pmhub/handoffs, so redirect it into the fixture before any button click.
        handoff_root = patch.object(pm_handoff, "ROOT", self.root)
        handoff_root.start()
        self.addCleanup(handoff_root.stop)
        for name in ("dashboard.py", "theme.py", "pm_progress.py", "pm_registry.py",
                     "pm_handoff.py", "export_static.py"):
            shutil.copy2(ROOT / name, self.root / name)
        self.registry = self.root / "registry.json"
        data = {
            "projects": [{
                "id": "demo", "name": "Example", "kind": "project", "status": "active",
                "parent": None, "paths": {"root": ""},
                "tasks": [{"id": "t1", "title": "Original", "status": "todo",
                           "acceptance": "页面可打开且无异常"}],
                "decisions": [{"id": "d1", "text": "Original decision", "status": "active"}],
            }],
            "apps": [], "locations": [],
        }
        self.registry.write_text(json.dumps(data), encoding="utf-8")
        self.app = AppTest.from_file(str(self.root / "dashboard.py"), default_timeout=60)
        self.app.session_state["nav"] = "🔍 项目详情"
        self.app.session_state["current_pid"] = "demo"
        self.app.run()
        self.assertFalse(self.app.exception)

    def text(self, label):
        return next(item for item in self.app.text_input if item.label == label)

    def click(self, label):
        next(item for item in self.app.button if item.label == label).click().run()

    def test_old_form_conflict_preserves_draft(self):
        base = pm_registry.read_registry(self.registry)
        edited = pm_registry.read_registry(self.registry)
        edited["projects"][0]["tasks"][0]["title"] = "External"
        pm_registry.save_registry(base, edited, "external", path=self.registry)
        self.text("标题").set_value("My draft")
        self.click("保存")
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertEqual(self.text("标题").value, "My draft")
        self.assertEqual(pm_registry.read_registry(self.registry)["projects"][0]["tasks"][0]["title"], "External")

    def test_old_format_add_saves_and_clears_form(self):
        self.text("任务标题").set_value("New task")
        # 验收标准为必填项（P0-03：无验收标准的任务不可交付）
        self.text("验收标准（必须可判定）").set_value("连续 3 个交易日自动更新，日志无报错")
        self.click("添加任务")
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.error)
        self.assertEqual(self.text("任务标题").value, "")
        project = pm_registry.read_registry(self.registry)["projects"][0]
        self.assertEqual([task["title"] for task in project["tasks"]], ["Original", "New task"])
        self.assertNotIn("files", project)

    def test_revoked_decision_blocks_stale_form_and_preserves_draft(self):
        self.click("改")
        self.assertFalse(self.app.exception)
        base = pm_registry.read_registry(self.registry)
        edited = pm_registry.read_registry(self.registry)
        edited["projects"][0]["decisions"][0]["status"] = "revoked"
        pm_registry.save_registry(base, edited, "external", path=self.registry)
        self.text("结论内容").set_value("Decision draft")
        # The task and decision each have a save button.
        next(item for item in self.app.button
             if item.label == "保存" and "deditform" in str(item.key)).click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertEqual(self.text("结论内容").value, "Decision draft")
        decision = pm_registry.read_registry(self.registry)["projects"][0]["decisions"][0]
        self.assertEqual(decision["status"], "revoked")
        self.assertEqual(decision["text"], "Original decision")

    def test_deleted_task_keeps_draft_and_cannot_be_recreated(self):
        base = pm_registry.read_registry(self.registry)
        edited = pm_registry.read_registry(self.registry)
        edited["projects"][0]["tasks"] = []
        pm_registry.save_registry(base, edited, "external", path=self.registry)
        self.text("标题").set_value("Task draft")
        self.click("保存")
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertEqual(self.text("标题").value, "Task draft")
        self.assertEqual(pm_registry.read_registry(self.registry)["projects"][0]["tasks"], [])

    def test_deleted_project_keeps_draft_and_cannot_be_recreated(self):
        base = pm_registry.read_registry(self.registry)
        edited = pm_registry.read_registry(self.registry)
        edited["projects"] = []
        pm_registry.save_registry(base, edited, "external", path=self.registry)
        self.text("标题").set_value("Project task draft")
        self.click("保存")
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertEqual(self.text("标题").value, "Project task draft")
        self.assertEqual(pm_registry.read_registry(self.registry)["projects"], [])


    def test_generate_handoff_pack_writes_into_fixture(self):
        """看板的「生成交接包」必须只写临时目录，且生成完整包结构。"""
        real = ROOT / ".pmhub" / "handoffs"
        before = sorted(p.name for p in real.iterdir()) if real.is_dir() else []
        self.click("生成交接包")
        self.assertFalse(self.app.exception)
        packs = sorted((self.root / ".pmhub" / "handoffs").glob("H-*"))
        self.assertEqual(len(packs), 1, "应生成且只生成一个交接包")
        for name in ("TASK.md", "CONTEXT.md", "MANIFEST.json", "HANDOFF.md"):
            self.assertTrue((packs[0] / name).exists(), name)
        after = sorted(p.name for p in real.iterdir()) if real.is_dir() else []
        self.assertEqual(before, after, "不得写入正式 .pmhub/handoffs")

        manifest = json.loads((packs[0] / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["project_id"], "demo")
        self.assertEqual(manifest["task_id"], "t1")
        self.assertFalse(manifest["program_id"])   # 独立小项目没有 L1 父级


if __name__ == "__main__":
    unittest.main()
