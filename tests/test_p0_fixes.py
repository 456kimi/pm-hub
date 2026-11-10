"""P0-03 修复项的回归测试（2026-11-10）。

覆盖：
  1. 应用扫描 id 唯一性（截断冲突 / 已有 id 占用）
  2. AI/网络代拟描述不得标成用户已确认
  3. 无验收标准的任务不得生成交接包
  4. 新建任务缺验收标准被拒绝
  5. 卡片 HTML 对台账文本做转义
  6. dashboard 不写死本机绝对路径
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bulk_describe
import export_static
import pm_handoff
import pm_registry
import scanner

ROOT = Path(__file__).resolve().parents[1]


class ScannerUniqueIdTests(unittest.TestCase):
    def test_truncated_ids_get_unique_suffix(self):
        base = "microsoft.net.workload.mono.toolchain.ne"
        existing = [{"id": base, "name": "Workload A"}]
        new = [{"id": base, "name": "Workload B"}, {"id": base, "name": "Workload C"}]
        scanner.assign_unique_ids(existing, new)
        self.assertEqual([a["id"] for a in new], [base + "-2", base + "-3"])
        self.assertEqual(len({a["id"] for a in existing + new}), 3)

    def test_existing_ids_are_preserved(self):
        existing = [{"id": "keep", "name": "A"}]
        new = [{"id": "other", "name": "B"}]
        scanner.assign_unique_ids(existing, new)
        self.assertEqual(existing[0]["id"], "keep")
        self.assertEqual(new[0]["id"], "other")

    def test_empty_id_falls_back_to_name(self):
        new = [{"id": "", "name": "Some App"}]
        scanner.assign_unique_ids([], new)
        self.assertEqual(new[0]["id"], scanner.norm("Some App"))


class WebCacheConfirmTests(unittest.TestCase):
    def test_web_description_stays_unconfirmed(self):
        app = {"id": "a", "name": "A"}
        bulk_describe.apply_web_cache(app, {"purpose": "某工具（具体待确认）", "category": "dev"})
        self.assertIs(app["desc_confirmed"], False)
        self.assertEqual(app["auto_source"], "web")
        self.assertEqual(app["purpose"], "某工具（具体待确认）")


class HandoffAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmhub-p0-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_missing_acceptance_is_refused(self):
        with self.assertRaises(ValueError):
            pm_handoff.export_pack({"id": "p", "name": "P"},
                                   {"id": "T-1", "title": "无验收"},
                                   None, out_root=self.root)

    def test_acceptance_present_generates_full_pack(self):
        info = pm_handoff.export_pack(
            {"id": "p", "name": "P", "paths": {"root": str(self.root)}},
            {"id": "T-1", "title": "有验收", "acceptance": "tests 全绿"},
            None, out_root=self.root)
        pack = Path(info["pack_dir"])
        for name in ("TASK.md", "CONTEXT.md", "MANIFEST.json", "HANDOFF.md"):
            self.assertTrue((pack / name).exists(), name)
        manifest = json.loads((pack / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["acceptance"], "tests 全绿")
        self.assertTrue(any("dev_logs" in one for one in manifest["forbidden"]))


class DashboardP0Tests(unittest.TestCase):
    """AppTest：缺验收任务被拒 + 卡片文本转义。"""

    def setUp(self):
        main_module = sys.modules["__main__"]
        main_file = getattr(main_module, "__file__", None)
        argv = sys.argv[:]

        def restore():
            sys.modules["__main__"] = main_module
            if main_file is None:
                main_module.__dict__.pop("__file__", None)
            else:
                main_module.__file__ = main_file
            sys.argv[:] = argv

        self.addCleanup(restore)
        self.tmp = tempfile.TemporaryDirectory(prefix="pmhub-p0-ui-", dir=ROOT / "tests")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for obj, attr in ((export_static, "HUB"), (pm_handoff, "ROOT")):
            p = patch.object(obj, attr, self.root)
            p.start()
            self.addCleanup(p.stop)
        for name in ("dashboard.py", "theme.py", "pm_progress.py", "pm_registry.py",
                     "pm_handoff.py", "export_static.py"):
            shutil.copy2(ROOT / name, self.root / name)
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps({
            "projects": [{
                "id": "demo", "name": "<b>Example</b>", "kind": "project",
                "status": "active", "parent": None, "paths": {"root": ""},
                "tasks": [{"id": "t1", "title": "Original", "status": "todo",
                           "acceptance": "可打开"}],
                "decisions": [],
            }],
            "apps": [], "locations": [],
        }, ensure_ascii=False), encoding="utf-8")
        from streamlit.testing.v1 import AppTest
        self.app = AppTest.from_file(str(self.root / "dashboard.py"), default_timeout=60)
        self.app.session_state["nav"] = "🔍 项目详情"
        self.app.session_state["current_pid"] = "demo"
        self.app.run()

    def label(self, label):
        return next(x for x in self.app.text_input if x.label == label)

    def test_task_without_acceptance_is_rejected(self):
        before = len(pm_registry.read_registry(self.registry)["projects"][0]["tasks"])
        self.label("任务标题").set_value("没有验收的任务")
        next(x for x in self.app.button if x.label == "添加任务").click().run()
        after = pm_registry.read_registry(self.registry)["projects"][0]["tasks"]
        self.assertEqual(len(after), before, "缺验收标准的任务不应入库")
        self.assertTrue(self.app.warning, "应给出验收标准必填提示")

    def test_card_escapes_registry_text(self):
        self.app.session_state["nav"] = "📊 项目总览"
        self.app.run()
        rendered = "\n".join(m.value for m in self.app.markdown if isinstance(m.value, str))
        self.assertIn("&lt;b&gt;", rendered, "台账文本必须转义后再拼 HTML")


class PathHygieneTests(unittest.TestCase):
    def test_dashboard_has_no_hardcoded_project_path(self):
        src = (ROOT / "dashboard.py").read_text(encoding="utf-8")
        self.assertNotIn(r'H:\github\pm-hub', src)
        self.assertIn("DEVLOGS_DIR = str(HUB / \"devlogs\")", src)


if __name__ == "__main__":
    unittest.main()
