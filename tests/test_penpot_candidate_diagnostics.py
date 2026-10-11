"""Synthetic exports test rejection behavior, never platform acceptance."""
import base64
import unittest
from adapters.penpot.candidate_diagnostics import diagnose_candidate


class CandidateDiagnosticsTests(unittest.TestCase):
    def receipts(self, asset="", path="M400,80L428,80L428,101L400,101L400,80"):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg"><style>@font-face{{src:url(https://design.penpot.app/assets/by-id/{asset})}}</style></svg>'
        capture = {"result": {"fileReference": "file", "pageReference": "page", "componentReference": "component",
            "nodes": [{"type": "text", "reference": "text"}], "nativeTextSvgBase64": base64.b64encode(svg.encode()).decode()}}
        outline = {"result": {"fileReference": "file", "pageReference": "page", "textReference": "text",
            "originalEditableTextUnchanged": True,
            "observations": [{"x":400,"y":80,"width":28,"height":21,"d":path}]}}
        return capture, outline

    def test_rectangle_and_empty_font_url_rejected_even_if_host_claims_observed(self):
        capture, outline = self.receipts()
        outline["result"]["status"] = "OBSERVED"
        report = diagnose_candidate(capture, outline)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual({i["code"] for i in report["issues"]}, {"outline_is_text_frame", "native_font_asset_url_incomplete"})
        self.assertFalse(report["admissionEligible"])

    def test_arbitrary_path_and_complete_url_cannot_admit_component(self):
        report = diagnose_candidate(*self.receipts("11111111-1111-1111-1111-111111111111", "M400,80Q410,70,428,80Z"))
        self.assertEqual(report["status"], "REVIEW")
        self.assertFalse(report["requiredProofsComplete"])
        self.assertFalse(report["admissionEligible"])

    def test_wrong_native_text_reference_rejected(self):
        capture, outline = self.receipts()
        outline["result"]["textReference"] = "other"
        self.assertIn("probe_identity_mismatch", {i["code"] for i in diagnose_candidate(capture, outline)["issues"]})
