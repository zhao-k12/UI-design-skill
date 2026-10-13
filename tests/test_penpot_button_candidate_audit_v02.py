from copy import deepcopy
import unittest

from PIL import Image

from adapters.penpot.button_candidate_audit_v02 import audit


def fixture():
    css = {"font-size": "14px", "line-height": "21px",
           "padding-left": "15px", "padding-right": "15px",
           "padding-top": "0px", "padding-bottom": "0px",
           "border-top-left-radius": "4px", "border-top-width": "1px",
           "background-color": "rgb(45, 140, 240)",
           "border-top-color": "rgb(45, 140, 240)", "color": "rgb(255, 255, 255)"}
    source = {"status": "PASS", "components": [{"componentType": "Button",
              "logicalComponentId": "button", "rootBounds": {"width": 60, "height": 32},
              "content": {"text": "查询"}, "screenshot": {"sha256": "source-hash"},
              "nodes": [{"path": "0", "computedStyle": css},
                        {"path": "0.0", "bounds": {"x": 16, "y": 5.5, "width": 28, "height": 21}}]}]}
    target = {"status": "OBSERVED_IN_REPLACEMENT_FILE", "fileReference": "new-file",
              "pageReference": "page", "candidateCaptureSha256": "capture-hash",
              "defaultFont": {"fontId": "sourcesanspro", "family": "sourcesanspro",
                              "fontVariantId": "regular", "weight": 400},
              "nativeAcceptance": "NOT_RUN", "releaseReady": False}
    capture = {"status": "CAPTURED", "fileId": "new-file", "pageId": "page",
               "nativeAdmission": "NOT_RUN", "releaseReady": False, "validation": [],
               "component": {"id": "component", "isMain": True,
                             "mainBounds": {"width": 60, "height": 32},
                             "fills": [{"fillColor": "#2d8cf0"}],
                             "strokes": [{"strokeColor": "#2d8cf0", "strokeWidth": 1}],
                             "borderRadius": 4,
                             "flex": {"leftPadding": 15, "rightPadding": 15,
                                      "topPadding": 0, "bottomPadding": 0}},
               "label": {"characters": "查询", "fontId": "sourcesanspro",
                         "fontFamily": "sourcesanspro", "fontVariantId": "regular",
                         "fontWeight": "400", "fontSize": "14", "lineHeight": "1.5",
                         "fills": [{"fillColor": "#ffffff"}]},
               "instance": {"isCopy": True, "componentId": "component"},
               "assets": {"colors": [{}, {}],
                          "typography": {"fontId": "sourcesanspro", "fontVariantId": "regular"}}}
    native = Image.new("RGBA", (60, 32), (45, 140, 240, 255))
    return source, target, capture, native, native.copy(), "capture-hash", "native-hash"


class PenpotButtonCandidateAuditTests(unittest.TestCase):
    def test_candidate_passes_checks_without_admission(self):
        inputs = fixture()
        before = deepcopy(inputs[:3])
        report = audit(*inputs)
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["nativeAdmission"], "NOT_RUN")
        self.assertEqual(report["pixelDifferenceCounts"]["nonTextInterior"], 0)
        self.assertEqual(inputs[:3], before)

    def test_wrong_file_or_fake_admission_rejected(self):
        inputs = list(fixture())
        inputs[2]["fileId"] = "old-file"
        with self.assertRaisesRegex(ValueError, "identity"):
            audit(*inputs)
        inputs = list(fixture())
        inputs[2]["nativeAdmission"] = "PASS"
        with self.assertRaisesRegex(ValueError, "admission"):
            audit(*inputs)

    def test_font_content_and_paint_changes_fail(self):
        for section, key, value in (("label", "characters", "错"),
                                    ("label", "fontId", "other"),
                                    ("component", "fills", [{"fillColor": "#000000"}])):
            inputs = list(fixture())
            inputs[2][section][key] = value
            self.assertEqual(audit(*inputs)["status"], "FAIL")

    def test_nontext_pixel_change_fails(self):
        inputs = list(fixture())
        inputs[3].putpixel((10, 16), (0, 0, 0, 255))
        report = audit(*inputs)
        self.assertFalse(report["checks"]["nonTextInteriorPixelsExact"])


if __name__ == "__main__":
    unittest.main()
