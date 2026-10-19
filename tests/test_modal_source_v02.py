import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-088/modal-source"


class ModalSourceTests(unittest.TestCase):
    def test_official_open_notice_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Modal"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "overlay.modal.notice.open")
        self.assertEqual(component["rootBounds"], {"width": 320, "height": 104})
        observation = json.loads((SOURCE / "modal-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["header"]["text"], "提示")
        self.assertEqual(metrics["body"]["text"], "操作已完成")
        self.assertEqual(metrics["header"]["bounds"]["height"], 51)
        self.assertEqual(metrics["body"]["bounds"]["height"], 53)
        self.assertEqual(metrics["footerCount"], 0)
        self.assertEqual(metrics["closeCount"], 0)
        with Image.open(SOURCE / "overlay.modal.notice.open.png") as image:
            self.assertEqual(image.size, (320, 104))


if __name__ == "__main__":
    unittest.main()
