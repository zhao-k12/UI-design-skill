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
CHECKBOX = "form.checkbox.default.enabled"
BASE = ROOT / "registries/components/v0.2.5"


class DefaultFontCheckboxAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(BASE / "catalog.json")
        self.evidence = load_json(BASE / "fidelity-reports.json")
        self.registry = logical.ComponentRegistry(self.catalog, self.evidence)

    def test_new_snapshot_only_adds_fixed_checkbox(self):
        previous = load_json(ROOT / "registries/components/v0.2.4/catalog.json")
        self.assertEqual(set(self.catalog["components"]) - set(previous["components"]), {CHECKBOX})
        self.assertEqual(self.registry.inspect(CHECKBOX)["contentScope"], logical.CHECKBOX_SCOPE)
        self.assertEqual(load_json(BASE / "admission.json")["registrySha256"], self.registry.fingerprint)
        self.assertNotIn(CHECKBOX, previous["components"])
        self.assertEqual(load_json(ROOT / "registries/components/catalog.json")["registryVersion"], "0.1.0")

    def test_scope_and_fidelity_cannot_expand(self):
        for key, value in (("text", "停用"), ("width", 53), ("modelValue", False), ("indeterminate", True)):
            altered = deepcopy(self.catalog)
            altered["components"][CHECKBOX]["contentScope"][key] = value
            with self.assertRaises((logical.ComponentError, ValidationError)):
                logical.ComponentRegistry(altered, self.evidence)
        changed = deepcopy(self.evidence)
        changed[self.catalog["components"][CHECKBOX]["fidelity"]["reportId"]]["platforms"]["penpot"]["checks"]["nativeRepeatStable"] = False
        with self.assertRaises(logical.ComponentError):
            logical.ComponentRegistry(self.catalog, changed)

    def test_core_requires_exact_source_claim_then_strips_content(self):
        scope = self.registry.inspect(CHECKBOX)["contentScope"]
        node = {"id": "checkbox", "props": {}, "slots": {"label": [{"type": "Text", "text": "启用"}]}}
        self.assertEqual(assembly.normalize_fixed_native_content(node, scope)["slots"], {})
        changed = deepcopy(node)
        changed["slots"]["label"][0]["text"] = "停用"
        with self.assertRaises(ValueError):
            assembly.normalize_fixed_native_content(changed, scope)

    def test_both_bindings_and_adapters_reject_overrides(self):
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        node = {"id": "checkbox", "type": "ComponentInstance", "componentId": CHECKBOX,
                "variant": "default", "layout": {"width": {"mode": "fixed", "value": 52},
                                                   "height": {"mode": "fixed", "value": 21}}}
        document = {"uiIrVersion": "0.1.0", "documentId": "fixed-checkbox",
                    "pages": [{"id": "page", "type": "Page", "children": [node]}]}
        for platform, prepare in (("figma", prepare_figma), ("penpot", prepare_penpot)):
            data = load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.5.json")
            bindings = ComponentBindings(data, self.registry, platform=platform)
            file_reference = bindings.resolve(CHECKBOX)["fileReference"]
            passed = prepare(document, tokens, self.registry, bindings, icons, file_reference=file_reference)
            self.assertEqual(passed["status"], "PASS", passed["issues"])
            for mutation in (lambda n: n.update(props={"text": "停用"}),
                             lambda n: n["layout"]["width"].update(value=53),
                             lambda n: n.update(style={"opacity": 0.5})):
                changed = deepcopy(document)
                mutation(changed["pages"][0]["children"][0])
                failed = prepare(changed, tokens, self.registry, bindings, icons, file_reference=file_reference)
                self.assertEqual(failed["status"], "FAIL")
                self.assertIn("unsupported_component", {item["code"] for item in failed["issues"]})
            changed = deepcopy(data)
            changed["bindings"][CHECKBOX]["variants"]["default"]["componentReference"] = "wrong-native-id"
            with self.assertRaises(BindingError):
                ComponentBindings(changed, self.registry, platform=platform)


if __name__ == "__main__":
    unittest.main()
