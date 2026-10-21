"""The skill must reject prototype-shaped geometry even when Core layout passes."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import tempfile
import unittest

from core.layout.builder import generate
from validators.ui_ir import load_json
from workflow_v03.core import fingerprint
from workflow_v03.layout_quality import audit
from workflow_v03.core import write
from scripts.run_revised_figma_stages import advance

token_module = import_module("core.design-rules.tokens")


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/workflow-v03-smoke-figma"
RUN = ROOT / "artifacts/task-122/core-run"
STAGED = ROOT / "artifacts/task-122/staged-r2"


class LayoutQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read = load_json
        cls.tree = read(STAGED / "page_content_tree.json")
        cls.plan = read(SOURCE / "layout-plan.json")
        cls.layout_tree = read(RUN / "layout_tree.json")
        cls.layout_report = read(RUN / "layout_qa_report.json")
        cls.tokens = read(ROOT / "registries/tokens/v0.2.2/default.json")
        cls.catalog = read(ROOT / "registries/components/v0.2.7/catalog.json")
        cls.rule = read(ROOT / "registries/design-standards/list-page-layout-v0.3.2.json")

    def intent(self):
        return {"version": "0.3.2", "sourcePageTreeSha256": self.tree["sourcePageTreeSha256"],
                "ruleSha256": fingerprint(self.rule), "pattern": "list-page",
                "geometryPolicy": "prototype-geometry-nonbinding",
                "sections": {section_id: {"paddingToken": "spacing.md",
                                          "basis": "project-page-rule", "rationale": "Consistent content inset"}
                             for section_id in ("header", "query", "list")},
                "tableSizing": {"user-table": {"policy": "fill-section-content",
                                               "basis": "project-page-rule",
                                               "rationale": "Use the list content width"}}}

    def check(self, plan=None, layout_tree=None, layout_report=None, catalog=None, intent=None, tree=None):
        return audit(tree or self.tree, plan or self.plan, layout_tree or self.layout_tree,
                     layout_report or self.layout_report, catalog or self.catalog,
                     self.tokens, self.rule, intent or self.intent())

    def test_old_accepted_page_fails_normative_layout(self):
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("section_padding_rule_mismatch", codes)
        self.assertIn("table_component_width_capability_mismatch", codes)
        self.assertIn("table_cell_not_fill_content", codes)

    def test_new_layout_requires_both_fill_cell_and_admitted_width(self):
        plan = deepcopy(self.plan)
        inset = {edge: {"token": "spacing.md"} for edge in ("top", "right", "bottom", "left")}
        plan["sectionConfigs"]["header"] = {"padding": inset}
        plan["sectionConfigs"]["list"]["padding"] = inset
        plan["measurements"]["user-table"]["width"] = 1840
        layout_tree, report = generate(
            load_json(RUN / "prototype_analysis.json"), load_json(RUN / "page_tree.json"),
            SOURCE, load_json(SOURCE / "review.json"), plan,
            token_module.TokenRegistry(self.tokens))
        self.assertEqual(report["status"], "PASS", report.get("issues"))
        catalog = deepcopy(self.catalog)
        catalog["components"]["data.table.default"]["contentScope"]["width"] = 1840
        tree = deepcopy(self.tree)
        for section in tree["sections"]:
            for item in section["items"]:
                if item["id"] == "user-table":
                    item["component"]["defaultContent"]["width"] = 1840
        result = self.check(plan, layout_tree, report, catalog, tree=tree)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertIn("table_component_width_capability_mismatch",
                      {issue["code"] for issue in self.check(plan, layout_tree, report)["issues"]})

    def test_self_declared_pass_cannot_override_project_rule(self):
        decision = self.intent()
        decision["sections"]["list"]["paddingToken"] = "spacing.none"
        self.assertIn("section_layout_intent_missing",
                      {issue["code"] for issue in self.check(intent=decision)["issues"]})

    def test_stage_blocks_native_skeleton_when_layout_quality_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temporary:
            staged = Path(temporary)
            for name in ("page_content_tree.json", "page_content_tree_review.json"):
                (staged / name).write_bytes((STAGED / name).read_bytes())
            write(staged / "intent.json", self.intent())
            write(staged / "iview_conformance_qa.json", {"status": "PASS"})
            result = advance(staged, "layout-qa", intent=staged / "intent.json",
                             plan=SOURCE / "layout-plan.json",
                             layout_tree=RUN / "layout_tree.json",
                             layout_report=RUN / "layout_qa_report.json",
                             tokens=ROOT / "registries/tokens/v0.2.2/default.json",
                             catalog=ROOT / "registries/components/v0.2.7/catalog.json")
            self.assertEqual(result["status"], "FAIL")
            with self.assertRaisesRegex(ValueError, "Normative layout intent"):
                advance(staged, "skeleton-script", file_reference="file", revision="r1")


if __name__ == "__main__":
    unittest.main()
