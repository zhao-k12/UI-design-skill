from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
from validators.ui_ir import ROOT, SCHEMA_PATH, load_json, validate_document


class UiIrTests(unittest.TestCase):
    def setUp(self):
        self.document = load_json(ROOT / "examples" / "user-management.ui-ir.json")

    def node(self):
        return self.document["pages"][0]

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(load_json(SCHEMA_PATH))

    def test_example_is_valid_and_covers_acceptance_structure(self):
        self.assertEqual(validate_document(self.document), [])
        sections = self.node()["children"]
        self.assertEqual([s["name"] for s in sections], ["Header", "SearchSection", "Toolbar", "TableSection"])
        columns = sections[1]["children"][0]["children"]
        self.assertEqual(len(columns), 4)
        self.assertEqual([column["layout"]["span"] for column in columns], [6] * 4)
        self.assertEqual(sections[3]["children"][0]["componentId"], "data.table.default")

    def test_all_minimum_node_types_are_supported(self):
        types = ["Frame", "Section", "Grid", "Row", "Column", "VerticalStack", "HorizontalStack", "Text", "ComponentInstance", "IconInstance", "Image", "Divider"]
        for kind in types:
            with self.subTest(kind=kind):
                child = {"id": "test.node", "type": kind}
                if kind in types[:7]:
                    child["children"] = []
                if kind == "Grid":
                    child["layout"] = {"gridColumns": 24}
                if kind == "Text":
                    child["text"] = "示例"
                if kind == "ComponentInstance":
                    child["componentId"] = "form.input.default.medium"
                if kind == "IconInstance":
                    child["iconId"] = "remix.search-line"
                if kind == "Image":
                    child.update(assetId="asset.logo", alt="标识")
                self.node()["children"] = [child]
                self.assertEqual(validate_document(self.document), [])

    def test_dimension_modes_are_exclusive(self):
        for value in ({"mode": "fixed", "value": 120}, {"mode": "fixed", "value": {"token": "size.control"}}, {"mode": "fill"}, {"mode": "hug"}):
            self.node()["layout"]["width"] = value
            self.assertEqual(validate_document(self.document), [])
        for value in ({"mode": "fixed"}, {"mode": "fill", "value": 1}, {"mode": "hug", "value": 1}, {"mode": "fixed", "value": 0}, {"mode": "fixed", "value": True}, "fill"):
            with self.subTest(value=value):
                self.node()["layout"]["width"] = value
                self.assertTrue(validate_document(self.document))

    def test_style_fill_and_layout_fill_are_distinct(self):
        self.node()["layout"]["width"] = {"mode": "fill"}
        self.node()["style"]["fill"] = "#aabbcc"
        self.assertEqual(validate_document(self.document), [])
        self.node()["style"]["fill"] = "fill"
        self.assertTrue(validate_document(self.document))

    def test_visual_attributes_validate_values_and_token_categories(self):
        self.node()["style"] = {
            "fill": "#ffffff80", "stroke": {"color": {"token": "color.border"}, "width": 1},
            "radius": {"token": "radius.sm"}, "opacity": 0.5,
            "typographyToken": {"token": "typography.body"},
            "colorToken": {"token": "color.text"}, "spacingToken": {"token": "spacing.md"},
        }
        self.assertEqual(validate_document(self.document), [])
        for key, value in (("opacity", 1.1), ("opacity", -0.1), ("radius", -1), ("fill", "#xyz123"), ("typographyToken", {"token": "color.text"}), ("stroke", {"width": 1})):
            doc = deepcopy(self.document)
            doc["pages"][0]["style"][key] = value
            self.assertTrue(validate_document(doc))

    def test_deep_container_tree_uses_type_selected_branches(self):
        child = {"id": "deep.text", "type": "Text", "text": "Nested contract"}
        for depth in range(20):
            child = {"id": f"deep.section.{depth}", "type": "Section", "children": [child]}
        self.node()["children"] = [child]
        self.assertEqual(validate_document(self.document), [])

    def test_tokens_are_typed_but_not_resolved(self):
        self.node()["layout"]["gap"] = {"token": "spacing.not-yet-registered"}
        self.assertEqual(validate_document(self.document), [])
        for value in ({"token": "color.primary"}, {"token": "spacing."}, {"token": "spacing.md", "value": 16}):
            self.node()["layout"]["gap"] = value
            self.assertTrue(validate_document(self.document))

    def test_unknown_fields_and_platform_metadata_are_rejected(self):
        for key in ("figmaNodeId", "penpotShapeId", "adapterMetadata", "x", "y", "unknown"):
            with self.subTest(key=key):
                doc = deepcopy(self.document)
                doc["pages"][0][key] = "123"
                self.assertTrue(validate_document(doc))
        table = self.node()["children"][3]["children"][0]
        table["props"]["rows"][0]["figmaNodeId"] = "123"
        self.assertIn("platform_field", {i["code"] for i in validate_document(self.document)})
        self.assertFalse(Draft202012Validator(load_json(SCHEMA_PATH)).is_valid(self.document))

    def test_resource_ids_and_text_are_required(self):
        for kind, field in (("Text", "text"), ("ComponentInstance", "componentId"), ("IconInstance", "iconId"), ("Image", "assetId")):
            self.node()["children"] = [{"id": "test.node", "type": kind}]
            self.assertTrue(validate_document(self.document), field)

    def test_duplicate_ids_in_children_and_slots_are_rejected(self):
        duplicate = deepcopy(self.node()["children"][0]["children"][0])
        table = self.node()["children"][3]["children"][0]
        table["slots"] = {"content": [duplicate]}
        issues = validate_document(self.document)
        self.assertEqual([i["code"] for i in issues], ["duplicate_node_id"])
        self.assertIn("/slots/content/0/id", issues[0]["path"])

    def test_pages_cannot_be_nested(self):
        self.node()["children"] = [{"id": "nested.page", "type": "Page", "children": []}]
        self.assertTrue(validate_document(self.document))

    def test_layout_bounds_and_direction_are_checked(self):
        for key, value in (("span", 25), ("span", 0), ("gap", -1), ("padding", {"top": 8}), ("wrap", "true")):
            doc = deepcopy(self.document)
            doc["pages"][0]["layout"][key] = value
            self.assertTrue(validate_document(doc))
        grid = self.node()["children"][1]["children"][0]
        grid["layout"]["gridColumns"] = 12
        self.assertTrue(validate_document(self.document))
        self.node()["children"] = [{"id": "row", "type": "Row", "children": [], "layout": {"direction": "vertical"}}]
        self.assertTrue(validate_document(self.document))

    def test_version_and_root_are_checked(self):
        self.document["uiIrVersion"] = "2.0.0"
        self.assertTrue(validate_document(self.document))
        for value in (None, [], {}, {"uiIrVersion": "0.1.0", "documentId": "test", "pages": []}):
            self.assertTrue(validate_document(value))

    def test_non_json_numbers_and_duplicate_keys_are_rejected(self):
        self.node()["layout"]["gap"] = float("nan")
        self.assertEqual(validate_document(self.document)[0]["code"], "invalid_json")
        for value in ({1: "non-string key"}, ("tuple",), {"object": object()}):
            self.assertEqual(validate_document(value)[0]["code"], "invalid_json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for text in ('{"id": "one", "id": "two"}', '{"gap": NaN}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_json(path)

    def test_cli_pass_and_fail_exit_codes(self):
        command = [sys.executable, "-X", "utf8", str(ROOT / "validators" / "ui_ir.py")]
        valid = subprocess.run(command + [str(ROOT / "examples" / "user-management.ui-ir.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["status"], "PASS")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"pages": []}', encoding="utf-8")
            invalid = subprocess.run(command + [str(path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stdout)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
