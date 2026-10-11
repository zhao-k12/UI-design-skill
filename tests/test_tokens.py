from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
from validators.ui_ir import ROOT, load_json, validate_document

tokens = import_module("core.design-rules.tokens")


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.data = load_json(ROOT / "registries" / "tokens" / "default.json")
        self.document = load_json(ROOT / "examples" / "user-management.ui-ir.json")

    def test_registry_schema_and_required_categories(self):
        schema = load_json(ROOT / "schemas" / "token-registry.schema.json")
        Draft202012Validator.check_schema(schema)
        registry = tokens.TokenRegistry(self.data)
        self.assertEqual({v["type"] for v in registry.snapshot["tokens"].values()}, {"color", "typography", "spacing", "radius", "border", "shadow", "size"})
        self.assertEqual(self.data["tokens"]["spacing.page"]["role"], "page-padding")
        self.assertEqual(self.data["tokens"]["spacing.section"]["role"], "section-gap")

    def test_aliases_and_composite_references_resolve(self):
        registry = tokens.TokenRegistry(self.data)
        self.assertEqual(registry.resolve("spacing.page"), 24)
        self.assertEqual(registry.resolve("border.default"), {"color": "#d8dee6", "width": 1, "style": "solid"})
        self.assertEqual(registry.resolve("typography.heading")["fontSize"], 20)
        self.assertEqual(registry.resolve("shadow.card")[0]["blur"], 8)

    def test_example_references_pass_without_modifying_ui_ir(self):
        original = deepcopy(self.document)
        registry = tokens.TokenRegistry(self.data)
        self.assertEqual(validate_document(self.document), [])
        self.assertEqual(tokens.check_references(self.document, registry), [])
        self.assertEqual(self.document, original)

    def test_missing_token_reports_exact_path_without_fallback(self):
        self.document["pages"][0]["layout"]["gap"] = {"token": "spacing.unknown"}
        original = deepcopy(self.document)
        issues = tokens.check_references(self.document, tokens.TokenRegistry(self.data))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "missing_token")
        self.assertEqual(issues[0]["token"], "spacing.unknown")
        self.assertEqual(issues[0]["path"], "/pages/0/layout/gap")
        self.assertEqual(self.document, original)

    def test_fixed_dimension_rejects_wrong_token_type_or_zero(self):
        for token_id, code in (("color.primary", "token_type_mismatch"), ("spacing.none", "invalid_token_value")):
            self.document["pages"][0]["layout"]["width"]["value"] = {"token": token_id}
            self.assertEqual(tokens.check_references(self.document, tokens.TokenRegistry(self.data))[0]["code"], code)

    def test_unknown_direct_resolve_is_explicit_missing(self):
        with self.assertRaises(tokens.TokenError) as caught:
            tokens.TokenRegistry(self.data).resolve("color.unknown")
        self.assertEqual(caught.exception.code, "missing_token")

    def test_registry_dangling_reference_and_cycles_fail(self):
        for value, code in (({"token": "spacing.unknown"}, "missing_token"), ({"token": "spacing.page"}, "token_cycle")):
            data = deepcopy(self.data)
            data["tokens"]["spacing.page"]["value"] = value
            with self.assertRaises(tokens.RegistryError) as caught:
                tokens.TokenRegistry(data)
            self.assertIn(code, {i["code"] for i in caught.exception.issues})
        self.data["tokens"]["spacing.lg"]["value"] = {"token": "spacing.section"}
        with self.assertRaises(tokens.RegistryError) as caught:
            tokens.TokenRegistry(self.data)
        self.assertIn("token_cycle", {i["code"] for i in caught.exception.issues})

    def test_unused_composite_with_missing_reference_fails(self):
        self.data["tokens"]["shadow.card"]["value"][0]["color"] = {"token": "color.unknown"}
        with self.assertRaises(tokens.RegistryError) as caught:
            tokens.TokenRegistry(self.data)
        self.assertIn("missing_token", {i["code"] for i in caught.exception.issues})

    def test_registry_values_and_prefixes_are_validated(self):
        for name, value in (("spacing.md", -1), ("size.icon", 0), ("color.primary", "blue"), ("radius.sm", True), ("typography.heading", {"fontSize": 20})):
            data = deepcopy(self.data)
            data["tokens"][name]["value"] = value
            with self.subTest(name=name), self.assertRaises(tokens.RegistryError):
                tokens.TokenRegistry(data)
        self.data["tokens"]["color.primary"] = {"type": "spacing", "value": 8}
        with self.assertRaises(tokens.RegistryError) as caught:
            tokens.TokenRegistry(self.data)
        self.assertEqual(caught.exception.issues[0]["code"], "token_type_mismatch")

    def test_registry_snapshot_and_resolved_values_are_isolated(self):
        registry = tokens.TokenRegistry(self.data)
        fingerprint = registry.fingerprint
        self.data["tokens"]["spacing.md"]["value"] = 999
        snapshot = registry.snapshot
        snapshot["tokens"]["spacing.md"]["value"] = 888
        border = registry.resolve("border.default")
        border["width"] = 777
        self.assertEqual(registry.resolve("spacing.md"), 16)
        self.assertEqual(registry.resolve("border.default")["width"], 1)
        self.assertEqual(registry.fingerprint, fingerprint)
        with self.assertRaises(AttributeError):
            registry.version = "0.2.0"
        with self.assertRaises(AttributeError):
            registry.fingerprint = "different"

    def test_unregistered_raw_visual_values_fail_without_replacement(self):
        registry = tokens.TokenRegistry(self.data)
        for target, key, value in (("layout", "gap", 17), ("style", "fill", "#123abc"), ("style", "radius", 7)):
            doc = deepcopy(self.document)
            doc["pages"][0][target][key] = value
            original = deepcopy(doc)
            issues = tokens.check_references(doc, registry)
            self.assertEqual(issues[0]["code"], "unregistered_visual_value")
            self.assertEqual(doc, original)

    def test_declared_raw_scale_values_and_fixed_geometry_remain_valid(self):
        page = self.document["pages"][0]
        page["layout"]["gap"] = 16
        page["layout"]["width"]["value"] = 1377
        page["style"]["fill"] = "#FFFFFF"
        page["style"]["radius"] = 0
        self.assertEqual(tokens.check_references(self.document, tokens.TokenRegistry(self.data)), [])

    def test_cli_cannot_overwrite_its_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.json"
            content = json.dumps(self.document)
            path.write_text(content, encoding="utf-8")
            result = subprocess.run([sys.executable, "-X", "utf8", "-m", "validators.tokens", str(path), "--report", str(path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_version_expectation_and_fingerprint_are_deterministic(self):
        registry = tokens.TokenRegistry(self.data, expected_version="0.1.0")
        reordered = {key: self.data[key] for key in reversed(list(self.data))}
        self.assertEqual(registry.fingerprint, tokens.TokenRegistry(reordered).fingerprint)
        self.assertEqual(len(registry.fingerprint), 64)
        with self.assertRaises(tokens.RegistryError) as caught:
            tokens.TokenRegistry(self.data, expected_version="0.2.0")
        self.assertEqual(caught.exception.issues[0]["code"], "token_version_mismatch")

    def test_slots_checked_and_business_token_keys_ignored(self):
        table = self.document["pages"][0]["children"][3]["children"][0]
        table["props"]["businessData"] = {"token": "auth-value"}
        table["slots"] = {"content": [{"id": "slot.text", "type": "Text", "text": "x", "style": {"colorToken": {"token": "color.unknown"}}}]}
        issues = tokens.check_references(self.document, tokens.TokenRegistry(self.data))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["path"], "/pages/0/children/3/children/0/slots/content/0/style/colorToken")

    def test_border_shadow_and_existing_stroke_parts_are_consumable(self):
        self.document["pages"][0]["style"].update(stroke={"token": "border.default"}, shadowToken={"token": "shadow.card"}, radius={"token": "radius.sm"})
        registry = tokens.TokenRegistry(self.data)
        self.assertEqual(validate_document(self.document), [])
        self.assertEqual(tokens.check_references(self.document, registry), [])
        self.document["pages"][0]["style"]["stroke"] = {"color": {"token": "color.border"}, "width": {"token": "spacing.none"}}
        self.assertEqual(validate_document(self.document), [])
        self.assertEqual(tokens.check_references(self.document, registry), [])

    def test_cli_persists_pass_and_missing_token_reports(self):
        command = [sys.executable, "-X", "utf8", "-m", "validators.tokens"]
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "document.json"
            report = Path(directory) / "qa.json"
            for missing in (False, True):
                if missing:
                    self.document["pages"][0]["layout"]["gap"] = {"token": "spacing.unknown"}
                document.write_text(json.dumps(self.document), encoding="utf-8")
                result = subprocess.run(command + [str(document), "--report", str(report)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 1 if missing else 0, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(output, load_json(report))
                self.assertEqual(output["status"], "FAIL" if missing else "PASS")
                if missing:
                    self.assertEqual(output["issues"][0]["code"], "missing_token")

    def test_cli_stops_on_invalid_contract_or_registry(self):
        command = [sys.executable, "-X", "utf8", "-m", "validators.tokens"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{}", encoding="utf-8")
            for args, expected_code in (([str(path)], "schema_violation"), ([str(ROOT / "examples" / "user-management.ui-ir.json"), "--registry", str(path)], "invalid_token_registry")):
                result = subprocess.run(command + args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(expected_code, {i["code"] for i in json.loads(result.stdout)["issues"]})


if __name__ == "__main__":
    unittest.main()
