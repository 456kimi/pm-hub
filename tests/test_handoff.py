# -*- coding: utf-8 -*-
"""交接包（pm_handoff）的行为测试：生成结构、授权范围、结果校验。

这些测试只碰临时目录，不读写正式台账、不联网、不调用任何模型。
"""
import json
import tempfile
import unittest
from pathlib import Path

import pm_handoff as H

ROOT = Path(__file__).resolve().parents[1]


def make_program():
    return {
        "id": "prog-demo",
        "name": "示例超大项目",
        "kind": "program",
        "description": "L1 说明",
        "decisions": [
            {"id": "d1", "date": "2026-01-01", "text": "L1 现行口径", "status": "active"},
            {"id": "d2", "date": "2026-01-02", "text": "L1 已推翻口径", "status": "revoked"},
        ],
    }


def make_project(parent="prog-demo"):
    return {
        "id": "demo-proj",
        "name": "示例小项目",
        "kind": "project",
        "parent": parent,
        "stage": "开发中",
        "description": "L2 说明",
        "paths": {"root": str(ROOT)},
        "data_deps": ["本地 parquet"],
        "goals": [{"id": "g1", "text": "目标一", "done": False}],
        "decisions": [
            {"id": "d1", "date": "2026-02-01", "text": "本项目现行口径", "status": "active"},
            {"id": "d2", "date": "2026-02-02", "text": "本项目已推翻口径",
             "status": "revoked", "revoked_on": "2026-02-03"},
        ],
        "tasks": [{
            "id": "t1", "title": "修一个 bug", "detail": "细节",
            "acceptance": "测试全绿", "inputs": "", "outputs": "",
            "batch": "B1", "status": "todo",
        }],
    }


class HandoffExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmhub-handoff-", dir=ROOT / "tests")
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.prog = make_program()
        self.proj = make_project()

    def export(self, prog=None, proj=None):
        return H.export_pack(proj or self.proj, (proj or self.proj)["tasks"][0],
                             prog if prog is not None else self.prog,
                             out_root=self.out, operator="test")

    def test_pack_has_all_files(self):
        info = self.export()
        pack = Path(info["pack_dir"])
        self.assertTrue(pack.is_dir())
        for name in ("TASK.md", "CONTEXT.md", "MANIFEST.json",
                     "EVIDENCE.template.json", "HANDOFF.md"):
            self.assertTrue((pack / name).exists(), name)
        self.assertEqual(info["handoff_id"], pack.name)

    def test_manifest_carries_ids_and_scope(self):
        info = self.export()
        m = json.loads((Path(info["pack_dir"]) / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(m["task_id"], "t1")
        self.assertEqual(m["project_id"], "demo-proj")
        self.assertEqual(m["program_id"], "prog-demo")
        self.assertEqual(m["schema_version"], H.SCHEMA_VERSION)
        self.assertTrue(m["allowed_roots"])
        self.assertIn(str(ROOT), m["allowed_roots"])
        self.assertTrue(any("registry.json" in x for x in m["forbidden"]))

    def test_task_md_only_carries_active_decisions(self):
        info = self.export()
        text = (Path(info["pack_dir"]) / "TASK.md").read_text(encoding="utf-8")
        self.assertIn("本项目现行口径", text)
        self.assertIn("L1 现行口径", text)          # 父 L1 的 active 结论必须带上
        self.assertNotIn("已推翻口径", text)         # revoked 一律不得出现
        self.assertIn("测试全绿", text)              # 验收标准

    def test_context_md_has_goals_and_decisions(self):
        info = self.export()
        ctx = (Path(info["pack_dir"]) / "CONTEXT.md").read_text(encoding="utf-8")
        self.assertIn("目标一", ctx)
        self.assertIn("本项目现行口径", ctx)
        self.assertNotIn("本项目已推翻口径", ctx)
        self.assertIn("非目标", ctx)

    def test_repeated_export_does_not_overwrite(self):
        a = self.export()
        b = self.export()
        self.assertNotEqual(a["handoff_id"], b["handoff_id"])
        self.assertTrue(Path(a["pack_dir"]).is_dir())
        self.assertTrue(Path(b["pack_dir"]).is_dir())
        self.assertTrue(b["handoff_id"].startswith(a["handoff_id"]))

    def test_export_leaves_registry_untouched(self):
        before = (ROOT / "registry.json").stat().st_mtime_ns
        self.export()
        after = (ROOT / "registry.json").stat().st_mtime_ns
        self.assertEqual(before, after)


class HandoffValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmhub-validate-", dir=ROOT / "tests")
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.proj = make_project()
        info = H.export_pack(self.proj, self.proj["tasks"][0], make_program(),
                             out_root=self.out, operator="test")
        self.pack = Path(info["pack_dir"])
        self.manifest = json.loads((self.pack / "MANIFEST.json").read_text(encoding="utf-8"))

    def evidence(self, **kw):
        ev = {
            "schema_version": H.SCHEMA_VERSION,
            "handoff_id": self.manifest["handoff_id"],
            "task_id": self.manifest["task_id"],
            "status": "ready_for_review",
            "agent_app": "WorkBuddy",
            "model": "some-model",
            "files_changed": [str(ROOT / "pm_handoff.py")],
            "tests": [{"command": "python -m unittest", "outcome": "passed",
                       "notes": "Ran 27 tests OK"}],
            "unresolved": [],
            "requires_approval": False,
        }
        ev.update(kw)
        return ev

    def write(self, ev, result="改了 pm_handoff.py 的校验逻辑，动了看板按钮，"
                                "测试实跑 27 个全绿，没有遗留问题。"):
        (self.pack / "RESULT.md").write_text(result, encoding="utf-8")
        (self.pack / "EVIDENCE.json").write_text(
            json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
        return H.validate_pack(self.pack)

    def test_missing_result_files_blocks(self):
        rep = H.validate_pack(self.pack)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("RESULT.md" in x for x in rep["issues"]))
        self.assertTrue(any("EVIDENCE.json" in x for x in rep["issues"]))

    def test_clean_result_passes(self):
        rep = self.write(self.evidence())
        self.assertTrue(rep["ok"], rep["issues"])
        self.assertEqual(rep["warnings"], [])

    def test_out_of_scope_change_blocks(self):
        rep = self.write(self.evidence(files_changed=["G:\\other\\thing.py"]))
        self.assertFalse(rep["ok"])
        self.assertTrue(any("超出授权范围" in x for x in rep["issues"]))

    def test_touching_registry_blocks(self):
        rep = self.write(self.evidence(
            files_changed=[str(ROOT / "registry.json")]))
        self.assertFalse(rep["ok"])
        self.assertTrue(any("正式台账" in x for x in rep["issues"]))

    def test_task_id_mismatch_blocks(self):
        rep = self.write(self.evidence(task_id="t999"))
        self.assertFalse(rep["ok"])
        self.assertTrue(any("task_id 不匹配" in x for x in rep["issues"]))

    def test_handoff_id_mismatch_blocks(self):
        rep = self.write(self.evidence(handoff_id="H-other"))
        self.assertFalse(rep["ok"])
        self.assertTrue(any("handoff_id 不匹配" in x for x in rep["issues"]))

    def test_bad_status_blocks(self):
        rep = self.write(self.evidence(status="done"))
        self.assertFalse(rep["ok"])
        self.assertTrue(any("status 非法" in x for x in rep["issues"]))

    def test_self_claimed_pass_without_notes_warns(self):
        rep = self.write(self.evidence(
            tests=[{"command": "pytest", "outcome": "passed", "notes": ""}]))
        self.assertTrue(rep["ok"])
        self.assertTrue(any("不采信自称" in x for x in rep["warnings"]))

    def test_admitted_not_run_is_acceptable(self):
        rep = self.write(self.evidence(
            tests=[{"command": "", "outcome": "未运行", "notes": "环境缺依赖"}]))
        self.assertTrue(rep["ok"])
        self.assertFalse(any("缺少 command" in x for x in rep["warnings"]))

    def test_requires_approval_warns(self):
        rep = self.write(self.evidence(requires_approval=True))
        self.assertTrue(any("需要审批" in x for x in rep["warnings"]))

    def test_relative_path_resolves_against_project_root(self):
        rep = self.write(self.evidence(files_changed=["pm_handoff.py"]))
        self.assertTrue(rep["ok"], rep["issues"])

    def test_empty_model_warns(self):
        rep = self.write(self.evidence(model=""))
        self.assertTrue(any("model 为空" in x for x in rep["warnings"]))

    def test_import_writes_validation_report(self):
        self.write(self.evidence())
        rep = H.import_result(self.pack)
        self.assertTrue(rep["ok"])
        report = self.pack / "VALIDATION.json"
        self.assertTrue(report.exists())
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(data["ok"])
        self.assertIn("validated_at", data)

    def test_short_result_blocks(self):
        rep = self.write(self.evidence(), result="好了")
        self.assertFalse(rep["ok"])
        self.assertTrue(any("RESULT.md 内容过短" in x for x in rep["issues"]))


class HandoffHelpersTests(unittest.TestCase):
    def test_is_within_handles_case_and_separators(self):
        self.assertTrue(H.is_within("H:\\Github\\pm-hub\\a.py", ["h:/github/pm-hub"]))
        self.assertFalse(H.is_within("H:\\github\\pm-hubX\\a.py", ["H:\\github\\pm-hub"]))

    def test_extract_paths_dedupes(self):
        text = r"读 H:\a\b.csv 和 H:\a\b.csv 以及 G:\c"
        self.assertEqual(H.extract_paths(text), ["H:\\a\\b.csv", "G:\\c"])

    def test_active_decisions_defaults_to_active(self):
        obj = {"decisions": [{"text": "no status"}, {"text": "revoked", "status": "revoked"}]}
        self.assertEqual([d["text"] for d in H.active_decisions(obj)], ["no status"])

    def test_list_packs_reports_state(self):
        tmp = tempfile.TemporaryDirectory(prefix="pmhub-list-", dir=ROOT / "tests")
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        proj = make_project()
        info = H.export_pack(proj, proj["tasks"][0], make_program(),
                             out_root=out, operator="test")
        packs = H.list_packs(out)
        self.assertEqual(len(packs), 1)
        self.assertFalse(packs[0]["has_result"])
        (Path(info["pack_dir"]) / "RESULT.md").write_text("x", encoding="utf-8")
        self.assertTrue(H.list_packs(out)[0]["has_result"])


if __name__ == "__main__":
    unittest.main()
