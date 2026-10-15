import json
import unittest

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-070/card-source"


class CardSourceTests(unittest.TestCase):
    def test_official_fixed_card_source(self):
        self.assertEqual(verify_artifacts(SOURCE, expected_types={"Card"}), [])
        component = json.loads((SOURCE / "component_ir.json").read_text(encoding="utf-8"))["components"][0]
        self.assertEqual(component["logicalComponentId"], "content.card.default.user-info")
        self.assertEqual(component["rootBounds"], {"width": 240, "height": 106})
        self.assertEqual(component["props"], {"title": "用户信息", "bordered": True,
                                             "disHover": True, "shadow": False, "padding": 16})
        observation = json.loads((SOURCE / "card-observation.json").read_text(encoding="utf-8"))
        self.assertEqual(observation["metrics"]["classes"],
                         ["ivu-card", "ivu-card-bordered", "ivu-card-dis-hover"])
        self.assertEqual(observation["metrics"]["titleText"], "用户信息")
        self.assertEqual(observation["metrics"]["bodyText"], "暂无内容")
        self.assertEqual(observation["metrics"]["rootStyle"]["border"],
                         "1px solid rgb(232, 234, 236)")
        with Image.open(SOURCE / "content.card.default.user-info.png") as screenshot:
            self.assertEqual(screenshot.size, (240, 106))


if __name__ == "__main__":
    unittest.main()
