from copy import deepcopy
from importlib import import_module
import unittest

from adapters.component_bindings import BindingError, ComponentBindings
from adapters.figma.compiler import prepare as prepare_figma
from adapters.penpot.compiler import prepare as prepare_penpot
from validators.ui_ir import ROOT, load_json

logical = import_module("core.component-resolver.registry")
assembly = import_module("core.component-resolver.assembly")
BASE = ROOT / "registries/components/v0.2.1"
INPUT = "form.input.default.medium"
BUTTON = "action.button.primary.medium"


class DefaultFontInputAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(BASE / "catalog.json")
        self.evidence = load_json(BASE / "fidelity-reports.json")
        self.registry = logical.ComponentRegistry(self.catalog, self.evidence)

    def test_versioned_snapshot_admits_only_two_fixed_fixtures(self):
        self.assertEqual(set(self.catalog["components"]), {BUTTON, INPUT})
        self.assertEqual(load_json(BASE / "admission.json")["registrySha256"], self.registry.fingerprint)
        self.assertEqual(self.registry.inspect(INPUT)["contentScope"], {
            "kind": "fixed-native-content", "placeholder": "请输入姓名",
            "value": "", "width": 240, "height": 32})
        self.assertEqual(load_json(ROOT / "registries/components/v0.2.0/catalog.json")["registryVersion"], "0.2.0")
        self.assertEqual(load_json(ROOT / "registries/components/catalog.json")["registryVersion"], "0.1.0")

    def test_input_scope_and_native_binding_cannot_expand(self):
        altered = deepcopy(self.catalog)
        altered["components"][INPUT]["contentScope"]["placeholder"] = "任意文字"
        with self.assertRaises(logical.ComponentError) as caught:
            logical.ComponentRegistry(altered, self.evidence)
        self.assertEqual(caught.exception.code, "invalid_content_scope")
        for platform in ("figma", "penpot"):
            binding = load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.1.json")
            ComponentBindings(binding, self.registry, platform=platform)
            binding["bindings"][INPUT]["variants"]["default"]["componentReference"] = "wrong-native-id"
            with self.assertRaises(BindingError) as caught:
                ComponentBindings(binding, self.registry, platform=platform)
            self.assertEqual(caught.exception.code, "binding_native_mismatch")

    def test_assembly_consumes_exact_source_placeholder_and_uses_native_content(self):
        scope = self.registry.inspect(INPUT)["contentScope"]
        node = {"id": "input", "props": {"placeholder": "请输入姓名"}, "slots": {}}
        normalized = assembly.normalize_fixed_native_content(node, scope)
        self.assertEqual(normalized["props"], {})
        self.assertEqual(node["props"], {"placeholder": "请输入姓名"})
        for props in ({"placeholder": "搜索"}, {"placeholder": "请输入姓名", "value": "张三"}, {}):
            with self.assertRaises(ValueError):
                assembly.normalize_fixed_native_content({"id": "input", "props": props, "slots": {}}, scope)

    def test_both_adapters_accept_fixed_instance_and_reject_overrides(self):
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        native = {"id": "input", "type": "ComponentInstance", "componentId": INPUT,
                  "variant": "default", "layout": {"width": {"mode": "fixed", "value": 240},
                                                   "height": {"mode": "fixed", "value": 32}}}
        document = {"uiIrVersion": "0.1.0", "documentId": "fixed-input",
                    "pages": [{"id": "page", "type": "Page", "children": [native]}]}
        for platform, prepare in (("figma", prepare_figma), ("penpot", prepare_penpot)):
            bindings = ComponentBindings(
                load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.1.json"),
                self.registry, platform=platform)
            file_reference = bindings.resolve(INPUT)["fileReference"]
            passed = prepare(document, tokens, self.registry, bindings, icons, file_reference=file_reference)
            self.assertEqual(passed["status"], "PASS", passed["issues"])
            for change in (lambda n: n.update(props={"placeholder": "搜索"}),
                           lambda n: n["layout"]["width"].update(value=241)):
                changed = deepcopy(document)
                change(changed["pages"][0]["children"][0])
                failed = prepare(changed, tokens, self.registry, bindings, icons, file_reference=file_reference)
                self.assertEqual(failed["status"], "FAIL")
                self.assertIn("unsupported_component", {item["code"] for item in failed["issues"]})


if __name__ == "__main__":
    unittest.main()
