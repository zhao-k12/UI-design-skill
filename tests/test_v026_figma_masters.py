import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_v026_figma_masters import audit
from validators.ui_ir import ROOT, load_json


class V026FigmaMastersTests(unittest.TestCase):
    def test_seven_live_masters_match_admitted_catalog(self):
        report = audit()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["componentCount"], 7)
        self.assertFalse(report["releaseReady"])

    def test_fixed_text_tamper_is_rejected(self):
        native = load_json(ROOT / "artifacts/task-111/figma-live-masters.json")
        native["components"]["data.tag.default.enabled"]["texts"][0]["characters"] = "停用"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.json"
            path.write_text(json.dumps(native, ensure_ascii=False), encoding="utf-8")
            report = audit(native_path=path)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("fixed text" in issue for issue in report["issues"]))

    def test_wrong_component_reference_is_rejected(self):
        native = load_json(ROOT / "artifacts/task-111/figma-live-masters.json")
        native["components"]["form.radio.default.enabled"]["id"] = "missing:1"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.json"
            path.write_text(json.dumps(native, ensure_ascii=False), encoding="utf-8")
            report = audit(native_path=path)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("native identity" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
