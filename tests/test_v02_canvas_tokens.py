"""The versioned 1920px canvas token must not change earlier snapshots."""
import importlib
from copy import deepcopy
from pathlib import Path
import unittest

from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]
tokens_module = importlib.import_module("core.design-rules.tokens")
patterns = importlib.import_module("core.layout.patterns")
engine = importlib.import_module("core.layout.engine")


class V02CanvasTokensTests(unittest.TestCase):
    def test_new_snapshot_changes_only_page_width(self):
        previous = load_json(ROOT / "registries/tokens/v0.2.0/default.json")
        current = load_json(ROOT / "registries/tokens/v0.2.1/default.json")
        old_tokens = deepcopy(previous["tokens"])
        old_tokens["size.page"]["value"] = 1920
        self.assertEqual(current["tokens"], old_tokens)
        self.assertEqual(tokens_module.TokenRegistry(previous, expected_version="0.2.0").resolve("size.page"), 1440)
        registry = tokens_module.TokenRegistry(current, expected_version="0.2.1")
        self.assertEqual(registry.resolve("size.page"), 1920)
        self.assertEqual(registry.resolve("typography.heading")["fontFamily"], "platform-default")

    def test_layout_pattern_resolves_new_page_width(self):
        registry = tokens_module.TokenRegistry(load_json(ROOT / "registries/tokens/v0.2.1/default.json"))
        regions = {name: [] for name in patterns.PATTERNS["list-page"]}
        report = engine.LayoutEngine(registry).run(patterns.instantiate("list-page", regions))
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["skeleton"]["box"]["width"], 1920)

    def test_wrong_version_is_rejected(self):
        snapshot = load_json(ROOT / "registries/tokens/v0.2.1/default.json")
        with self.assertRaises(tokens_module.RegistryError):
            tokens_module.TokenRegistry(snapshot, expected_version="0.2.0")


if __name__ == "__main__":
    unittest.main()
