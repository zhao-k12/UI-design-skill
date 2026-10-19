import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-082/datepicker-source"


class DatePickerSourceTests(unittest.TestCase):
    def test_official_selected_date_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"DatePicker"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "form.datepicker.date.selected")
        self.assertEqual(component["rootBounds"], {"width": 211, "height": 32})
        observation = json.loads((SOURCE / "datepicker-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["input"]["value"], "2024-01-01")
        self.assertEqual(metrics["input"]["style"]["borderRadius"], "4px")
        self.assertEqual(metrics["icon"]["classes"],
                         ["ivu-icon", "ivu-icon-ios-calendar-outline"])
        with Image.open(SOURCE / "form.datepicker.date.selected.png") as image:
            self.assertEqual(image.size, (211, 32))


if __name__ == "__main__":
    unittest.main()
