"""Replacement-file native Remix masters are source-bound and usable by V0.2 Adapter."""
from copy import deepcopy
from importlib import import_module
import unittest

from adapters.component_bindings import ComponentBindings
from adapters.penpot.compiler import prepare
from adapters.penpot.icon_admission_v02 import FILE, REPORT, MASTER_IDS, build_gate, verify_binding
from validators.ui_ir import ROOT, load_json


class PenpotIconsV02Tests(unittest.TestCase):
    def setUp(self):
        self.binding = load_json(ROOT / "adapters/penpot/metadata/icon-bindings-0.2.0.json")
        self.icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())

    def test_native_gate_and_binding_match_current_file(self):
        self.assertEqual(load_json(REPORT), build_gate())
        for icon_id, (component_id, _) in MASTER_IDS.items():
            row = verify_binding(icon_id, self.binding["bindings"][icon_id], FILE, self.icons.fingerprint)
            self.assertEqual(row["componentReference"], component_id)
            with self.assertRaises(ValueError):
                verify_binding(icon_id, self.binding["bindings"][icon_id], "deleted-file", self.icons.fingerprint)
        self.assertNotEqual(self.binding["bindings"]["remix.download-line"]["fileReference"],
                            load_json(ROOT / "adapters/penpot/metadata/icon-bindings.json")["bindings"]["remix.download-line"]["fileReference"])

    def test_tampered_source_bound_path_is_rejected(self):
        altered = deepcopy(self.binding["bindings"]["remix.download-line"])
        altered["svgSha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_binding("remix.download-line", altered, FILE, self.icons.fingerprint)

    def test_v02_adapter_accepts_real_icon_masters(self):
        document = load_json(ROOT / "examples/v02-default-font-adapter-contract.ui-ir.json")
        for icon_id in MASTER_IDS:
            document["pages"][0]["children"].append({"id": icon_id, "type": "IconInstance", "iconId": icon_id,
                "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}}})
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
        components = import_module("core.component-resolver.registry").ComponentRegistry(
            load_json(ROOT / "registries/components/v0.2.3/catalog.json"),
            load_json(ROOT / "registries/components/v0.2.3/fidelity-reports.json"))
        component_bindings = ComponentBindings(
            load_json(ROOT / "adapters/penpot/metadata/component-bindings-0.2.3.json"), components, platform="penpot")
        font_bindings = load_json(ROOT / "adapters/penpot/metadata/page-default-font-bindings-0.2.0.json")
        report = prepare(document, tokens, components, component_bindings, self.icons,
                         self.binding, font_bindings, file_reference=FILE)
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["nativeExecution"], "NOT_RUN")
        references = {node.get("componentReference") for node in report["plan"]["pages"][0]["children"]}
        self.assertTrue({item[0] for item in MASTER_IDS.values()}.issubset(references))


if __name__ == "__main__":
    unittest.main()
