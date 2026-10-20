import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v02_component_coverage_figma import ROOT, audit


class ComponentCoverageFigmaTests(unittest.TestCase):
    def test_all_eighteen_have_precisely_scoped_figma_evidence(self):
        report = audit()
        self.assertEqual(report["status"], "FIGMA_EVIDENCE_COMPLETE")
        self.assertEqual(report["formalAdmissionTypeCount"], 7)
        self.assertEqual(report["figmaOnlyQaTypeCount"], 11)
        self.assertEqual(report["figmaEvidenceTypeCount"], 18)
        self.assertFalse(report["releaseReady"])
        self.assertEqual(report["issues"], [])

    def test_changed_quality_report_is_rejected(self):
        original = ROOT / "artifacts/task-099/cascader-figma-qa.json"
        changed = json.loads(original.read_text(encoding="utf-8"))
        changed["status"] = "FAIL"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "changed.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            report = audit(qa_overrides={"Cascader": path})
            self.assertEqual(report["status"], "INVALID_EVIDENCE")
            self.assertLess(report["figmaEvidenceTypeCount"], 18)

    def test_changed_repeat_export_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "native-repeat.png"
            path.write_bytes(b"tampered export")
            report = audit(native_overrides={("Cascader", "native-repeat.png"): path})
            self.assertEqual(report["status"], "INVALID_EVIDENCE")
            self.assertIn("Cascader", [issue.get("componentType") for issue in report["issues"]])


if __name__ == "__main__":
    unittest.main()
