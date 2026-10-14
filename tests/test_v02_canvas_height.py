"""V0.2.2 static canvas grows beyond its minimum without changing older snapshots."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import unittest

from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]
tokens = import_module("core.design-rules.tokens")
patterns = import_module("core.layout.patterns")
layout = import_module("core.layout.engine")


def registry(version):
    return tokens.TokenRegistry(load_json(ROOT / f"registries/tokens/v{version}/default.json"), expected_version=version)


def regions():
    return {name: [] for name in patterns.PATTERNS["list-page"]}


class V02CanvasHeightTests(unittest.TestCase):
    def test_new_snapshot_only_adds_minimum_height(self):
        previous = registry("0.2.1").snapshot
        current = registry("0.2.2")
        expected = deepcopy(previous["tokens"])
        expected["size.page-min-height"] = current.snapshot["tokens"]["size.page-min-height"]
        self.assertEqual(current.snapshot["tokens"], expected)
        self.assertEqual(current.resolve("size.page"), 1920)
        self.assertEqual(current.resolve("size.page-min-height"), 1080)
        self.assertEqual(current.resolve("typography.heading")["fontFamily"], "platform-default")

    def test_short_page_uses_minimum_only_under_new_policy(self):
        old_tree = patterns.instantiate("list-page", regions())
        old_result = layout.LayoutEngine(registry("0.2.1")).run(old_tree)
        self.assertEqual(old_result["status"], "PASS", old_result["issues"])
        self.assertLess(old_result["skeleton"]["box"]["height"], 1080)
        self.assertNotIn("constraints", old_tree["page"])

        new_tree = patterns.instantiate("list-page", regions(), canvas_policy="0.2.0-static-grow")
        result = layout.LayoutEngine(registry("0.2.2")).run(new_tree)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["skeleton"]["box"]["width"], 1920)
        self.assertEqual(result["skeleton"]["box"]["height"], 1080)

    def test_long_page_grows_and_contains_content(self):
        content = {"id": "long-content", "type": "Frame", "layout": {
            "width": {"mode": "fill"}, "height": {"mode": "fixed", "value": 1200}}, "children": []}
        supplied = regions()
        supplied["table"].append(content)
        tree = patterns.instantiate("list-page", supplied, canvas_policy="0.2.0-static-grow")
        result = layout.LayoutEngine(registry("0.2.2")).run(tree)
        self.assertEqual(result["status"], "PASS", result["issues"])
        page = result["skeleton"]
        self.assertGreater(page["box"]["height"], 1200)
        self.assertGreater(page["box"]["height"], 1080)
        self.assertNotIn("container_overflow", {issue["code"] for issue in result["issues"]})
        self.assertEqual(tree["page"]["layout"]["height"], {"mode": "hug"})


if __name__ == "__main__":
    unittest.main()
