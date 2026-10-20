from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.run_pipeline import profile_resources
from validators.ui_ir import ROOT, load_json


class V026ProfileTests(unittest.TestCase):
    def test_seven_component_profile_is_versioned_and_bound(self):
        old, new = profile_resources("v0.2"), profile_resources("v0.2.6")
        self.assertNotEqual(old["components"], new["components"])
        self.assertNotEqual(old["componentBindings"], new["componentBindings"])
        self.assertEqual(load_json(ROOT / new["components"])["registryVersion"], "0.2.6")
        catalog = load_json(ROOT / new["components"])
        self.assertEqual(len(catalog["components"]), 7)
        for platform in ("figma", "penpot"):
            bindings = load_json(ROOT / "adapters" / platform / "metadata" / new["componentBindings"])
            self.assertEqual(set(bindings["bindings"]), set(catalog["components"]))
            self.assertEqual(bindings["registrySha256"],
                             load_json(ROOT / "registries/components/v0.2.6/admission.json")["registrySha256"])
        source = ROOT / "examples/user-management-compact-search-v026"
        manifest = load_json(source / "input-manifest.json")
        self.assertEqual(manifest["sourcePackage"], "examples/user-management-compact-search")
        self.assertEqual(manifest["status"], "READY_FOR_PREFLIGHT")

    def test_old_input_is_rejected_and_migrated_input_runs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            def run(source, name):
                return subprocess.run([sys.executable, "scripts/run_pipeline.py", str(source),
                    "--output-dir", str(Path(directory) / name),
                    "--figma-file", "0vGWSRoLxBiVPXiZ8xJAX9",
                    "--penpot-file", "57949053-620f-8001-8008-c804c8d61529",
                    "--profile", "v0.2.6"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            old = run(ROOT / "examples/user-management-compact-search", "old")
            self.assertNotEqual(old.returncode, 0)
            self.assertIn("Input versions do not match", old.stderr)
            migrated = run(ROOT / "examples/user-management-compact-search-v026", "migrated")
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
            output = Path(directory) / "migrated"
            qa = load_json(output / "qa_report.json")
            self.assertEqual(qa["adapterPreflights"], {"figma": "PASS", "penpot": "PASS"})
            self.assertEqual(len(load_json(output / "adapter-execution-lock.json")["platforms"]), 2)
            self.assertEqual(load_json(output / "manifest.json")["versions"]["component_library_version"],
                             load_json(ROOT / profile_resources("v0.2.6")["components"])["libraryVersion"])


if __name__ == "__main__":
    unittest.main()
