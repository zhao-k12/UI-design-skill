import base64
from copy import deepcopy
from io import BytesIO
import unittest

from PIL import Image

from adapters.figma.button_candidate_audit_v02 import inspect


def fixture():
    img = Image.new("RGBA", (60, 32), (45, 140, 240, 255))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    css = {"font-weight": "400", "font-size": "14px", "line-height": "21px",
           "padding-left": "15px", "padding-right": "15px", "padding-top": "0px", "padding-bottom": "0px",
           "border-top-left-radius": "4px", "border-top-width": "1px",
           "background-color": "rgb(45, 140, 240)", "border-top-color": "rgb(45, 140, 240)",
           "color": "rgb(255, 255, 255)"}
    source = {"status": "PASS", "components": [{"componentType": "Button", "logicalComponentId": "button",
              "rootBounds": {"width": 60, "height": 32}, "content": {"text": "查询"},
              "screenshot": {"sha256": "source-hash"},
              "nodes": [{"path": "0", "computedStyle": css},
                        {"path": "0.0", "bounds": {"x": 16, "y": 5.5, "width": 28, "height": 21}}]}]}
    font = {"platform": "figma", "status": "PASS", "nativeAcceptance": "NOT_RUN",
            "readyForPageGeneration": False, "releaseReady": False,
            "fileReference": "file", "defaultFont": {"family": "Inter"},
            "bindings": {"Inter:400": {"style": "Regular"}}}
    creation = {"status": "CANDIDATE", "componentId": "component", "pageReference": "page",
                "fileReference": "file", "nativeAcceptance": "NOT_RUN", "releaseReady": False,
                "labelPropertyKey": "Label#1"}
    color = lambda r, g, b: {"type": "SOLID", "color": {"r": r/255, "g": g/255, "b": b/255}}
    capture = {"status": "CAPTURED", "componentId": "component", "pageReference": "page",
               "fileReference": "file", "nativeAcceptance": "NOT_RUN", "releaseReady": False,
               "instanceMainComponentId": "component", "componentName": "V0.2/Button/Primary/Medium/Default",
               "componentLayout": "HORIZONTAL", "componentBounds": {"width": 60, "height": 32},
               "padding": {"left": 15, "right": 15, "top": 0, "bottom": 0}, "radius": 4,
               "strokeWeight": 1, "fills": [color(45, 140, 240)], "strokes": [color(45, 140, 240)],
               "label": {"characters": "查询", "fontName": {"family": "Inter", "style": "Regular"},
                         "fontSize": 14, "fontWeight": 400, "lineHeight": {"unit": "PIXELS", "value": 21},
                         "hasMissingFont": False, "fills": [color(255, 255, 255)]},
               "componentPropertyDefinitions": {"Label#1": {"type": "TEXT"}},
               "variableCollection": {"variables": [{} for _ in range(11)]},
               "boundVariables": {"component": {"fills": 1}, "label": {"fontSize": 1}}}
    export = {"componentId": "component", "pageReference": "page", "fileReference": "file",
              "width": 60, "height": 32, "nativePngBase64": base64.b64encode(buffer.getvalue()).decode()}
    return source, font, creation, capture, export, img


class ButtonCandidateAuditTests(unittest.TestCase):
    def test_good_candidate_remains_unadmitted(self):
        inputs = fixture()
        before = deepcopy(inputs[:5])
        report = inspect(*inputs)
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["pixelDifferenceCounts"], {"textZone": 0, "cornerEdge": 0, "nonTextInterior": 0})
        self.assertEqual(before, inputs[:5])
        self.assertEqual(report["nativeAdmission"], "NOT_RUN")

    def test_wrong_font_or_text_cannot_pass(self):
        for field, value in (("characters", "错误"), ("fontName", {"family": "Other", "style": "Regular"})):
            inputs = list(fixture())
            inputs[3]["label"][field] = value
            self.assertEqual(inspect(*inputs)["status"], "FAIL")

    def test_nontext_paint_and_pixel_drift_fail(self):
        inputs = list(fixture())
        inputs[3]["fills"][0]["color"]["r"] = 0
        self.assertEqual(inspect(*inputs)["status"], "FAIL")
        inputs = list(fixture())
        changed = Image.open(BytesIO(base64.b64decode(inputs[4]["nativePngBase64"]))).convert("RGBA")
        changed.putpixel((10, 16), (0, 0, 0, 255))
        buffer = BytesIO(); changed.save(buffer, format="PNG")
        inputs[4]["nativePngBase64"] = base64.b64encode(buffer.getvalue()).decode()
        report = inspect(*inputs)
        self.assertFalse(report["checks"]["nonTextInteriorPixelsExact"])

    def test_foreign_component_and_fake_admission_rejected(self):
        inputs = list(fixture())
        inputs[4]["componentId"] = "other"
        with self.assertRaisesRegex(ValueError, "identity"):
            inspect(*inputs)
        inputs = list(fixture())
        inputs[3]["nativeAcceptance"] = "PASS"
        with self.assertRaisesRegex(ValueError, "admission"):
            inspect(*inputs)


if __name__ == "__main__":
    unittest.main()
