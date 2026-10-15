import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-079/tree-source"


class TreeSourceTests(unittest.TestCase):
    def test_official_expanded_tree_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Tree"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "navigation.tree.expanded.departments")
        self.assertEqual(component["rootBounds"], {"width": 240, "height": 79})
        observation = json.loads((SOURCE / "tree-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual([title["text"] for title in metrics["titles"]],
                         ["部门", "研发部", "设计部"])
        self.assertEqual([title["bounds"]["y"] - metrics["root"]["y"]
                          for title in metrics["titles"]], [0, 29, 58])
        self.assertIn("ivu-tree-arrow-open", metrics["arrows"][0]["classes"])
        self.assertEqual(metrics["arrows"][0]["icon"], "ivu-icon ivu-icon-ios-arrow-forward")
        with Image.open(SOURCE / "navigation.tree.expanded.departments.png") as image:
            self.assertEqual(image.size, (240, 79))


if __name__ == "__main__":
    unittest.main()
