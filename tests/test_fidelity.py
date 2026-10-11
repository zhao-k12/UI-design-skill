from copy import deepcopy
from importlib import import_module
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from validators.visual.fidelity import compare, digest, file_hash, measurement
from tests.test_component_registry import fixture


class FidelityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name) / "reference.png"
        self.b = Path(self.tmp.name) / "candidate.png"
        Image.new("RGBA", (10, 10), "white").save(self.a)
        Image.new("RGBA", (10, 10), "white").save(self.b)
        self.ref = {"logicalComponentId": "form.input.default.medium", "componentType": "Input", "variant": "default",
                    "state": "default-static", "props": {}, "content": {}, "fixtureContext": {},
                    "provenance": {"sourceVersion": "fixture-source-v1"}, "environment": {"deviceScaleFactor": 1},
                    "rootBounds": {"width": 10, "height": 10},
                    "nodes": [{"path": "0", "visible": True, "bounds": {"x": 0, "y": 0, "width": 10, "height": 10},
                               "computedStyle": {"padding-left": "1px", "background-color": "white", "font-size": "14px"},
                               "textRuns": [{"text": "A", "bounds": {"x": 2, "y": 2, "width": 5, "height": 5}}]}]}
        self.candidate = {k: deepcopy(self.ref[k]) for k in ("logicalComponentId", "variant", "state", "props", "content", "fixtureContext")}
        self.candidate.update(scope="test-fixture", evidenceKind="native-design-capture", sourceVersion="fixture-source-v1",
                              capture={"captureId": "fixture-independent", "exporterVersion": "fixture-v1", "nativeEvidenceSha256": "2" * 64},
                              measurements=measurement(self.ref), rasterContext={"deviceScaleFactor": 1, "background": "white"},
                              screenshotSha256=file_hash(self.b))

    def compare(self):
        return compare(self.ref, self.candidate, self.a, self.b, scope="test-fixture")

    def pixel(self, xy, color):
        with Image.open(self.b) as image:
            image.putpixel(xy, color)
            image.save(self.b)
        self.candidate["screenshotSha256"] = file_hash(self.b)

    def test_independent_exact_fixture_pass_is_not_production_eligible(self):
        report = self.compare()
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["admissionEligible"])

    def test_missing_candidate_warning(self):
        report = compare(self.ref, None, self.a, None)
        self.assertEqual(report["status"], "WARNING")
        self.assertFalse(report["admissionEligible"])

    def test_geometry_and_style_changes_fail_even_with_identical_pixels(self):
        for kind in ("bounds", "computedStyle"):
            with self.subTest(kind=kind):
                candidate = deepcopy(self.candidate)
                candidate["measurements"]["nodes"][0][kind].update({"width": 10.001} if kind == "bounds" else {"padding-left": "2px"})
                self.assertEqual(compare(self.ref, candidate, self.a, self.b, scope="test-fixture")["status"], "FAIL")

    def test_nontext_and_large_text_pixel_differences_fail(self):
        for xy in ((0, 0), (3, 3)):
            self.pixel(xy, (0, 0, 0, 255))
            self.assertEqual(self.compare()["status"], "FAIL")

    def test_minor_text_antialiasing_is_review_not_admission(self):
        self.pixel((3, 3), (250, 250, 250, 255))
        report = self.compare()
        self.assertEqual(report["status"], "WARNING")
        self.assertEqual(report["issues"][0]["code"], "text_antialiasing_review")

    def test_reference_self_comparison_and_reference_exports_rejected(self):
        self.assertEqual(compare(self.ref, self.candidate, self.a, self.a, scope="test-fixture")["status"], "FAIL")
        self.candidate["evidenceKind"] = "official-runtime"
        self.assertEqual(self.compare()["status"], "FAIL")

    def test_missing_or_altered_png_never_passes(self):
        self.candidate["screenshotSha256"] = "0" * 64
        self.assertEqual(self.compare()["status"], "FAIL")
        self.b.unlink()
        self.assertEqual(self.compare()["status"], "WARNING")

    def test_size_scale_context_and_scope_not_silently_normalized(self):
        Image.new("RGB", (11, 10), "white").save(self.b)
        self.candidate["screenshotSha256"] = file_hash(self.b)
        self.assertEqual(self.compare()["status"], "FAIL")
        self.assertEqual(compare(self.ref, self.candidate, self.a, self.b)["status"], "FAIL")

    def test_minimal_handwritten_pass_cannot_activate_production(self):
        logical = import_module("core.component-resolver.registry")
        data, evidence = fixture()
        data["scope"] = "production"
        report = evidence["fixture.report"]
        report["scope"] = "production"
        data["components"][self.ref["logicalComponentId"]]["fidelity"]["reportSha256"] = digest(report)
        with self.assertRaises(logical.ComponentError) as caught:
            logical.ComponentRegistry(data, evidence)
        self.assertEqual(caught.exception.code, "invalid_fidelity_gate_report")

    def test_malformed_candidate_explicit_failure(self):
        self.assertEqual(compare(self.ref, [], self.a, self.b)["status"], "FAIL")
