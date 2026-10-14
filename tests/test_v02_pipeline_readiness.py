"""Migration audit must expose real blockers without modifying frozen inputs."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v02_readiness", ROOT / "scripts/audit_v02_pipeline_readiness.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class V02PipelineReadinessTests(unittest.TestCase):
    def test_current_target_has_explicit_migration_blockers(self):
        report = module.audit()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual([item["code"] for item in report["blockers"]], [
            "legacy_input_lock", "source_geometry_mismatch",
            "text_measurements_need_rebind"])
        self.assertEqual(report["nativeExecution"], "NOT_RUN")
        self.assertEqual(report, module.audit())

    def test_icon_blocker_rejects_deleted_target_file(self):
        old_target = "91396aad-60c8-808b-8008-c0885ca79899"
        report = module.audit(penpot_file=old_target)
        self.assertIn("penpot_icon_target_mismatch", [item["code"] for item in report["blockers"]])
        self.assertEqual(report["status"], "BLOCKED")

    def test_explicit_admitted_geometry_removes_only_geometry_blocker(self):
        path = ROOT / "examples/acceptance-prototype-v02/source-geometry.json"
        report = module.audit(geometry_path=path)
        self.assertEqual(report["geometry"], "examples/acceptance-prototype-v02/source-geometry.json")
        self.assertEqual([item["code"] for item in report["blockers"]], [
            "legacy_input_lock",
            "text_measurements_need_rebind"])


if __name__ == "__main__":
    unittest.main()
