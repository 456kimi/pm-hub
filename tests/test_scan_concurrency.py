"""Exercise scan commits against concurrently modified synthetic registries."""
import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import scanner
import bulk_describe


class ScanConcurrencyTests(unittest.TestCase):
    def test_scanner_rechecks_empty_paths_and_deduplicates_unchanged_groups(self):
        baseline = {
            "projects": [{"id": "p1", "paths": {"root": ""}},
                         {"id": "p2", "paths": {"root": ""}}],
            "apps": [{"id": "a1", "name": "A", "path": "", "purpose": ""},
                     {"id": "a2", "name": "A", "path": "", "purpose": ""},
                     {"id": "a1", "name": "B", "path": "", "purpose": ""},
                     {"id": "b2", "name": "B", "path": "", "purpose": "from duplicate"}],
            "locations": [],
        }
        candidates = [{"path": "H:\\p1", "name": "p1", "mtime": 0, "prints": []},
                      {"path": "H:\\p2", "name": "p2", "mtime": 0, "prints": []}]
        latest = copy.deepcopy(baseline)
        latest["projects"][0]["paths"]["root"] = "H:\\user-choice"
        latest["apps"][0]["purpose"] = "user edit"

        def save(operator, mutate, **kwargs):
            mutate(latest)
            return SimpleNamespace(data=latest, export_error=None)

        def scan_apps(reg):
            scanner.dedupe_apps(reg)
            reg["apps"][0]["path"] = "H:\\for-a"
            reg["apps"][1]["path"] = "H:\\for-b"
            reg["apps"].append({"id": "c1", "name": "C", "path": "H:\\c", "exe": "", "category": "tool"})
            return [reg["apps"][-1]], []

        with patch.object(scanner, "read_registry", return_value=copy.deepcopy(baseline)), \
             patch.object(scanner, "scan_projects", return_value=(candidates, 2, [])), \
             patch.object(scanner, "top_level_dirs", return_value=[]), \
             patch.object(scanner, "merge_apps", side_effect=scan_apps), \
             patch.object(scanner, "apply_registry", side_effect=save), \
             patch.object(Path, "mkdir"), patch.object(Path, "write_text"):
            scanner.main()

        self.assertEqual(latest["projects"][0]["paths"]["root"], "H:\\user-choice")
        self.assertEqual(latest["projects"][1]["paths"]["root"], "H:\\p2")
        self.assertEqual([a["id"] for a in latest["apps"]], ["a1", "a2", "a1", "c1"])
        self.assertEqual(latest["apps"][0]["purpose"], "user edit")
        self.assertEqual(latest["apps"][2]["purpose"], "from duplicate")
        self.assertEqual(latest["apps"][0]["path"], "H:\\for-a")
        self.assertEqual(latest["apps"][2]["path"], "H:\\for-b")

    def test_description_rechecks_concurrent_manual_change(self):
        baseline = {"apps": [{"id": "a", "name": "App A", "source": "registry", "purpose": ""},
                             {"id": "a", "name": "App B", "source": "registry", "purpose": ""}]}
        latest = copy.deepcopy(baseline)
        latest["apps"][0]["purpose"] = "manual"

        def save(operator, mutate, **kwargs):
            mutate(latest)
            return SimpleNamespace(data=latest, export_error="offline export failed")

        with patch.object(bulk_describe, "read_registry", return_value=copy.deepcopy(baseline)), \
             patch.object(bulk_describe, "classify", return_value=("automatic", "tool")), \
             patch.object(bulk_describe, "apply_registry", side_effect=save), \
             patch.object(Path, "exists", return_value=False), patch.object(Path, "write_text"):
            bulk_describe.main()
        self.assertEqual(latest["apps"][0]["purpose"], "manual")
        self.assertEqual(latest["apps"][1]["purpose"], "automatic")


if __name__ == "__main__":
    unittest.main()
