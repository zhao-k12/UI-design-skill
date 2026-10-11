"""Local compiler guards only; these tests are not Penpot platform acceptance."""
from copy import deepcopy
from importlib import import_module
import unittest

from adapters.component_bindings import ComponentBindings
from adapters.penpot.compiler import prepare, script_for_page
from validators.ui_ir import ROOT, load_json


class PenpotCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = import_module("core.design-rules.tokens").TokenRegistry(load_json(ROOT / "registries/tokens/default.json"))
        cls.components = import_module("core.component-resolver.registry").ComponentRegistry(
            load_json(ROOT / "registries/components/catalog.json"), load_json(ROOT / "registries/components/fidelity-reports.json"))
        cls.bindings = ComponentBindings(load_json(ROOT / "adapters/penpot/metadata/component-bindings.json"), cls.components, platform="penpot")
        cls.icons = import_module("core.icon-resolver.registry").IconRegistry(import_module("icon-manager.remix-sync.manager").current())

    def document(self):
        return {"uiIrVersion":"0.1.0", "documentId":"penpot-local-test", "pages":[{"id":"page", "type":"Page",
            "layout":{"width":{"mode":"fixed", "value":1440}}, "children":[{"id":"title", "type":"Text", "text":"固定输入",
            "style":{"typographyToken":{"token":"typography.body"}, "colorToken":{"token":"color.text"}}}]}]}

    def prepare(self, doc, **kwargs):
        return prepare(doc, self.tokens, self.components, self.bindings, self.icons, file_reference="test-only-file",
            font_bindings={"Noto Sans SC:400":{"fontId":"test-only-font", "fontVariantId":"test-only-regular", "family":"Noto Sans SC", "weight":400, "style":"normal"}}, **kwargs)

    def test_deterministic_independent_adapter_preserves_input(self):
        doc = self.document(); original = deepcopy(doc)
        a, b = self.prepare(doc), self.prepare(doc)
        self.assertEqual(a, b); self.assertEqual(a["status"], "PASS"); self.assertEqual(doc, original)
        self.assertEqual(a["nativeExecution"], "NOT_RUN")
        code = script_for_page(a["plan"])
        self.assertIn("executePenpotAdapter(penpot, payload)", code)
        self.assertNotIn("figma", code.lower())
        self.assertEqual(a["plan"]["platform"], "penpot")

    def test_target_and_font_discovery_required(self):
        r = prepare(self.document(), self.tokens, self.components, self.bindings, self.icons)
        self.assertIsNone(r["plan"]); self.assertIn("missing_target_file", {i["code"] for i in r["issues"]})
        r = prepare(self.document(), self.tokens, self.components, self.bindings, self.icons, file_reference="test-only")
        self.assertIn("missing_font_binding", {i["code"] for i in r["issues"]})

    def test_exact_task009_ir_requires_actual_penpot_bindings(self):
        doc = load_json(ROOT / "examples/adapter-fidelity-acceptance.ui-ir.json"); original = deepcopy(doc)
        # Keep this missing-resource scenario independent of production admission.
        data=load_json(ROOT / "adapters/penpot/metadata/component-bindings.json")
        data['bindings']={}
        empty=ComponentBindings(data,self.components,platform='penpot')
        r=prepare(doc,self.tokens,self.components,empty,self.icons,file_reference='test-only-file')
        codes = {i["code"] for i in r["issues"]}
        self.assertEqual(r["status"], "FAIL"); self.assertIsNone(r["plan"])
        self.assertIn("missing_component_reference", codes); self.assertIn("missing_icon_reference", codes)
        self.assertEqual(doc, original)
        self.assertEqual(import_module("core.component-resolver.registry").digest(doc), "94fa6d9483f78754913cf5089a3c1d70887debdd953edd9f0bd14208e4b155d1")

    def test_figma_fidelity_alone_cannot_admit_penpot_master(self):
        doc = self.document(); doc["pages"][0]["children"] = [{"id":"button", "type":"ComponentInstance",
            "componentId":"action.button.primary.medium", "layout":{"width":{"mode":"fixed", "value":60}, "height":{"mode":"fixed", "value":32}}}]
        data = load_json(ROOT / "adapters/figma/metadata/component-bindings.json")
        data["platform"] = "penpot"
        for entry in data["bindings"].values():
            for binding in entry["variants"].values(): binding["fileReference"] = "test-only-file"
        bindings = ComponentBindings(data, self.components, platform="penpot")
        r = prepare(doc, self.tokens, self.components, bindings, self.icons, file_reference="test-only-file")
        self.assertIn("missing_penpot_fidelity", {i["code"] for i in r["issues"]}); self.assertIsNone(r["plan"])

    def test_grid24_same_exact_span_arithmetic(self):
        doc = self.document(); doc["pages"][0]["layout"]["padding"] = {s:24 for s in ("top","right","bottom","left")}
        doc["pages"][0]["children"] = [{"id":"grid", "type":"Grid", "layout":{"width":{"mode":"fill"}, "gap":16, "gridColumns":24},
            "children":[{"id":f"col{i}", "type":"Column", "layout":{"span":6,"width":{"mode":"fill"}},"children":[]} for i in range(5)]}]
        r = self.prepare(doc); self.assertEqual(r["status"], "PASS")
        cells = r["plan"]["pages"][0]["children"][0]["gridCells"]
        self.assertEqual([c["row"] for c in cells], [0,0,0,0,1])
        self.assertEqual([c["width"] for c in cells], [336]*5)

    def test_wrong_weight_and_unverified_shadow_do_not_fallback(self):
        doc = self.document(); doc["pages"][0]["children"][0]["style"]["typographyToken"] = {"token":"typography.heading"}
        self.assertIn("missing_font_binding", {i["code"] for i in self.prepare(doc)["issues"]})
        doc = self.document(); doc["pages"][0]["style"] = {"shadowToken":{"token":"shadow.card"}}
        self.assertIn("unsupported_shadow", {i["code"] for i in self.prepare(doc)["issues"]})
