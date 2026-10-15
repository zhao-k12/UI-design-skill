import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-076/tabs-source"


class TabsSourceTests(unittest.TestCase):
    def test_official_two_tab_static_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Tabs"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "navigation.tabs.line.overview")
        self.assertEqual(component["rootBounds"], {"width": 320, "height": 73})
        self.assertEqual(component["props"]["modelValue"], "overview")
        observation = json.loads((SOURCE / "tabs-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual([tab["text"] for tab in metrics["tabs"]], ["概览", "详情"])
        self.assertEqual(metrics["ink"]["bounds"], {"x": 24, "y": 58, "width": 60, "height": 2})
        self.assertEqual(metrics["panes"][0]["text"], "概览内容")
        self.assertEqual(metrics["panes"][1]["bounds"]["width"], 0)
        with Image.open(SOURCE / "navigation.tabs.line.overview.png") as image:
            self.assertEqual(image.size, (320, 73))


if __name__ == "__main__":
    unittest.main()
