from copy import deepcopy
from importlib import import_module
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError
from adapters.component_bindings import BindingError, ComponentBindings
from adapters.figma.compiler import prepare as prepare_figma
from adapters.penpot.compiler import prepare as prepare_penpot
from validators.ui_ir import ROOT, load_json
from validators.structure.gate import builder


logical = import_module("core.component-resolver.registry")
assembly = import_module("core.component-resolver.assembly")
placement = import_module("core.component-resolver.placement")
BASE = ROOT / "registries/components/v0.2.3"
TABLE = "data.table.default"


class DefaultFontTableAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(BASE / "catalog.json")
        self.evidence = load_json(BASE / "fidelity-reports.json")
        self.registry = logical.ComponentRegistry(self.catalog, self.evidence)

    def test_new_snapshot_adds_only_fixed_table(self):
        self.assertEqual(set(self.catalog["components"]), {
            "action.button.primary.medium", "form.input.default.medium",
            "form.select.default.medium", TABLE})
        self.assertEqual(load_json(BASE / "admission.json")["registrySha256"], self.registry.fingerprint)
        self.assertEqual(self.registry.inspect(TABLE)["contentScope"], logical.TABLE_SCOPE)
        self.assertNotIn(TABLE, load_json(ROOT / "registries/components/v0.2.2/catalog.json")["components"])
        self.assertEqual(load_json(ROOT / "registries/components/catalog.json")["registryVersion"], "0.1.0")

    def test_fidelity_scope_and_bindings_cannot_expand_data(self):
        altered = deepcopy(self.catalog)
        altered["components"][TABLE]["contentScope"]["data"][0]["name"] = "赵六"
        with self.assertRaises((logical.ComponentError, ValidationError)):
            logical.ComponentRegistry(altered, self.evidence)
        altered_report = deepcopy(self.evidence)
        key = self.catalog["components"][TABLE]["fidelity"]["reportId"]
        altered_report[key]["platforms"]["penpot"]["checks"]["independentNativeSvg"] = False
        with self.assertRaises(logical.ComponentError):
            logical.ComponentRegistry(self.catalog, altered_report)
        for platform in ("figma", "penpot"):
            binding = load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.3.json")
            ComponentBindings(binding, self.registry, platform=platform)
            binding["bindings"][TABLE]["variants"]["default"]["componentReference"] = "wrong-native-id"
            with self.assertRaises(BindingError) as caught:
                ComponentBindings(binding, self.registry, platform=platform)
            self.assertEqual(caught.exception.code, "binding_native_mismatch")

    def test_core_requires_exact_source_rows_and_geometry(self):
        scope = self.registry.inspect(TABLE)["contentScope"]
        source = load_json(ROOT / "examples/acceptance-prototype/source-geometry.json")
        geometry = placement.SourceGeometry({**source, "components": [next(
            c for c in source["components"] if c["logicalComponentId"] == TABLE)]}, self.registry)
        self.assertEqual(geometry.source_component(TABLE, "default")["props"],
                         {key: scope[key] for key in ("showHeader", "border", "stripe", "columns", "data")})
        node = {"id": "table", "props": {}, "slots": {}}
        normalized = assembly.normalize_fixed_native_content(node, scope, table_records=scope["data"])
        self.assertEqual(normalized["props"], {})
        self.assertEqual(normalized["slots"], {})
        for records in (None, [], scope["data"][:-1],
                        [{**scope["data"][0], "name": "赵六"}, *scope["data"][1:]]):
            with self.assertRaises(ValueError):
                assembly.normalize_fixed_native_content(node, scope, table_records=records)
        with self.assertRaises(ValueError):
            assembly.normalize_fixed_native_content({**node, "props": {"data": scope["data"]}},
                                                    scope, table_records=scope["data"])

    def test_both_adapters_reject_content_and_geometry_overrides(self):
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        icons = import_module("core.icon-resolver.registry").IconRegistry(
            import_module("icon-manager.remix-sync.manager").current())
        native = {"id": "table", "type": "ComponentInstance", "componentId": TABLE,
                  "variant": "default", "layout": {"width": {"mode": "fixed", "value": 1392},
                                                   "height": {"mode": "fixed", "value": 144}}}
        document = {"uiIrVersion": "0.1.0", "documentId": "fixed-table",
                    "pages": [{"id": "page", "type": "Page", "children": [native]}]}
        for platform, prepare in (("figma", prepare_figma), ("penpot", prepare_penpot)):
            bindings = ComponentBindings(
                load_json(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.3.json"),
                self.registry, platform=platform)
            file_reference = bindings.resolve(TABLE)["fileReference"]
            passed = prepare(document, tokens, self.registry, bindings, icons, file_reference=file_reference)
            self.assertEqual(passed["status"], "PASS", passed["issues"])
            for change in (lambda n: n.update(props={"data": [{"name": "赵六"}]}),
                           lambda n: n["layout"]["width"].update(value=1393),
                           lambda n: n.update(style={"opacity": 0.5})):
                changed = deepcopy(document)
                change(changed["pages"][0]["children"][0])
                failed = prepare(changed, tokens, self.registry, bindings, icons, file_reference=file_reference)
                self.assertEqual(failed["status"], "FAIL")
                self.assertIn("unsupported_component", {item["code"] for item in failed["issues"]})

    def test_assembly_requires_source_claim_for_every_cell(self):
        source = load_json(ROOT / "examples/acceptance-prototype/source-geometry.json")
        geometry = placement.SourceGeometry({**source, "components": [next(
            c for c in source["components"] if c["logicalComponentId"] == TABLE)]}, self.registry)
        box = {"x": 0, "y": 0, "width": 1392, "height": 144}
        mapping = {"status": "PASS", "readyForAssembly": True,
                   "rows": [{"sourceId": "table-source", "componentType": "Table", "componentId": TABLE,
                             "variant": "default", "cellId": "cell", "sectionId": "section",
                             "evidence": ["e1"]}],
                   "layoutReport": {"engineReport": {"skeleton": {
                       "id": "root", "box": box, "children": [{"id": "cell", "box": box}]}}}}
        scope = logical.TABLE_SCOPE
        record_claims = [{key: {"text": value, "evidence": ["e1"]} for key, value in row.items()}
                         for row in scope["data"]]
        item = {"sourceId": "table-source", "props": {}, "slots": {}, "tableRecords": record_claims}
        content = {"version": "0.1.0", "mappingSha256": builder.fingerprint(mapping), "items": [item]}
        analysis = {"evidence": [{"id": "e1", "quote": "张三 启用 管理员 李四 启用 编辑 王五 停用 访客"}]}
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(ROOT / "registries/tokens/default.json"))
        def run(payload):
            with patch.object(assembly.primitive_mapping, "resolve", return_value=mapping):
                return assembly.assemble(analysis, {}, ROOT, None, {}, {}, self.registry, tokens,
                                         payload, source_geometry=geometry)
        passed = run(content)
        self.assertEqual(passed["status"], "PASS", passed["issues"])
        self.assertEqual(passed["sections"]["section"][0]["instance"]["props"], {})
        for changed in (lambda entry: entry.pop("tableRecords"),
                        lambda entry: entry["tableRecords"][0]["name"].update(text="赵六"),
                        lambda entry: entry["tableRecords"][1]["role"].update(evidence=["wrong"])):
            bad = deepcopy(content)
            changed(bad["items"][0])
            result = run(bad)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["operations"], [])


if __name__ == "__main__":
    unittest.main()
