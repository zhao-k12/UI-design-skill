from copy import deepcopy
from importlib import import_module
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from adapters.component_bindings import ComponentBindings
from adapters.figma.compiler import prepare, script_for_page
from adapters.figma.icons import source_import_script
from adapters.figma.qa import validate_native_evidence
from validators.ui_ir import ROOT, load_json


class FigmaCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = import_module("core.design-rules.tokens").TokenRegistry(load_json(ROOT / "registries/tokens/default.json"))
        cls.components = import_module("core.component-resolver.registry").ComponentRegistry(load_json(ROOT / "registries/components/catalog.json"),load_json(ROOT/'registries/components/fidelity-reports.json'))
        cls.bindings = ComponentBindings(load_json(ROOT / "adapters/figma/metadata/component-bindings.json"), cls.components, platform="figma")
        cls.icons = import_module("core.icon-resolver.registry").IconRegistry(import_module("icon-manager.remix-sync.manager").current())
    def document(self):
        return {"uiIrVersion": "0.1.0", "documentId": "adapter-test", "pages": [{"id": "page", "type": "Page",
                "layout": {"width": {"mode": "fixed", "value": 1440}, "height": {"mode": "hug"}, "gap": {"token": "spacing.md"}},
                "children": [{"id": "title", "type": "Text", "text": "固定输入",
                              "style": {"typographyToken": {"token": "typography.body"}, "colorToken": {"token": "color.text"}}}]}]}
    def prepare(self, doc, **kwargs):
        return prepare(doc, self.tokens, self.components, self.bindings, self.icons,
                       font_bindings={"Noto Sans SC:400": {"family": "Noto Sans SC", "style": "Regular"}}, **kwargs)
    def codes(self, report):
        return {issue["code"] for issue in report["issues"]}
    def test_deterministic_translation_and_input_isolation(self):
        document = self.document()
        original = deepcopy(document)
        a, b = self.prepare(document), self.prepare(document)
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "PASS")
        self.assertEqual(document, original)
        page = a["plan"]["pages"][0]
        self.assertEqual(page["layout"]["gap"], 16)
        self.assertEqual(page["children"][0]["style"]["typographyToken"]["fontSize"], 14)
        self.assertEqual(a["nativeExecution"], "NOT_RUN")
    def test_missing_font_mapping_blocks_without_guessing_style(self):
        report = prepare(self.document(), self.tokens, self.components, self.bindings, self.icons)
        self.assertIn("missing_font_binding", self.codes(report))
        self.assertIsNone(report["plan"])
    def test_variable_axis_binding_must_preserve_requested_token_weight(self):
        doc = self.document()
        doc["pages"][0]["children"][0]["style"]["typographyToken"] = {"token": "typography.heading"}
        for weight in (400, 600):
            report = prepare(doc, self.tokens, self.components, self.bindings, self.icons,
                             font_bindings={"Noto Sans SC:600": {"family": "Noto Sans SC", "style": "Regular", "variationSettings": {"wght": weight}}})
            self.assertEqual(report["status"], "PASS" if weight == 600 else "FAIL")
    def test_icon_import_recipe_uses_byte_exact_official_svg_and_rejects_tamper(self):
        entry = self.icons.resolve("remix.search-line")["descriptor"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / (entry["svgSha256"] + ".svg")
            source = ROOT / "registries/icons/objects" / path.name
            path.write_bytes(source.read_bytes())
            script = source_import_script(self.icons, Path(folder), ["remix.search-line"], file_reference="test-only", page_reference="test-only")
            self.assertIn("createNodeFromSvg(icon.svg)", script)
            self.assertIn(entry["svgSha256"], script)
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                source_import_script(self.icons, Path(folder), ["remix.search-line"], file_reference="test-only", page_reference="test-only")
    def test_unadmitted_real_component_blocks_execution(self):
        doc = self.document()
        doc["pages"][0]["children"] = [{"id": "input", "type": "ComponentInstance", "componentId": "form.date-picker.default.medium",
                                       "layout": {"width": {"mode": "fixed", "value": 240}, "height": {"mode": "fixed", "value": 32}}}]
        report = self.prepare(doc)
        self.assertIn("component_not_ready", self.codes(report))
        self.assertIsNone(report["plan"])
    def test_official_svg_without_native_binding_is_not_an_instance(self):
        doc = self.document()
        doc["pages"][0]["children"] = [{"id": "search", "type": "IconInstance", "iconId": "remix.search-line",
                                       "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}}}]
        self.assertIn("missing_icon_reference", self.codes(self.prepare(doc)))
        binding = {"scope": "production", "registrySha256": self.icons.fingerprint,
                   "bindings": {"remix.search-line": {"componentReference": "fixture-test-id", "fileReference": "test-file",
                    "svgSha256": "0" * 64}}}
        self.assertIn("icon_binding_mismatch", self.codes(self.prepare(doc, icon_bindings=binding, file_reference="test-file")))
    def test_grid24_uses_exact_source_width_gap_and_span(self):
        doc = self.document()
        children = [{"id": f"col{i}", "type": "Frame", "layout": {"span": 6, "width": {"mode": "fill"}}, "children": []} for i in range(5)]
        doc["pages"][0]["children"] = [{"id": "grid", "type": "Grid", "layout": {"gridColumns": 24, "width": {"mode": "fill"},
                                              "gap": {"token": "spacing.md"}}, "children": children}]
        report = self.prepare(doc)
        self.assertEqual(report["status"], "PASS")
        cells = report["plan"]["pages"][0]["children"][0]["gridCells"]
        self.assertEqual([cell["row"] for cell in cells], [0,0,0,0,1])
        self.assertAlmostEqual(cells[0]["width"], (1440 - 3 * 16) / 4)
    def test_grid_rejects_unbounded_and_exhausted_width(self):
        for layout in ({"gridColumns": 24}, {"gridColumns": 24, "width": {"mode": "fixed", "value": 100}, "gap": {"token": "spacing.md"}}):
            doc = self.document()
            doc["pages"][0]["children"] = [{"id": "grid", "type": "Grid", "layout": layout, "children": []}]
            self.assertIsNone(self.prepare(doc)["plan"])
    def test_unsupported_resources_and_ambiguous_styles_fail_explicitly(self):
        for node in ({"id": "image", "type": "Image", "assetId": "logo", "alt": "Logo"},
                     {"id": "frame", "type": "Frame", "style": {"spacingToken": {"token": "spacing.md"}}, "children": []}):
            doc = self.document()
            doc["pages"][0]["children"] = [node]
            self.assertIsNone(self.prepare(doc)["plan"])
    def test_invalid_ui_ir_and_missing_token_stop_before_translation(self):
        doc = self.document()
        doc["pages"][0]["figmaNodeId"] = "bad"
        self.assertIsNone(self.prepare(doc)["plan"])
        doc = self.document()
        doc["pages"][0]["layout"]["gap"] = {"token": "spacing.missing"}
        self.assertIn("missing_token", self.codes(self.prepare(doc)))
    def test_payload_is_json_encoded_not_executable_user_text(self):
        doc = self.document()
        doc["pages"][0]["children"][0]["text"] = '"; throw new Error("injection"); //'
        report = self.prepare(doc)
        code = script_for_page(report["plan"])
        self.assertTrue(code.startswith("const payload = {"))
        self.assertIn('\\"injection\\"', code)
        self.assertEqual(code.count("await api.setCurrentPageAsync(page)"), 1)
        self.assertNotIn("detachInstance", code)
    def test_failure_invalidates_stale_scripts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as folder:
            target = Path(folder)
            (target / "page-0.js").write_text("stale success")
            (target / "generated_scripts.json").write_text(json.dumps({"status": "PASS", "scripts": {
                "page-0.js": hashlib.sha256((target / "page-0.js").read_bytes()).hexdigest()}}))
            result = subprocess.run([sys.executable, "-m", "adapters.figma", "examples/user-management.ui-ir.json", "--output-dir", str(target)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((target / "page-0.js").exists())
            report = load_json(target / "adapter_preflight_report.json")
            self.assertIsNone(report["plan"])
            self.assertEqual(report["nativeExecution"], "NOT_RUN")
    def test_modified_script_is_preserved_and_never_leaves_pass_report(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as folder:
            target = Path(folder)
            original = b"generated"
            (target / "page-0.js").write_bytes(b"user modified")
            (target / "generated_scripts.json").write_text(json.dumps({"status": "PASS", "scripts": {"page-0.js": hashlib.sha256(original).hexdigest()}}))
            result = subprocess.run([sys.executable, "-m", "adapters.figma", "examples/adapter-native-smoke.ui-ir.json", "--output-dir", str(target)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual((target / "page-0.js").read_bytes(), b"user modified")
            self.assertEqual(load_json(target / "adapter_preflight_report.json")["status"], "FAIL")
    def test_recorded_native_evidence_matches_fixed_smoke_ir_and_detects_drift(self):
        report = prepare(load_json(ROOT / "examples/adapter-native-smoke.ui-ir.json"), self.tokens, self.components, self.bindings, self.icons,
                         load_json(ROOT / "adapters/figma/metadata/icon-bindings.json"), load_json(ROOT / "adapters/figma/metadata/font-bindings.json"),
                         file_reference="0vGWSRoLxBiVPXiZ8xJAX9")
        native = load_json(ROOT / "adapters/figma/metadata/native-smoke-evidence.json")
        self.assertEqual(validate_native_evidence(report['plan'],native,load_json(ROOT/'adapters/figma/metadata/icon-bindings.json'))['status'],'FAIL')
        # Historical smoke uses the earlier planned catalog. Its measurements
        # remain useful, but current admission invalidates the catalog binding.
        report['plan']['componentsSha256']=native['componentsSha256']
        icons = load_json(ROOT / "adapters/figma/metadata/icon-bindings.json")
        self.assertEqual(validate_native_evidence(report["plan"], native, icons)["status"], "PASS")
        changed = deepcopy(native)
        next(entry for entry in changed["evidence"] if entry["uiIrId"] == "column0")["width"] += 1
        self.assertEqual(validate_native_evidence(report["plan"], changed, icons)["status"], "FAIL")
        changed = deepcopy(native)
        next(entry for entry in changed["evidence"] if entry["uiIrId"] == "icon0")["mainComponentReference"] = "wrong-reference"
        self.assertEqual(validate_native_evidence(report["plan"], changed, icons)["status"], "FAIL")
        changed = deepcopy(native)
        next(entry for entry in changed["evidence"] if entry["uiIrId"] == "native-page")["layoutSizingVertical"] = "FIXED"
        self.assertEqual(validate_native_evidence(report["plan"], changed, icons)["status"], "FAIL")
