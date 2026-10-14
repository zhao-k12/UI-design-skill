import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_v02_release_readiness import ROOT, audit


class V02ReleaseReadinessTests(unittest.TestCase):
    def test_scoped_native_pass_does_not_claim_full_release(self):
        report = audit()
        self.assertTrue(report["evidenceValid"])
        self.assertEqual(report["status"], "NOT_READY")
        self.assertFalse(report["releaseReady"])
        self.assertEqual(report["componentCoverage"]["admittedTypeCount"], 4)
        self.assertEqual(len(report["componentCoverage"]["missingTypes"]), 14)
        self.assertEqual(report["gates"]["adapterRuntimeByteLock"], "NOT_IMPLEMENTED")

    def test_modified_native_png_digest_invalidates_evidence(self):
        source = ROOT / "artifacts/task-052/native-qa.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "native-qa.json"
            data = json.loads(source.read_text(encoding="utf-8"))
            data["counts"]["penpot"]["nativePngSha256"] = "0" * 64
            target.write_text(json.dumps(data), encoding="utf-8")
            report = audit(native_qa_path=target)
        self.assertEqual(report["status"], "INVALID_EVIDENCE")
        self.assertFalse(report["releaseReady"])
        self.assertIn("native_png_hash_mismatch", [issue["code"] for issue in report["issues"]])

    def test_malformed_native_report_fails_closed(self):
        source = ROOT / "artifacts/task-052/native-qa.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "native-qa.json"
            data = json.loads(source.read_text(encoding="utf-8"))
            del data["counts"]
            target.write_text(json.dumps(data), encoding="utf-8")
            report = audit(native_qa_path=target)
        self.assertEqual(report["status"], "INVALID_EVIDENCE")
        self.assertFalse(report["releaseReady"])


if __name__ == "__main__":
    unittest.main()
