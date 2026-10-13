from copy import deepcopy
from importlib import import_module
import unittest
from jsonschema import ValidationError

from adapters.component_bindings import BindingError, ComponentBindings, validate_instance_scope
from adapters.figma.compiler import prepare as prepare_figma
from adapters.penpot.compiler import prepare as prepare_penpot
from validators.ui_ir import ROOT, load_json

logical = import_module("core.component-resolver.registry")
assembly = import_module("core.component-resolver.assembly")
BUTTON = "action.button.primary.medium"
BASE = ROOT / "registries/components/v0.2.0"
SCOPE = {"kind": "fixed-native-content", "text": "查询", "width": 60, "height": 32}


class DefaultFontButtonAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(BASE / "catalog.json")
        self.evidence = load_json(BASE / "fidelity-reports.json")
        self.registry = logical.ComponentRegistry(self.catalog, self.evidence)

    def test_scoped_button_and_both_native_bindings_are_admitted(self):
        self.assertEqual(self.registry.inspect(BUTTON)["contentScope"], SCOPE)
        receipt = load_json(BASE / "admission.json")
        self.assertEqual(receipt["registryAdmission"], "PASS")
        self.assertEqual(receipt["registrySha256"], self.registry.fingerprint)
        self.assertTrue(receipt["scopedPageGenerationReady"])
        for platform, expected in (("figma", "135:15"),
                                   ("penpot", "4b3abcb2-3ae8-803f-8008-c805b99e5b4e")):
            bindings = ComponentBindings(load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.0.json"),
                                         self.registry, platform=platform)
            self.assertEqual(bindings.resolve(BUTTON)["componentReference"], expected)

    def test_scope_or_report_cannot_be_broadened(self):
        for change in (lambda c: c["components"][BUTTON]["contentScope"].update(text="搜索"),
                       lambda c: c["components"][BUTTON]["contentScope"].update(width=61)):
            altered = deepcopy(self.catalog)
            change(altered)
            with self.assertRaises((ValueError, ValidationError)):
                logical.ComponentRegistry(altered, self.evidence)
        altered = deepcopy(self.evidence)
        report_id = self.catalog["components"][BUTTON]["fidelity"]["reportId"]
        altered[report_id]["platforms"]["figma"]["status"] = "FAIL"
        with self.assertRaises(logical.ComponentError):
            logical.ComponentRegistry(self.catalog, altered)

    def test_native_binding_cannot_redirect_to_another_component(self):
        binding = load_json(ROOT / "adapters/penpot/metadata/component-bindings-0.2.0.json")
        binding["bindings"][BUTTON]["variants"]["default"]["componentReference"] = "another-component"
        with self.assertRaises(BindingError) as caught:
            ComponentBindings(binding, self.registry, platform="penpot")
        self.assertEqual(caught.exception.code, "binding_native_mismatch")

    def test_assembly_accepts_only_source_verified_fixed_label(self):
        base = {"id": "button", "props": {}, "slots": {"label": [{"type": "Text", "text": "查询"}]}}
        normalized = assembly.normalize_fixed_native_content(base, SCOPE)
        self.assertEqual(normalized["slots"], {})
        self.assertEqual(base["slots"]["label"][0]["text"], "查询")
        for mutation in (lambda n: n["slots"]["label"][0].update(text="搜索"),
                         lambda n: n["props"].update(value="查询"),
                         lambda n: n["slots"].update(actions=[])):
            node = deepcopy(base)
            mutation(node)
            with self.assertRaises(ValueError):
                assembly.normalize_fixed_native_content(node, SCOPE)

    def test_both_adapters_reject_content_style_and_geometry_overrides(self):
        descriptor = self.registry.inspect(BUTTON)
        node = {"props": {}, "slots": {}, "style": {}}
        width = {"mode": "fixed", "value": 60}
        height = {"mode": "fixed", "value": 32}
        validate_instance_scope(node, descriptor, width, height)
        for changed_node, changed_width, changed_height in (
                (dict(node, slots={"label": []}), width, height),
                (dict(node, props={"label": "搜索"}), width, height),
                (dict(node, style={"fill": "red"}), width, height),
                (node, {"mode": "fixed", "value": 61}, height),
                (node, width, {"mode": "fill"})):
            with self.assertRaises(BindingError) as caught:
                validate_instance_scope(changed_node, descriptor, changed_width, changed_height)
            self.assertEqual(caught.exception.code, "unsupported_component")

    def test_both_adapter_preflights_use_the_scoped_native_master(self):
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        button = {"id": "query", "type": "ComponentInstance", "componentId": BUTTON,
                  "variant": "default", "layout": {"width": {"mode": "fixed", "value": 60},
                                                   "height": {"mode": "fixed", "value": 32}}}
        document = {"uiIrVersion": "0.1.0", "documentId": "query-only",
                    "pages": [{"id": "page", "type": "Page", "children": [button]}]}
        for platform, prepare in (("figma", prepare_figma), ("penpot", prepare_penpot)):
            binding = ComponentBindings(
                load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.0.json"),
                self.registry, platform=platform)
            file_reference = binding.resolve(BUTTON)["fileReference"]
            passed = prepare(document, tokens, self.registry, binding, icons, file_reference=file_reference)
            self.assertEqual(passed["status"], "PASS", passed["issues"])
            changed = deepcopy(document)
            changed["pages"][0]["children"][0]["layout"]["width"]["value"] = 61
            failed = prepare(changed, tokens, self.registry, binding, icons, file_reference=file_reference)
            self.assertEqual(failed["status"], "FAIL")
            self.assertIn("unsupported_component", {item["code"] for item in failed["issues"]})


if __name__ == "__main__":
    unittest.main()
