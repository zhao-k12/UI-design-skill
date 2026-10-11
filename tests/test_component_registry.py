from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import ValidationError
from adapters.component_bindings import BindingError, ComponentBindings
from validators.ui_ir import ROOT, load_json

logical = import_module("core.component-resolver.registry")


def fixture():
    component_id = "form.input.default.medium"
    report = {"scope": "test-fixture", "status": "PASS", "logicalComponentId": component_id, "componentType": "Input", "variants": ["default"], "sourceVersion": "fixture-source-v1", "componentIrSha256": "1" * 64}
    data = {"registryVersion": "0.1.0", "libraryVersion": "fixture-library-v1", "sourceVersion": "fixture-source-v1", "scope": "test-fixture", "components": {component_id: {"componentType": "Input", "tier": "base", "status": "active", "variants": ["default"], "defaultVariant": "default", "slots": ["leading-icon", "trailing-icon"], "fidelity": {"reportId": "fixture.report", "reportSha256": logical.digest(report), "componentIrSha256": "1" * 64}}}}
    return data, {"fixture.report": report}


def bindings(registry, platform):
    component_id = "form.input.default.medium"
    return {"metadataVersion": "0.1.0", "platform": platform, "scope": "test-fixture", "libraryVersion": registry.library_version, "sourceVersion": registry.source_version, "registrySha256": registry.fingerprint, "bindings": {component_id: {"variants": {"default": {"kind": "component", "fileReference": platform + ".fixture.file", "componentReference": platform + ".fixture.component", "fidelityReportSha256": registry.inspect(component_id)["fidelity"]["reportSha256"]}}}}}


