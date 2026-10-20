from pathlib import Path
import json
import tempfile
import unittest

from scripts.audit_v02_current_readiness import ROOT, audit


class V02CurrentReadinessTests(unittest.TestCase):
    def test_current_evidence_still_fails_full_release_gate(self):
        report = audit()
        self.assertEqual(report["status"], "NOT_READY")
        self.assertTrue(report["evidenceValid"])
        self.assertFalse(report["releaseReady"])
        self.assertEqual(report["componentCoverage"]["formallyAdmittedTypeCount"], 7)
        self.assertEqual(report["componentCoverage"]["figmaOnlyQaTypeCount"], 11)
        self.assertEqual(report["gates"]["figmaAdapterByteLockNativeReceipt"], "PASS")
        self.assertEqual(report["gates"]["sevenAdmittedFigmaMasters"], "PASS")
        self.assertEqual(report["gates"]["penpotAdapterByteLockNativeReceipt"], "DEFERRED")
        self.assertEqual(report["gates"]["newIndependentPrototypeFigmaE2E"], "PASS")
        self.assertEqual(report["gates"]["newIndependentPrototypePenpotE2E"], "DEFERRED")
        self.assertEqual(report["gates"]["figmaScopedReleaseGates"], "PASS")

    def test_native_png_drift_invalidates_current_report(self):
        source = ROOT / "artifacts/task-110/figma"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "native-read.json").write_bytes((source / "native-read.json").read_bytes())
            (target / "native.png").write_bytes((source / "native.png").read_bytes())
            (target / "native-repeat.png").write_bytes(b"changed")
            report = audit(native_dir=target)
        self.assertEqual(report["status"], "INVALID_EVIDENCE")
        self.assertFalse(report["evidenceValid"])
        self.assertEqual(report["gates"]["figmaAdapterByteLockNativeReceipt"], "INVALID")

    def test_drifted_component_master_invalidates_current_report(self):
        source = ROOT / "artifacts/task-111/figma-live-masters.json"
        native = json.loads(source.read_text(encoding="utf-8"))
        native["components"]["data.tag.default.enabled"]["texts"][0]["characters"] = "停用"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figma-live-masters.json"
            path.write_text(json.dumps(native, ensure_ascii=False), encoding="utf-8")
            report = audit(figma_master_path=path)
        self.assertEqual(report["status"], "INVALID_EVIDENCE")
        self.assertEqual(report["gates"]["sevenAdmittedFigmaMasters"], "INVALID")


if __name__ == "__main__":
    unittest.main()
