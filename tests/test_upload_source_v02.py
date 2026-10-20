import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-094/upload-source"


class UploadSourceTests(unittest.TestCase):
    def test_official_empty_drag_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Upload"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "data.upload.drag.empty")
        self.assertEqual(component["rootBounds"], {"width": 320, "height": 82})
        observation = json.loads((SOURCE / "upload-observation.json").read_text(encoding="utf-8"))
        metrics = observation["metrics"]
        self.assertEqual(metrics["drag"]["style"]["border"], "1px dashed rgb(220, 222, 226)")
        self.assertEqual(metrics["drag"]["style"]["borderRadius"], "4px")
        self.assertEqual(metrics["content"]["text"], "上传文件")
        self.assertEqual(metrics["content"]["bounds"]["width"], 318)
        self.assertTrue(metrics["fileInputPresent"])
        self.assertEqual(metrics["uploadListCount"], 0)
        with Image.open(SOURCE / "data.upload.drag.empty.png") as image:
            self.assertEqual(image.size, (320, 82))


if __name__ == "__main__":
    unittest.main()