class ComponentRegistryTests(unittest.TestCase):
    def active_fixture(self):
        data, reports = fixture()
        return logical.ComponentRegistry(data, reports, allow_test_fixtures=True)

    def test_catalog_covers_nine_required_types_without_faking_admission(self):
        registry = logical.ComponentRegistry(load_json(ROOT / "registries/components/catalog.json"),load_json(ROOT/'registries/components/fidelity-reports.json'))
        self.assertEqual({entry["componentType"] for entry in registry.snapshot["components"].values()}, {"Button", "Input", "Select", "DatePicker", "Table", "FormItem", "Pagination", "Card", "Tabs"})
        self.assertEqual({id for id,entry in registry.snapshot['components'].items() if entry['status']=='active'}, {'action.button.primary.medium','form.input.default.medium','form.select.default.medium','data.table.default'})
        with self.assertRaises(logical.ComponentError) as caught:
            registry.resolve("form.date-picker.default.medium")
        self.assertEqual(caught.exception.code, "component_not_ready")

    def test_test_catalog_is_rejected_by_default(self):
        data, reports = fixture()
        with self.assertRaises(logical.ComponentError) as caught:
            logical.ComponentRegistry(data, reports)
        self.assertEqual(caught.exception.code, "test_fixture_forbidden")

    def test_same_logical_fixture_resolves_through_two_isolated_metadata_files(self):
        registry = self.active_fixture()
        results = {}
        for platform in ("figma", "penpot"):
            metadata = bindings(registry, platform)
            resolver = ComponentBindings(metadata, registry, platform=platform, allow_test_fixtures=True)
            results[platform] = resolver.resolve("form.input.default.medium")
        self.assertEqual(results["figma"]["componentReference"], "figma.fixture.component")
        self.assertEqual(results["penpot"]["componentReference"], "penpot.fixture.component")
        self.assertNotEqual(results["figma"], results["penpot"])
        self.assertNotIn("componentReference", registry.resolve("form.input.default.medium"))

    def test_active_entries_require_loaded_passing_evidence(self):
        data, reports = fixture()
        with self.assertRaises(logical.ComponentError) as caught:
            logical.ComponentRegistry(data, {}, allow_test_fixtures=True)
        self.assertEqual(caught.exception.code, "missing_fidelity_evidence")
        for status in ("FAIL", "WARNING"):
            altered = deepcopy(reports)
            altered["fixture.report"]["status"] = status
            data["components"]["form.input.default.medium"]["fidelity"]["reportSha256"] = logical.digest(altered["fixture.report"])
            with self.assertRaises(logical.ComponentError) as caught:
                logical.ComponentRegistry(data, altered, allow_test_fixtures=True)
            self.assertEqual(caught.exception.code, "fidelity_not_passed")

    def test_evidence_cannot_target_another_component_or_ir(self):
        for key, value in (("logicalComponentId", "form.select.default.medium"), ("componentIrSha256", "2" * 64)):
            data, reports = fixture()
            reports["fixture.report"][key] = value
            data["components"]["form.input.default.medium"]["fidelity"]["reportSha256"] = logical.digest(reports["fixture.report"])
            with self.assertRaises(logical.ComponentError) as caught:
                logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
            self.assertEqual(caught.exception.code, "fidelity_not_passed")

    def test_fidelity_must_cover_all_declared_variants_and_component_type(self):
        for key, value in (("componentType", "Select"), ("variants", ["another"])):
            data, reports = fixture()
            reports["fixture.report"][key] = value
            data["components"]["form.input.default.medium"]["fidelity"]["reportSha256"] = logical.digest(reports["fixture.report"])
            with self.assertRaises(logical.ComponentError) as caught:
                logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
            self.assertEqual(caught.exception.code, "fidelity_variant_mismatch")

    def test_evidence_hash_source_and_scope_are_checked(self):
        for field, value, code in (("status", "FAIL", "fidelity_evidence_mismatch"), ("sourceVersion", "other", "fidelity_source_mismatch"), ("scope", "production", "fidelity_source_mismatch")):
            data, reports = fixture()
            reports["fixture.report"][field] = value
            if code != "fidelity_evidence_mismatch":
                data["components"]["form.input.default.medium"]["fidelity"]["reportSha256"] = logical.digest(reports["fixture.report"])
            with self.assertRaises(logical.ComponentError) as caught:
                logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
            self.assertEqual(caught.exception.code, code)

    def test_missing_and_invalid_variants_are_explicit(self):
        registry = self.active_fixture()
        for component_id, variant, code in (("missing.component", None, "missing_component"), ("form.input.default.medium", "unknown", "invalid_component_variant")):
            with self.assertRaises(logical.ComponentError) as caught:
                registry.resolve(component_id, variant)
            self.assertEqual(caught.exception.code, code)
        data, reports = fixture()
        data["components"]["form.input.default.medium"]["defaultVariant"] = "unknown"
        with self.assertRaises(logical.ComponentError) as caught:
            logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
        self.assertEqual(caught.exception.code, "invalid_component_variant")

    def test_core_catalog_rejects_platform_fields(self):
        data, reports = fixture()
        data["components"]["form.input.default.medium"]["figmaNodeId"] = "fake"
        with self.assertRaises(ValidationError):
            logical.ComponentRegistry(data, reports, allow_test_fixtures=True)

    def test_bindings_check_snapshot_platform_scope_and_fidelity(self):
        registry = self.active_fixture()
        for field, value, code in (("platform", "penpot", "platform_mismatch"), ("registrySha256", "0" * 64, "binding_version_mismatch"), ("libraryVersion", "different", "binding_version_mismatch"), ("sourceVersion", "different", "binding_version_mismatch"), ("scope", "production", "binding_scope_mismatch")):
            metadata = bindings(registry, "figma")
            metadata[field] = value
            with self.assertRaises(BindingError) as caught:
                ComponentBindings(metadata, registry, platform="figma", allow_test_fixtures=True)
            self.assertEqual(caught.exception.code, code)
        metadata = bindings(registry, "figma")
        metadata["bindings"]["form.input.default.medium"]["variants"]["default"]["fidelityReportSha256"] = "0" * 64
        with self.assertRaises(BindingError) as caught:
            ComponentBindings(metadata, registry, platform="figma", allow_test_fixtures=True)
        self.assertEqual(caught.exception.code, "binding_fidelity_mismatch")

    def test_bindings_reject_noncomponent_and_missing_reference(self):
        registry = self.active_fixture()
        metadata = bindings(registry, "figma")
        metadata["bindings"]["form.input.default.medium"]["variants"]["default"]["kind"] = "rectangle"
        with self.assertRaises(ValidationError):
            ComponentBindings(metadata, registry, platform="figma", allow_test_fixtures=True)
        metadata = bindings(registry, "figma")
        metadata["bindings"] = {}
        resolver = ComponentBindings(metadata, registry, platform="figma", allow_test_fixtures=True)
        with self.assertRaises(BindingError) as caught:
            resolver.resolve("form.input.default.medium")
        self.assertEqual(caught.exception.code, "missing_component_reference")

    def test_sources_snapshots_and_returned_references_are_isolated(self):
        data, reports = fixture()
        registry = logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
        metadata = bindings(registry, "figma")
        resolver = ComponentBindings(metadata, registry, platform="figma", allow_test_fixtures=True)
        data["components"].clear()
        reports.clear()
        registry.snapshot["components"].clear()
        metadata["bindings"].clear()
        resolver.resolve("form.input.default.medium")["componentReference"] = "changed"
        self.assertEqual(resolver.resolve("form.input.default.medium")["componentReference"], "figma.fixture.component")

    def test_deprecated_component_is_retained_but_not_newly_resolved(self):
        data, reports = fixture()
        data["components"]["form.input.default.medium"]["status"] = "deprecated"
        registry = logical.ComponentRegistry(data, reports, allow_test_fixtures=True)
        self.assertEqual(registry.inspect("form.input.default.medium")["status"], "deprecated")
        with self.assertRaises(logical.ComponentError) as caught:
            registry.resolve("form.input.default.medium")
        self.assertEqual(caught.exception.code, "deprecated_component")

    def test_cli_reports_contract_pass_and_rejects_fixture_promotion(self):
        command = [sys.executable, "-X", "utf8", "-m", "validators.component"]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "qa.json"
            result = subprocess.run(command + ["--report", str(report_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = load_json(report_path)
            self.assertEqual(report, json.loads(result.stdout))
            self.assertEqual(report["activeComponents"], 4)
            self.assertEqual(report["liveDualPlatformAcceptance"], "DEFERRED")
            data, _ = fixture()
            catalog = Path(directory) / "test-catalog.json"
            catalog.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(command + ["--catalog", str(catalog)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["issues"][0]["code"], "test_fixture_forbidden")


if __name__ == "__main__":
    unittest.main()
