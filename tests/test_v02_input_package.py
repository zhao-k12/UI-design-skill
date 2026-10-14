"""V0.2 input locks must preserve source geometry and two-platform font evidence."""

import hashlib
import unittest

from scripts.build_v02_acceptance_input import ROOT, TARGET, load


class V02InputPackageTests(unittest.TestCase):
    def test_all_input_and_capture_locks_match_bytes(self):
        manifest = load(TARGET / "input-manifest.json")
        self.assertEqual(manifest["status"], "READY_FOR_PREFLIGHT")
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((TARGET / name).read_bytes()).hexdigest(), expected)
        capture = load(TARGET / "runtime-capture.json")
        for entry in capture["sourceLocks"].values():
            self.assertEqual(hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest(), entry["sha256"])

    def test_composed_measurements_preserve_component_and_text_sources(self):
        capture = {row["uiIrId"]: row for row in load(TARGET / "runtime-capture.json")["evidence"]}
        measurements = load(TARGET / "runtime-measurements.json")["measurements"]
        self.assertEqual((capture["list.count"]["width"], capture["list.count"]["height"]), (73, 22))
        self.assertEqual(capture["list.count"]["provenance"]["kind"], "two-platform-default-font-envelope")
        for name, width, height in (("button.query", 60, 32), ("input.name", 240, 32),
                                    ("select.status", 240, 32), ("table.body", 1392, 144)):
            self.assertEqual((capture[name]["width"], capture[name]["height"]), (width, height))
            self.assertEqual(capture[name]["provenance"]["kind"], "admitted-v02-component-ir")
        for name, size in (("field-name", (328, 62)), ("field-status", (328, 62)),
                           ("scope-content", (328, 52)), ("export-action", (60, 24)),
                           ("user-table", (1392, 192)), ("list-summary", (73, 22))):
            self.assertEqual((measurements[name]["width"], measurements[name]["height"]), size)


if __name__ == "__main__":
    unittest.main()
