import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-091/drawer-source"


class DrawerSourceTests(unittest.TestCase):
    def test_official_open_detail_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Drawer"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "overlay.drawer.detail.open")
        self.assertEqual(component["rootBounds"], {"width": 320, "height": 500})
        observation = json.loads((SOURCE / "drawer-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["header"]["text"], "详情")
        self.assertEqual(metrics["body"]["text"], "抽屉内容")
        self.assertEqual(metrics["header"]["bounds"]["height"], 51)
        self.assertEqual(metrics["body"]["bounds"]["height"], 449)
        self.assertEqual(metrics["closeCount"], 0)
        self.assertEqual(metrics["maskCount"], 1)
        self.assertEqual(metrics["content"]["style"]["backgroundColor"], "rgb(255, 255, 255)")
        with Image.open(SOURCE / "overlay.drawer.detail.open.png") as image:
            self.assertEqual(image.size, (320, 500))


if __name__ == "__main__":
    unittest.main()
