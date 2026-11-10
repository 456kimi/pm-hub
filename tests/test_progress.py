"""进度口径与静态汇总的隔离测试，不读取或写入真实台账。"""
import unittest

from export_static import card, program_block
from pm_progress import progress_info


class ProgressTests(unittest.TestCase):
    def test_tasks_take_precedence_without_mutating_cached_value(self):
        project = {"progress": None,
                   "tasks": [{"status": "done"}] * 7 + [{"status": "todo"}] * 3,
                   "goals": [{"done": True}] * 6 + [{"done": False}] * 2}
        self.assertEqual(progress_info(project), (70, "任务完成 7/10"))
        self.assertIsNone(project["progress"])

    def test_goals_used_when_tasks_empty(self):
        self.assertEqual(progress_info({"progress": 99, "tasks": [],
                                       "goals": [{"done": True}, {"done": False}]}),
                         (50, "目标完成 1/2"))

    def test_manual_and_missing_progress(self):
        self.assertEqual(progress_info({"progress": 0}), (0, "手动填写"))
        self.assertEqual(progress_info({}), (None, "未设定"))

    def test_static_card_uses_fresh_progress(self):
        project = {"name": "test", "progress": None,
                   "goals": [{"done": True}, {"done": False}]}
        markup = card(project)
        self.assertIn("50%", markup)
        self.assertIn("目标完成 1/2", markup)

    def test_static_l1_uses_task_counts_and_reports_coverage(self):
        children = [{"name": "one", "tasks": [{"status": "done"}, {"status": "todo"}]},
                    {"name": "two", "progress": 77}]
        markup = program_block({"name": "parent"}, children)
        self.assertIn("50%", markup)
        self.assertIn("按子项目任务 1/2 计算 · 1/2 个小项目有任务", markup)

    def test_static_l1_without_tasks_uses_fresh_child_average(self):
        children = [{"name": "one", "progress": 77},
                    {"name": "two", "goals": [{"done": True}]}]
        markup = program_block({"name": "parent"}, children)
        self.assertIn("88%", markup)
        self.assertIn("按 2/2 个有进度的小项目取均值", markup)


if __name__ == "__main__":
    unittest.main()
