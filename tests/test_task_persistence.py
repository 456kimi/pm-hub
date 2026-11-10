"""Exercise task forms using synthetic data; the real registry is never opened."""
import ast
import copy
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import MagicMock


class Rerun(Exception):
    pass


def load_task_functions():
    source = (Path(__file__).resolve().parents[1] / "dashboard.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {"norm_tasks", "next_tid", "task_stats", "render_task_block",
             "fresh_form_key", "reset_form_after_save"}
    module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
                        type_ignores=[])
    env = {"datetime": datetime, "TASK_STATUS_CN": {s: s for s in ("todo", "doing", "done", "blocked")},
           "TASK_STATUS_ORDER": ("todo", "doing", "done", "blocked"),
           "TASK_STATUS_COLOR": {s: "#000" for s in ("todo", "doing", "done", "blocked")}}
    exec(compile(module, "dashboard.py", "exec"), env)
    return env


class TaskPersistenceTest(unittest.TestCase):
    def submit(self, bulk):
        env = load_task_functions()
        st = MagicMock()
        st.session_state = {}
        st.radio.return_value = "未完成"
        col = MagicMock()
        col.text_input.side_effect = lambda label, **kw: {"任务标题": "新增任务", "批次（可空）": "B1"}.get(label, "")
        st.columns.side_effect = lambda spec: [col] * (spec if isinstance(spec, int) else len(spec))
        st.text_area.side_effect = lambda label, **kw: ("任务A | 说明 | 验收 | B1\n任务B | 说明 | 验收 | B2"
                                                        if label.startswith("批量粘贴") else "")
        st.text_input.return_value = "验收"
        st.form_submit_button.side_effect = lambda label, **kw: label == ("批量添加" if bulk else "添加任务")
        st.rerun.side_effect = Rerun
        saved = []
        p = {"id": "project", "tasks": [{"id": "t3", "title": "旧任务", "status": "done"}]}
        reg = {"projects": [p]}
        env.update(st=st, reg=reg, recompute_progress=lambda p: None, touch=lambda p: None,
                   save_reg=lambda data, operator: saved.append(copy.deepcopy(data)))
        with self.assertRaises(Rerun):
            env["render_task_block"](None, p)
        return saved[0]["projects"][0]["tasks"]

    def test_single_add_is_saved_to_project(self):
        tasks = self.submit(False)
        self.assertEqual([(t["id"], t["title"]) for t in tasks], [("t3", "旧任务"), ("t4", "新增任务")])

    def test_bulk_add_is_saved_with_distinct_ids(self):
        tasks = self.submit(True)
        self.assertEqual([(t["id"], t["title"]) for t in tasks],
                         [("t3", "旧任务"), ("t4", "任务A"), ("t5", "任务B")])


if __name__ == "__main__":
    unittest.main()
