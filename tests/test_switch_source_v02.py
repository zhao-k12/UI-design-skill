import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-067/switch-source"


class SwitchSourceTests(unittest.TestCase):
    def test_locked_official_runtime_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Switch"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "form.switch.default.enabled")
        self.assertEqual(component["rootBounds"], {"width": 44, "height": 22})
        self.assertEqual(component["content"]["text"], "开")
        self.assertEqual(component["props"], {"modelValue": True, "trueValue": True,
                                              "falseValue": False, "disabled": False,
                                              "size": "default", "loading": False})
        observation = json.loads((SOURCE / "switch-observation.json").read_text(encoding="utf-8"))
        self.assertEqual(observation["metrics"]["classes"],
                         ["ivu-switch", "ivu-switch-checked", "ivu-switch-default"])
        self.assertEqual(observation["metrics"]["knobStyle"]["width"], "18px")
        self.assertEqual(observation["fonts"][0]["familyName"], "PingFang SC")

    def test_fractional_capture_has_only_extra_blank_bottom_row(self):
        with Image.open(SOURCE / "form.switch.default.enabled.png") as screenshot:
            image = screenshot.convert("RGB")
        self.assertEqual(image.size, (44, 23))
        self.assertTrue(all(image.getpixel((x, 22)) == (255, 255, 255) for x in range(44)))


if __name__ == "__main__":
    unittest.main()
