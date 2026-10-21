"""The staged flow must not collapse prepared artifacts into native acceptance."""
from copy import deepcopy
from pathlib import Path
import unittest

from workflow_v03.figma import skeleton_script, component_script, fill_script
from workflow_v03.core import fingerprint, prepare
from workflow_v03.qa import (audit_content_tree, audit_skeleton,
                             audit_default_page, audit_filled_content)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "artifacts/task-118/figma-v027-run-final"
SOURCE = ROOT / "examples/user-management-compact-search-v027-figma"
FILE = "0vGWSRoLxBiVPXiZ8xJAX9"


class RevisedFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = prepare(RUN, SOURCE)

    def test_complete_unified_tree_and_colored_cells(self):
        tree = self.bundle["page_content_tree.json"]
        skeleton = self.bundle["annotated_skeleton_page.json"]
        items = [item for section in tree["sections"] for item in section["items"]]
        self.assertEqual(len(items), len(skeleton["cells"]))
        self.assertEqual({item["id"] for item in items},
                         {cell["sourceId"] for cell in skeleton["cells"]})
        self.assertTrue(all(item["layoutPath"] and item["sourceContent"] for item in items))
        self.assertEqual(next(item for item in items if item["id"] == "query-action")
                         ["component"]["defaultContent"]["text"], "查询")
        self.assertTrue(all(cell["color"].startswith("#") and cell["componentType"]
                            for cell in skeleton["cells"]))
        self.assertEqual(self.bundle["page_content_tree_qa.json"]["status"], "NOT_RUN")
        review = {"contentTreeSha256": fingerprint(tree), "sourceFiles": tree["sourceFiles"],
                  "sectionOrder": [section["id"] for section in tree["sections"]],
                  "layoutRelationsStatus": "PASS",
                  "items": [{"sourceId": item["id"], "contentAccuracy": "PASS",
                             "contentCompleteness": "PASS"} for item in items]}
        self.assertEqual(audit_content_tree(tree, review)["status"], "PASS")
        review["items"].pop()
        self.assertEqual(audit_content_tree(tree, review)["status"], "FAIL")

    def test_default_page_and_fill_are_distinct(self):
        default = self.bundle["default_component_page_ui_ir.json"]
        fill = self.bundle["prototype_content_fill.json"]
        self.assertEqual(fill["defaultPageSha256"], fingerprint(default))
        self.assertTrue(fill["targets"])
        self.assertTrue(all(target["expectedDefault"] == "文本" for target in fill["targets"]))
        self.assertFalse(self.bundle["workflow_qa.json"]["deliverable"])
        self.assertEqual(self.bundle["workflow_qa.json"]["prototypeProofread"]["status"], "NOT_RUN")

    def test_native_scripts_respect_stage_gates(self):
        skeleton = self.bundle["annotated_skeleton_page.json"]
        default = self.bundle["default_component_page_ui_ir.json"]
        fill = self.bundle["prototype_content_fill.json"]
        self.assertIn("executeAnnotatedSkeleton", skeleton_script(skeleton, FILE, "r1"))
        with self.assertRaises(ValueError):
            component_script(default, skeleton, FILE, "r1", {})
        skeleton_qa = {"status": "PASS", "skeletonSha256": fingerprint(skeleton),
                       "independentReadback": True, "pageReference": "native-skeleton-page"}
        script, report = component_script(default, skeleton, FILE, "r1", skeleton_qa)
        self.assertEqual(report["status"], "PASS")
        self.assertIn("executeFigmaAdapter", script)
        with self.assertRaises(ValueError):
            fill_script(fill, FILE, {})
        default_qa = {"status": "PASS", "defaultPageSha256": fill["defaultPageSha256"],
                      "independentReadback": True, "pageReference": "native-default-page",
                      "nodeMap": {target["uiIrId"]: "n" + str(index)
                                  for index, target in enumerate(fill["targets"])} }
        self.assertIn("fillPrototypeContent", fill_script(fill, FILE, default_qa))
        bad = deepcopy(default_qa)
        bad["defaultPageSha256"] = "changed"
        with self.assertRaises(ValueError):
            fill_script(fill, FILE, bad)

    def test_skeleton_readback_rejects_wrong_component_color(self):
        skeleton = self.bundle["annotated_skeleton_page.json"]
        receipt = {"status": "EXECUTED", "stage": "annotated-skeleton-page",
                   "pageReference": "page-1", "rootReference": "root-1"}
        readback = {"independent": True, "pageReference": "page-1", "rootReference": "root-1",
                    "cells": deepcopy(skeleton["cells"])}
        review = {"skeletonSha256": fingerprint(skeleton),
                  "cells": [{"cellId": cell["cellId"], "componentChoice": "PASS",
                             "placement": "PASS", "spacing": "PASS", "completeness": "PASS"}
                            for cell in skeleton["cells"]]}
        self.assertEqual(audit_skeleton(skeleton, receipt, readback, review)["status"], "PASS")
        readback["cells"][0]["color"] = "#000000"
        self.assertEqual(audit_skeleton(skeleton, receipt, readback, review)["status"], "FAIL")

    def test_default_page_and_fill_need_separate_native_evidence(self):
        document = self.bundle["default_component_page_ui_ir.json"]
        fill = self.bundle["prototype_content_fill.json"]
        nodes = []
        def visit(node):
            if node["type"] == "Text":
                nodes.append({"uiIrId": node["id"], "nodeId": "native-" + node["id"],
                              "type": "TEXT", "characters": node["text"]})
            elif node["type"] in ("ComponentInstance", "IconInstance"):
                nodes.append({"uiIrId": node["id"], "nodeId": "native-" + node["id"],
                              "type": "INSTANCE", "mainComponentReference": "master"})
            for child in node.get("children", []):
                visit(child)
        for page in document["pages"]:
            visit(page)
        receipt = {"status": "PASS", "pageReference": "default-page",
                   "nodeMap": {row["uiIrId"]: row["nodeId"] for row in nodes}}
        readback = {"independent": True, "pageReference": "default-page",
                    "skeletonPageReference": "skeleton-page", "nodes": nodes}
        skeleton_qa = {"status": "PASS", "pageReference": "skeleton-page"}
        qa = audit_default_page(document, skeleton_qa, receipt, readback)
        self.assertEqual(qa["status"], "PASS", qa["issues"])
        readback["skeletonPageReference"] = "missing"
        self.assertEqual(audit_default_page(document, skeleton_qa, receipt, readback)["status"], "FAIL")
        filled = {"independent": True, "pageReference": "default-page", "instancesIntact": True,
                  "texts": [{"uiIrId": row["uiIrId"],
                             "nodeId": qa["nodeMap"][row["uiIrId"]], "characters": row["text"]}
                            for row in fill["targets"]]}
        execution = {"status": "EXECUTED", "stage": "prototype-content-fill"}
        self.assertEqual(audit_filled_content(fill, qa, execution, filled)["status"], "PASS")
        filled["instancesIntact"] = False
        self.assertEqual(audit_filled_content(fill, qa, execution, filled)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
