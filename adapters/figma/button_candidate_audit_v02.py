"""Compare a native default-font Button candidate with its locked official source."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
FONT = ROOT / "adapters/figma/metadata/default-font-target-0.2.0.json"
CREATION = ROOT / "artifacts/task-027/figma/creation.json"
CAPTURE = ROOT / "artifacts/task-027/figma/independent-capture.json"
EXPORT = ROOT / "artifacts/task-027/figma/component-export.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def px(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d+)?px", value):
        raise ValueError("invalid_source_css_length")
    return float(value[:-2])


def rgb(value):
    found = re.fullmatch(r"rgb\((\d+), (\d+), (\d+)\)", value or "")
    if not found:
        raise ValueError("invalid_source_css_color")
    return tuple(int(part) for part in found.groups())


def paint_rgb(paints):
    if len(paints) != 1 or paints[0].get("type") != "SOLID":
        raise ValueError("invalid_native_paint")
    color = paints[0]["color"]
    return tuple(round(color[part] * 255) for part in ("r", "g", "b"))


def inspect(source, font, creation, capture, export, source_png):
    if (source.get("status") != "PASS" or font.get("platform") != "figma"
            or font.get("status") != "PASS" or font.get("nativeAcceptance") != "NOT_RUN"
            or font.get("readyForPageGeneration") is not False or font.get("releaseReady") is not False):
        raise ValueError("invalid_locked_inputs")
    choices = [c for c in source["components"] if c["componentType"] == "Button"]
    if len(choices) != 1:
        raise ValueError("missing_source_button")
    button = choices[0]
    source_root = next(n for n in button["nodes"] if n["path"] == "0")
    source_text = next(n for n in button["nodes"] if n["path"] == "0.0")
    css = source_root["computedStyle"]
    if (creation.get("status") != "CANDIDATE" or capture.get("status") != "CAPTURED"
            or not (creation.get("componentId") == capture.get("componentId") == export.get("componentId"))
            or not (creation.get("pageReference") == capture.get("pageReference") == export.get("pageReference"))
            or not (creation.get("fileReference") == capture.get("fileReference") == export.get("fileReference") == font.get("fileReference"))
            or capture.get("instanceMainComponentId") != capture.get("componentId")):
        raise ValueError("native_candidate_identity_mismatch")
    if (creation.get("nativeAcceptance") != "NOT_RUN" or capture.get("nativeAcceptance") != "NOT_RUN"
            or creation.get("releaseReady") is not False or capture.get("releaseReady") is not False):
        raise ValueError("unsupported_native_admission_claim")
    label = capture["label"]
    expected_text = button["content"]["text"]
    expected_family = font["defaultFont"]["family"]
    native_style = label.get("fontName", {})
    checks = {
        "componentType": capture.get("componentName") == "V0.2/Button/Primary/Medium/Default"
                         and capture.get("componentLayout") == "HORIZONTAL",
        "sourceContent": label.get("characters") == expected_text,
        "targetDefaultFont": native_style.get("family") == expected_family
                             and native_style.get("style") == font["bindings"][expected_family + ":400"]["style"]
                             and label.get("hasMissingFont") is False,
        "sourceWeightAndSize": label.get("fontWeight") == int(css["font-weight"])
                               and label.get("fontSize") == px(css["font-size"])
                               and label.get("lineHeight") == {"unit": "PIXELS", "value": px(css["line-height"])},
        "sourceGeometry": capture.get("componentBounds") == button["rootBounds"]
                          and export.get("width") == source_png.width and export.get("height") == source_png.height,
        "sourcePadding": capture.get("padding") == {
            edge: px(css["padding-" + edge]) for edge in ("left", "right", "top", "bottom")},
        "sourceRadiusAndBorder": capture.get("radius") == px(css["border-top-left-radius"])
                                 and capture.get("strokeWeight") == px(css["border-top-width"]),
        "sourcePaint": paint_rgb(capture["fills"]) == rgb(css["background-color"])
                       and paint_rgb(capture["strokes"]) == rgb(css["border-top-color"])
                       and paint_rgb(label["fills"]) == rgb(css["color"]),
        "editableComponentInstance": capture.get("instanceMainComponentId") == capture.get("componentId")
                                     and capture.get("componentPropertyDefinitions", {}).get(
                                         creation.get("labelPropertyKey"), {}).get("type") == "TEXT",
        "nativeVariableFoundations": len(capture.get("variableCollection", {}).get("variables", [])) >= 11
                                     and bool(capture.get("boundVariables", {}).get("component"))
                                     and bool(capture.get("boundVariables", {}).get("label")),
    }
    native_bytes = base64.b64decode(export["nativePngBase64"], validate=True)
    native = Image.open(BytesIO(native_bytes)).convert("RGBA")
    if native.size != source_png.size:
        raise ValueError("native_png_size_mismatch")
    white = Image.new("RGBA", native.size, (255, 255, 255, 255))
    white.alpha_composite(native)
    span = source_text["bounds"]
    margin = 2
    x0, y0 = int(span["x"] - margin), int(span["y"] - margin)
    x1, y1 = int(span["x"] + span["width"] + margin), int(span["y"] + span["height"] + margin)
    edge = int(px(css["border-top-left-radius"]) + 1)
    counts = {"textZone": 0, "cornerEdge": 0, "nonTextInterior": 0}
    for y in range(native.height):
        for x in range(native.width):
            if white.getpixel((x, y)) == source_png.getpixel((x, y)):
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                counts["textZone"] += 1
            elif x < edge or x >= native.width-edge or y < edge or y >= native.height-edge:
                counts["cornerEdge"] += 1
            else:
                counts["nonTextInterior"] += 1
    checks["nonTextInteriorPixelsExact"] = counts["nonTextInterior"] == 0
    return {"scope": "v02-button-source-native-candidate-audit", "version": "0.2.0",
            "platform": "figma", "status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
            "sourceLogicalComponentId": button["logicalComponentId"],
            "nativeComponentId": capture["componentId"],
            "checks": checks, "pixelDifferenceCounts": counts,
            "comparisonNotes": [
                "Native transparent PNG was composited on white to match the official opaque screenshot.",
                "Text zone uses the official span bounds expanded by two pixels; this is diagnostic, not an admission tolerance.",
                "Corner pixels and changed-font text pixels require separate fidelity review and glyph proof.",
            ],
            "sourceScreenshotSha256": button["screenshot"]["sha256"],
            "nativePngSha256": sha(native_bytes),
            "nativeAdmission": "NOT_RUN", "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status":"FAIL","nativeAdmission":"NOT_RUN","releaseReady":false}\n', encoding="utf-8")
    try:
        paths = (SOURCE, FONT, CREATION, CAPTURE, EXPORT)
        inputs = [json.loads(path.read_bytes()) for path in paths]
        screenshot_bytes = (SOURCE.parent / "action.button.primary.medium.png").read_bytes()
        button = next(c for c in inputs[0]["components"] if c["componentType"] == "Button")
        if sha(screenshot_bytes) != button["screenshot"]["sha256"]:
            raise ValueError("source_screenshot_changed")
        source_png = Image.open(BytesIO(screenshot_bytes)).convert("RGBA")
        result = inspect(*inputs, source_png)
        result["inputSha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path.read_bytes())
                                 for path in paths}
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "checksPassed": sum(result["checks"].values()),
                          "checksTotal": len(result["checks"]), "releaseReady": False}))
        return 0 if result["status"] == "CANDIDATE_REVIEW" else 2
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
