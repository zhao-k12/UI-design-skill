from copy import deepcopy
from importlib import import_module
import unittest

from adapters.component_bindings import ComponentBindings
from adapters.default_font import binding_for
from adapters.figma.compiler import prepare as prepare_figma
from adapters.penpot.compiler import prepare as prepare_penpot
from validators.ui_ir import ROOT, load_json


class DefaultPageFontPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/v0.2.0/default.json"), expected_version="0.2.0")
        self.components = import_module("core.component-resolver.registry").ComponentRegistry(
            load_json(ROOT / "registries/components/v0.2.3/catalog.json"),
            load_json(ROOT / "registries/components/v0.2.3/fidelity-reports.json"))
        self.icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        children = [{"id": "page-title", "type": "Text", "text": "用户管理",
                     "style": {"typographyToken": {"token": "typography.heading"},
                               "colorToken": {"token": "color.text"}},
                     "layout": {"width": {"mode": "fixed", "value": 80},
                                "height": {"mode": "fixed", "value": 28}}}]
        for identifier, logical_id, width, height in (
                ("query", "action.button.primary.medium", 60, 32),
                ("name", "form.input.default.medium", 240, 32),
                ("status", "form.select.default.medium", 240, 32),
                ("table", "data.table.default", 1392, 144)):
            children.append({"id": identifier, "type": "ComponentInstance", "componentId": logical_id,
                             "variant": "default", "layout": {
                                 "width": {"mode": "fixed", "value": width},
                                 "height": {"mode": "fixed", "value": height}}})
        self.document = {"uiIrVersion": "0.1.0", "documentId": "v02-adapter-contract",
                         "pages": [{"id": "page", "type": "Page", "layout": {
                             "width": {"mode": "fixed", "value": 1920},
                             "height": {"mode": "fixed", "value": 1080}}, "children": children}]}

    def prepare(self, platform, document=None, fonts=None, file_reference=None):
        bindings = ComponentBindings(
            load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.3.json"),
            self.components, platform=platform)
        if fonts is None:
            fonts = load_json(ROOT / f"adapters/{platform}/metadata/page-default-font-bindings-0.2.0.json")
        if file_reference is None:
            file_reference = bindings.resolve("data.table.default")["fileReference"]
        compiler = prepare_figma if platform == "figma" else prepare_penpot
        return compiler(document or self.document, self.tokens, self.components, bindings,
                        self.icons, font_bindings=fonts, file_reference=file_reference)

    def test_same_ui_ir_resolves_target_defaults_and_four_native_components(self):
        self.assertEqual(self.document, load_json(ROOT / "examples/v02-default-font-adapter-contract.ui-ir.json"))
        self.assertEqual(self.tokens.resolve("typography.heading")["fontFamily"], "platform-default")
        self.assertEqual(self.tokens.resolve("typography.heading")["fontWeight"], 400)
        for platform, family in (("figma", "Inter"), ("penpot", "sourcesanspro")):
            report = self.prepare(platform)
            self.assertEqual(report["status"], "PASS", report["issues"])
            children = report["plan"]["pages"][0]["children"]
            title = children[0]
            actual = title["fontName"]["family"] if platform == "figma" else title["fontBinding"]["family"]
            self.assertEqual(actual, family)
            self.assertEqual(len([n for n in children if n.get("componentReference")]), 4)
            self.assertEqual(report["nativeExecution"], "NOT_RUN")

    def test_wrong_file_font_and_unobserved_weight_are_rejected(self):
        for platform in ("figma", "penpot"):
            fonts = load_json(ROOT / f"adapters/{platform}/metadata/page-default-font-bindings-0.2.0.json")
            changed = deepcopy(fonts)
            changed["fileReference"] = "different-file"
            report = self.prepare(platform, fonts=changed)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("missing_font_binding", {i["code"] for i in report["issues"]})
            changed = deepcopy(fonts)
            changed["bindings"]["platform-default:400"]["family"] = "Wrong Font"
            report = self.prepare(platform, fonts=changed)
            self.assertIn("missing_font_binding", {i["code"] for i in report["issues"]})
            forged = deepcopy(fonts)
            forged["bindings"]["platform-default:600"] = deepcopy(fonts["bindings"]["platform-default:400"])
            self.assertIsNone(binding_for({"fontFamily": "platform-default", "fontWeight": 600}, forged,
                                          platform=platform, file_reference=fonts["fileReference"]))
            doc = deepcopy(self.document)
            doc["pages"][0]["children"][0]["style"]["typographyToken"] = {"token": "typography.body"}
            changed = deepcopy(fonts)
            changed["bindings"].pop("platform-default:400")
            report = self.prepare(platform, document=doc, fonts=changed)
            self.assertIn("missing_font_binding", {i["code"] for i in report["issues"]})


if __name__ == "__main__":
    unittest.main()
