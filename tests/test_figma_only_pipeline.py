"""The active Figma workflow never needs a Penpot target or preflight."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from adapters.byte_lock import verify_platform
from scripts.prepare_adapter_execution import prepare as prepare_execution
from scripts.run_figma_pipeline import run
from validators.ui_ir import ROOT, load_json


class FigmaOnlyPipelineTests(unittest.TestCase):
    def test_current_input_runs_with_only_figma_and_rejects_lock_drift(self):
        source = ROOT / "examples/user-management-compact-search-v026"
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            output = Path(directory) / "run"
            qa = run(source, output, "0vGWSRoLxBiVPXiZ8xJAX9")
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["developmentScope"], "FIGMA_ONLY")
            self.assertEqual(qa["adapterPreflights"], {"figma": "PASS"})
            self.assertTrue(qa["readyForAdapter"])
            self.assertFalse((output / "penpot_preflight.json").exists())
            lock = load_json(output / "adapter-execution-lock.json")
            self.assertEqual(set(lock["platforms"]), {"figma"})
            self.assertTrue(verify_platform(
                lock, "figma", load_json(output / "figma_preflight.json")["plan"]))
            intent = prepare_execution(output, "figma", Path(directory) / "execution")
            self.assertEqual(intent["status"], "READY_TO_EXECUTE")
            self.assertEqual(run(source, output, "0vGWSRoLxBiVPXiZ8xJAX9")["status"], "PASS")
            altered = deepcopy(lock)
            altered["platforms"]["figma"]["planSha256"] = "0" * 64
            (output / "adapter-execution-lock.json").write_text(
                json.dumps(altered), encoding="utf-8")
            rejected = run(source, output, "0vGWSRoLxBiVPXiZ8xJAX9")
            self.assertEqual(rejected["status"], "MIGRATION_REQUIRED")
            self.assertFalse(rejected["readyForAdapter"])

    def test_prior_input_cannot_be_silently_used_with_current_profile(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            with self.assertRaisesRegex(ValueError, "Input versions do not match"):
                run(ROOT / "examples/acceptance-prototype", Path(directory) / "run",
                    "0vGWSRoLxBiVPXiZ8xJAX9")


if __name__ == "__main__":
    unittest.main()
