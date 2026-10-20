from pathlib import Path
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
        self.assertEqual(report["gates"]["penpotAdapterByteLockNativeReceipt"], "DEFERRED")

    def test_native_png_drift_invalidates_current_report(self):
        source = ROOT / "artifacts/task-106/figma"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "native-read.json").write_bytes((source / "native-read.json").read_bytes())
            (target / "native.png").write_bytes((source / "native.png").read_bytes())
            (target / "native-repeat.png").write_bytes(b"changed")
            report = audit(native_dir=target)
        self.assertEqual(report["status"], "INVALID_EVIDENCE")
        self.assertFalse(report["evidenceValid"])
        self.assertEqual(report["gates"]["figmaAdapterByteLockNativeReceipt"], "INVALID")


if __name__ == "__main__":
    unittest.main()
