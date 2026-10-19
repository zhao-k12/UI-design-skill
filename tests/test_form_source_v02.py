import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-085/form-source"


class FormSourceTests(unittest.TestCase):
    def test_official_single_name_field_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Form"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "form.single.name.empty")
        self.assertEqual(component["rootBounds"], {"width": 320, "height": 34})
        observation = json.loads((SOURCE / "form-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["label"]["text"], "姓名")
        self.assertEqual(metrics["label"]["bounds"]["width"], 80)
        self.assertEqual(metrics["input"]["placeholder"], "请输入姓名")
        self.assertEqual(metrics["input"]["bounds"]["width"], 240)
        with Image.open(SOURCE / "form.single.name.empty.png") as image:
            self.assertEqual(image.size, (320, 34))


if __name__ == "__main__":
    unittest.main()
