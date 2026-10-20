import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_v02_compact_search_figma import ROOT, audit


class V02CompactSearchFigmaTests(unittest.TestCase):
    def test_independent_prototype_and_native_layout_pass(self):
        result = audit()
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["nativeInstanceCount"], 5)
        self.assertFalse(result["releaseReady"])

    def test_right_alignment_readback_drift_fails(self):
        source = ROOT / "artifacts/task-108/figma"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ("native-read.json", "native.png", "native-repeat.png", "layout-read.json"):
                shutil.copy2(source / name, target / name)
            path = target / "layout-read.json"
            rows = json.loads(path.read_text(encoding="utf-8"))
            next(row for row in rows if row["name"] == "layout.item.1.2.instance")["x"] -= 12
            path.write_text(json.dumps(rows), encoding="utf-8")
            result = audit(native_dir=target)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("native_compact_query_layout_mismatch", result["issues"])


if __name__ == "__main__":
    unittest.main()
