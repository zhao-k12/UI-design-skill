import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-097/cascader-source"


class CascaderSourceTests(unittest.TestCase):
    def test_official_selected_region_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Cascader"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "form.cascader.region.selected")
        self.assertEqual(component["rootBounds"], {"width": 240, "height": 32})
        observation = json.loads((SOURCE / "cascader-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["input"]["value"], "浙江 / 杭州")
        self.assertEqual(metrics["input"]["placeholder"], "请选择地区")
        self.assertEqual(metrics["input"]["style"]["border"], "1px solid rgb(220, 222, 226)")
        self.assertEqual(metrics["arrow"]["bounds"]["width"], 14)
        self.assertEqual(metrics["visibleDropdownCount"], 0)
        with Image.open(SOURCE / "form.cascader.region.selected.png") as image:
            self.assertEqual(image.size, (240, 32))


if __name__ == "__main__":
    unittest.main()
