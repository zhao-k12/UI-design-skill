"""The old visual proof must not pass as iView page conformance."""
from copy import deepcopy
from pathlib import Path
import json
import unittest

from workflow_v03.iview_conformance import audit

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class IViewConformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = read("registries/tokens/v0.2.2/default.json")
        cls.catalog = read("registries/components/v0.2.7/catalog.json")
        cls.standard = read("registries/design-standards/iview-plus-1.3.24.json")
        cls.lock = read("component-builder/source-reader/source-lock.json")
        cls.tree = {"sections": [{"items": [{"id": "users", "component":
            {"type": "Table", "id": "data.table.default"}, "sourceContent":
            {"props": {"headers": [{"text": name} for name in ("姓名", "状态", "角色")]}}}]}]}
        cls.document = {"pages": [{"id": "page", "type": "Page", "children": [
            {"id": "table.instance", "type": "ComponentInstance", "componentId": "data.table.default",
             "sourceIds": ["users"]},
            {"id": "table.header", "type": "Frame", "children": [
                {"id": "table.header.column.0.text", "type": "Text", "text": "姓名"}]}]}]}

    def test_old_page_fails_on_official_colors_and_synthetic_table_header(self):
        report = audit(self.tree, self.document, self.tokens, self.catalog,
                       self.standard, self.lock)
        codes = {issue["code"] for issue in report["issues"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("iview_token_mismatch", codes)
        self.assertIn("iview_native_table_header_required", codes)
        self.assertIn("iview_synthetic_table_header", codes)

    def test_official_source_identity_is_bound(self):
        lock = deepcopy(self.lock)
        lock["files"][self.standard["source"]["path"]] = "changed"
        report = audit(self.tree, self.document, self.tokens, self.catalog,
                       self.standard, lock)
        self.assertIn("iview_source_lock_mismatch",
                      {issue["code"] for issue in report["issues"]})

    def test_native_header_and_official_tokens_can_pass_narrow_gate(self):
        tokens = deepcopy(self.tokens)
        for token_id, color in (("color.primary", "primary"), ("color.text", "text"),
                                ("color.page", "layoutBody"), ("color.surface", "surface"),
                                ("color.border", "border")):
            tokens["tokens"][token_id]["value"] = self.standard["colors"][color]
        catalog = deepcopy(self.catalog)
        catalog["components"]["data.table.default"]["contentScope"]["showHeader"] = True
        document = deepcopy(self.document)
        document["pages"][0]["children"].pop()
        report = audit(self.tree, document, tokens, catalog, self.standard, self.lock)
        self.assertEqual(report["status"], "PASS", report["issues"])


if __name__ == "__main__":
    unittest.main()
