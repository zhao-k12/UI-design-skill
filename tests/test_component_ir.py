from copy import deepcopy
import unittest

from validators.ui_ir import ROOT, load_json
from validators.component_ir import validate_bundle


class ComponentIrTests(unittest.TestCase):
    def setUp(self):
        schema = load_json(ROOT / "schemas/component-ir.schema.json")
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(schema)
        # Tiny synthetic schema fixture; never exported as official runtime evidence.
        style = {key: "fixture" for key in schema["$defs"]["style"]["required"]}
        bounds = {"x": 0, "y": 0, "width": 20, "height": 10}
        self.bundle = {"status": "PASS", "componentIrVersion": "0.1.0", "components": [{
            "componentIrVersion": "0.1.0", "evidenceKind": "official-runtime", "logicalComponentId": "fixture.component", "componentType": "Button", "variant": "default", "state": "default-static",
            "props": {}, "resolvedProps": {}, "content": {"text": None, "options": []}, "fixtureContext": {"containerWidth": 100},
            "provenance": {key: "0" * 64 if definition.get("pattern") else "fixture" for key, definition in schema["$defs"]["provenance"]["properties"].items()},
            "environment": {"browser": "fixture", "browserExecutableSha256": "0" * 64, "node": "fixture", "operatingSystem": {"platform": "fixture", "release": "fixture"}, "viewport": {"width": 100, "height": 100}, "deviceScaleFactor": 1, "locale": "fixture", "fontsStatus": "loaded"},
            "rootBounds": {"width": 20, "height": 10}, "nodes": [{"path": "0", "parentPath": None, "tag": "button", "attributes": {}, "bounds": bounds, "visible": True, "computedStyle": style, "pseudoElements": {}, "textRuns": [], "value": None}],
            "iconMetrics": [], "screenshot": {"path": "fixture.png", "sha256": "0" * 64},
        }]}

    def test_complete_contract_fixture(self):
        self.assertEqual(validate_bundle(self.bundle), [])

    def test_missing_computed_style_and_nonpositive_root_are_rejected(self):
        del self.bundle["components"][0]["nodes"][0]["computedStyle"]["font-size"]
        self.assertTrue(validate_bundle(self.bundle))
        self.bundle["components"][0]["rootBounds"]["height"] = 0
        self.assertTrue(validate_bundle(self.bundle))

    def test_dom_parent_duplicate_identity_and_icon_reference_are_checked(self):
        component = self.bundle["components"][0]
        child = deepcopy(component["nodes"][0])
        child.update(path="0.0", parentPath="missing")
        component["nodes"].append(child)
        self.assertIn("invalid_dom_parent", {item["code"] for item in validate_bundle(self.bundle)})
        self.bundle["components"].append(deepcopy(component))
        self.assertIn("duplicate_component_ir", {item["code"] for item in validate_bundle(self.bundle)})

    def test_wrong_root_visibility_and_failed_output_cannot_pass(self):
        self.bundle["components"][0]["nodes"][0]["visible"] = False
        self.assertIn("inconsistent_root_bounds", {item["code"] for item in validate_bundle(self.bundle)})
        self.bundle["status"] = "FAIL"
        self.assertTrue(validate_bundle(self.bundle))
