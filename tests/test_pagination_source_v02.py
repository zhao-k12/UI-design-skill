import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-073/pagination-source"


class PaginationSourceTests(unittest.TestCase):
    def test_official_three_page_static_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Pagination"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "data.pagination.default.three-pages")
        self.assertEqual(component["rootBounds"], {"width": 400, "height": 32})
        self.assertEqual(component["props"]["total"], 30)
        self.assertEqual(component["props"]["pageSize"], 10)
        self.assertEqual(component["props"]["modelValue"], 1)
        observation = json.loads((SOURCE / "pagination-observation.json").read_text(encoding="utf-8"))
        items = observation["metrics"]["items"]
        self.assertEqual(len(items), 5)
        self.assertEqual([item["bounds"]["width"] for item in items], [32] * 5)
        self.assertEqual([item["text"] for item in items], ["", "1", "2", "3", ""])
        self.assertIn("ivu-page-disabled", items[0]["classes"])
        self.assertIn("ivu-page-item-active", items[1]["classes"])
        self.assertEqual(items[0]["icon"], "ivu-icon ivu-icon-ios-arrow-back")
        self.assertEqual(items[-1]["icon"], "ivu-icon ivu-icon-ios-arrow-forward")
        with Image.open(SOURCE / "data.pagination.default.three-pages.png") as image:
            self.assertEqual(image.size, (400, 32))


if __name__ == "__main__":
    unittest.main()
