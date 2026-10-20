import json
from pathlib import Path
import tempfile
import unittest

from scripts.migrate_compact_search_v026 import TARGET, digest, migrate
from validators.ui_ir import ROOT


class V026MigrationTests(unittest.TestCase):
    def test_new_target_is_created_and_second_run_reuses_unchanged_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            target = Path(directory) / "v026"
            created = migrate(target)
            self.assertEqual(created["action"], "CREATED")
            before = {path.name: digest(path) for path in target.iterdir() if path.is_file()}
            self.assertEqual(before, {path.name: digest(path) for path in TARGET.iterdir() if path.is_file()})
            reused = migrate(target)
            after = {path.name: digest(path) for path in target.iterdir() if path.is_file()}
            self.assertEqual(reused["action"], "REUSED")
            self.assertEqual(before, after)

    def test_modified_target_is_rejected_without_overwrite_even_if_rehashed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            target = Path(directory) / "v026"
            migrate(target)
            content_path = target / "content.json"
            content = json.loads(content_path.read_text(encoding="utf-8"))
            content["mappingSha256"] = "0" * 64
            content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
            manifest_path = target / "input-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["content.json"] = digest(content_path)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            before = digest(content_path), digest(manifest_path)
            with self.assertRaisesRegex(ValueError, "content mapping differs"):
                migrate(target)
            self.assertEqual(before, (digest(content_path), digest(manifest_path)))


if __name__ == "__main__":
    unittest.main()
