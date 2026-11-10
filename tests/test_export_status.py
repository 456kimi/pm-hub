# -*- coding: utf-8 -*-
"""公开状态导出（export_status）的边界测试。

重点盯两件会害人的事：
  1. 已推翻（revoked）的决策绝不能出现在公开文件里 —— 否则协作者按作废口径干活
  2. 进度必须走统一口径 —— 台账里 L1 存的 progress 常年是 0，直接用会导出假数据
"""
import unittest

import export_status as E
import pm_progress

ACTIVE = {"id": "d1", "date": "2026-01-01", "text": "这是现行口径", "status": "active"}
REVOKED = {"id": "d2", "date": "2026-01-02", "text": "这是已推翻口径",
           "status": "revoked", "revoked_on": "2026-01-03"}
NO_STATUS = {"id": "d3", "date": "2026-01-03", "text": "老数据没有 status"}


class DecisionFilterTests(unittest.TestCase):
    def test_active_decisions_filters_revoked(self):
        obj = {"decisions": [ACTIVE, REVOKED, NO_STATUS]}
        got = [d["id"] for d in E.active_decisions(obj)]
        self.assertEqual(got, ["d1", "d3"])

    def test_active_decisions_tolerates_missing_field(self):
        self.assertEqual(E.active_decisions({}), [])
        self.assertEqual(E.active_decisions(None), [])

    def test_program_render_excludes_revoked(self):
        prog = {"name": "L1", "decisions": [ACTIVE, REVOKED]}
        text = "\n".join(E.render_program(prog, []))
        self.assertIn("这是现行口径", text)
        self.assertNotIn("这是已推翻口径", text)
        self.assertIn("现行决策", text)
        self.assertNotIn("已定决策", text)

    def test_sub_render_excludes_revoked(self):
        proj = {"id": "p1", "name": "L2", "decisions": [ACTIVE, REVOKED]}
        text = "\n".join(E.render_sub(proj))
        self.assertIn("这是现行口径", text)
        self.assertNotIn("这是已推翻口径", text)


class ScrubTests(unittest.TestCase):
    def test_drive_paths_are_masked(self):
        self.assertNotIn("Users", E.scrub(r"见 C:\Users\Administrator\x.txt"))

    def test_prefixed_keys_are_masked(self):
        for raw in ("sk-proj-abcdefghijklmnop1234",
                    "ghp_1234567890abcdefghijklmnopqrstuvwx",
                    "github_pat_abcdefghijklmnopqrstuvwxyz"):
            self.assertNotIn(raw, E.scrub("key=" + raw))

    def test_assignment_style_token_is_masked(self):
        raw = "b941f43f0f4e2b1a4c3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f"
        out = E.scrub('TUSHARE_TOKEN = "%s"' % raw)
        self.assertNotIn(raw, out)
        self.assertIn("TUSHARE_TOKEN", out)   # 字段名保留，便于人看懂被抹了什么

    def test_bare_long_hex_is_masked(self):
        self.assertNotIn("a" * 40, E.scrub("值 " + "a" * 40))

    def test_phone_is_masked(self):
        self.assertNotIn("13812345678", E.scrub("联系 13812345678"))

    def test_normal_numbers_untouched(self):
        text = "回测区间 20240101 至 20250630，收益 +12.3%"
        self.assertEqual(E.scrub(text), text)

    def test_short_commit_hash_untouched(self):
        text = "commit 6609a0b 新增索引"
        self.assertEqual(E.scrub(text), text)

    def test_scrub_handles_containers(self):
        self.assertEqual(E.scrub(["a", None, ""]), "a")
        self.assertIn("k=", E.scrub({"k": "v"}))


class ProgressConsistencyTests(unittest.TestCase):
    """L1 必须走汇总，L2 走任务/目标，两处都不能读台账里的旧 progress 字段。"""

    def test_program_rollup_ignores_stale_stored_progress(self):
        prog = {"id": "L1", "name": "大项目", "progress": 0}
        kids = [
            {"id": "a", "parent": "L1", "tasks": [
                {"id": "t1", "status": "done"}, {"id": "t2", "status": "todo"}]},
            {"id": "b", "parent": "L1", "tasks": [
                {"id": "t1", "status": "done"}]},
        ]
        roll = pm_progress.program_rollup(kids + [prog], prog)
        self.assertEqual(roll["progress"], 67)      # 2/3，而不是台账里的 0
        self.assertEqual(roll["n_tasks"], 3)

    def test_program_rollup_falls_back_to_child_average(self):
        prog = {"id": "L1", "progress": 0}
        kids = [{"id": "a", "parent": "L1", "progress": 80},
                {"id": "b", "parent": "L1", "progress": 40}]
        roll = pm_progress.program_rollup(kids + [prog], prog)
        self.assertEqual(roll["progress"], 60)

    def test_render_program_uses_rollup(self):
        prog = {"name": "大项目", "progress": 0, "status": "active"}
        kids = [{"id": "a", "name": "小项目", "parent": "大项目", "status": "active",
                 "tasks": [{"id": "t1", "status": "done"}]}]
        prog["id"] = "大项目"
        text = "\n".join(E.render_program(prog, kids))
        self.assertIn("100%", text)
        self.assertIn("按子项目任务", text)

    def test_render_sub_uses_task_ratio(self):
        proj = {"id": "p", "name": "小项目", "status": "active", "progress": 5,
                "tasks": [{"id": "t1", "status": "done", "title": "a"},
                          {"id": "t2", "status": "todo", "title": "b"}]}
        text = "\n".join(E.render_sub(proj))
        self.assertIn("50%", text)
        self.assertIn("任务完成 1/2", text)


if __name__ == "__main__":
    unittest.main()
