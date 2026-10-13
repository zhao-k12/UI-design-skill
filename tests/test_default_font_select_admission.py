from copy import deepcopy
from importlib import import_module
import unittest

from jsonschema.exceptions import ValidationError
from adapters.component_bindings import BindingError, ComponentBindings
from adapters.figma.compiler import prepare as prepare_figma
from adapters.penpot.compiler import prepare as prepare_penpot
from validators.ui_ir import ROOT, load_json

logical = import_module("core.component-resolver.registry")
assembly = import_module("core.component-resolver.assembly")
BASE = ROOT / "registries/components/v0.2.2"
SELECT = "form.select.default.medium"


class DefaultFontSelectAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(BASE / "catalog.json")
        self.evidence = load_json(BASE / "fidelity-reports.json")
        self.registry = logical.ComponentRegistry(self.catalog, self.evidence)

    def test_snapshot_adds_only_fixed_select(self):
        self.assertEqual(set(self.catalog["components"]), {
            "action.button.primary.medium", "form.input.default.medium", SELECT})
        self.assertEqual(load_json(BASE / "admission.json")["registrySha256"], self.registry.fingerprint)
        self.assertEqual(self.registry.inspect(SELECT)["contentScope"], {
            "kind": "fixed-native-content", "modelValue": "enabled", "selectedText": "启用",
            "width": 240, "height": 32})
        self.assertNotIn(SELECT, load_json(ROOT / "registries/components/v0.2.1/catalog.json")["components"])
        self.assertEqual(load_json(ROOT / "registries/components/catalog.json")["registryVersion"], "0.1.0")

    def test_fidelity_and_bindings_cannot_expand_scope(self):
        altered = deepcopy(self.catalog)
        altered["components"][SELECT]["contentScope"]["selectedText"] = "任意文字"
        with self.assertRaises((logical.ComponentError, ValidationError)):
            logical.ComponentRegistry(altered, self.evidence)
        altered_report = deepcopy(self.evidence)
        key = self.catalog["components"][SELECT]["fidelity"]["reportId"]
        altered_report[key]["platforms"]["penpot"]["checks"]["sourceArrowOutline"] = False
        with self.assertRaises(logical.ComponentError):
            logical.ComponentRegistry(self.catalog, altered_report)
        for platform in ("figma", "penpot"):
            binding = load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.2.json")
            ComponentBindings(binding, self.registry, platform=platform)
            binding["bindings"][SELECT]["variants"]["default"]["componentReference"] = "wrong-native-id"
            with self.assertRaises(BindingError) as caught:
                ComponentBindings(binding, self.registry, platform=platform)
            self.assertEqual(caught.exception.code, "binding_native_mismatch")

    def test_assembly_only_accepts_source_selected_value(self):
        scope = self.registry.inspect(SELECT)["contentScope"]
        node = {"id": "select", "props": {"value": "启用"}, "slots": {}}
        normalized = assembly.normalize_fixed_native_content(node, scope)
        self.assertEqual(normalized["props"], {})
        for props in ({"value": "停用"}, {"value": "enabled"},
                      {"placeholder": "请选择状态"}, {}):
            with self.assertRaises(ValueError):
                assembly.normalize_fixed_native_content({"id": "select", "props": props, "slots": {}}, scope)

    def test_both_adapters_reject_content_and_geometry_overrides(self):
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        native = {"id": "select", "type": "ComponentInstance", "componentId": SELECT,
                  "variant": "default", "layout": {"width": {"mode": "fixed", "value": 240},
                                                   "height": {"mode": "fixed", "value": 32}}}
        document = {"uiIrVersion": "0.1.0", "documentId": "fixed-select",
                    "pages": [{"id": "page", "type": "Page", "children": [native]}]}
        for platform, prepare in (("figma", prepare_figma), ("penpot", prepare_penpot)):
            bindings = ComponentBindings(
                load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.2.json"),
                self.registry, platform=platform)
            file_reference = bindings.resolve(SELECT)["fileReference"]
            passed = prepare(document, tokens, self.registry, bindings, icons, file_reference=file_reference)
            self.assertEqual(passed["status"], "PASS", passed["issues"])
            for change in (lambda n: n.update(props={"value": "停用"}),
                           lambda n: n["layout"]["width"].update(value=241),
                           lambda n: n.update(style={"opacity": 0.5})):
                changed = deepcopy(document)
                change(changed["pages"][0]["children"][0])
                failed = prepare(changed, tokens, self.registry, bindings, icons, file_reference=file_reference)
                self.assertEqual(failed["status"], "FAIL")
                self.assertIn("unsupported_component", {item["code"] for item in failed["issues"]})


if __name__ == "__main__":
    unittest.main()
