"""Audit the replacement-file Penpot Button candidate against locked source evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
TARGET = ROOT / "adapters/penpot/metadata/default-font-target-0.2.1.json"
CAPTURE = ROOT / "artifacts/task-028/penpot/independent-capture.json"
NATIVE = ROOT / "artifacts/task-028/penpot/component-native.png"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def px(value):
    if not isinstance(value, str) or not value.endswith("px"):
        raise ValueError("invalid_css_length")
    return float(value[:-2])


def hex_rgb(value):
    match = re.fullmatch(r"rgb\((\d+), (\d+), (\d+)\)", value or "")
    if not match:
        raise ValueError("invalid_css_color")
    return "#" + "".join(f"{int(channel):02x}" for channel in match.groups())


def audit(source, target, capture, native, official, capture_sha, native_sha):
    if source.get("status") != "PASS" or target.get("status") != "OBSERVED_IN_REPLACEMENT_FILE":
        raise ValueError("invalid_source_or_target")
    if (capture.get("status") != "CAPTURED" or capture.get("fileId") != target.get("fileReference")
            or capture.get("pageId") != target.get("pageReference")
            or target.get("candidateCaptureSha256") != capture_sha):
        raise ValueError("candidate_target_identity_mismatch")
    if (capture.get("nativeAdmission") != "NOT_RUN" or capture.get("releaseReady") is not False
            or target.get("nativeAcceptance") != "NOT_RUN" or target.get("releaseReady") is not False):
        raise ValueError("unsupported_admission_claim")
    choices = [item for item in source["components"] if item["componentType"] == "Button"]
    if len(choices) != 1:
        raise ValueError("missing_source_button")
    button = choices[0]
    root = next(node for node in button["nodes"] if node["path"] == "0")
    span = next(node for node in button["nodes"] if node["path"] == "0.0")
    css = root["computedStyle"]
    comp, label, instance, assets = (capture[key] for key in ("component", "label", "instance", "assets"))
    font = target["defaultFont"]
    checks = {
        "nativeComponentAndCopy": comp["isMain"] is True and instance["isCopy"] is True
                                  and instance["componentId"] == comp["id"],
        "sourceContent": label["characters"] == button["content"]["text"],
        "replacementDefaultFont": label["fontId"] == font["fontId"]
                                  and label["fontFamily"] == font["family"]
                                  and label["fontVariantId"] == font["fontVariantId"]
                                  and label["fontWeight"] == str(font["weight"]),
        "sourceTypographyMetrics": float(label["fontSize"]) == px(css["font-size"])
                                  and float(label["lineHeight"]) * float(label["fontSize"]) == px(css["line-height"]),
        "sourceGeometry": comp["mainBounds"]["width"] == button["rootBounds"]["width"]
                          and comp["mainBounds"]["height"] == button["rootBounds"]["height"]
                          and native.size == official.size,
        "sourcePadding": all(comp["flex"][edge + "Padding"] == px(css["padding-" + edge])
                             for edge in ("left", "right", "top", "bottom")),
        "sourceRadiusAndBorder": comp["borderRadius"] == px(css["border-top-left-radius"])
                                 and len(comp["strokes"]) == 1
                                 and comp["strokes"][0]["strokeWidth"] == px(css["border-top-width"]),
        "sourcePaint": len(comp["fills"]) == 1 and len(label["fills"]) == 1
                       and comp["fills"][0]["fillColor"] == hex_rgb(css["background-color"])
                       and comp["strokes"][0]["strokeColor"] == hex_rgb(css["border-top-color"])
                       and label["fills"][0]["fillColor"] == hex_rgb(css["color"]),
        "editableLocalAssets": len(assets["colors"]) == 2
                               and assets["typography"]["fontId"] == font["fontId"]
                               and assets["typography"]["fontVariantId"] == font["fontVariantId"],
        "validNativeFile": capture["validation"] == [],
    }
    white = Image.new("RGBA", native.size, (255, 255, 255, 255))
    white.alpha_composite(native.convert("RGBA"))
    bounds = span["bounds"]
    x0, y0 = int(bounds["x"] - 2), int(bounds["y"] - 2)
    x1, y1 = int(bounds["x"] + bounds["width"] + 2), int(bounds["y"] + bounds["height"] + 2)
    edge = int(comp["borderRadius"] + 1)
    counts = {"textZone": 0, "cornerEdge": 0, "nonTextInterior": 0}
    for y in range(native.height):
        for x in range(native.width):
            if white.getpixel((x, y)) == official.getpixel((x, y)):
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                counts["textZone"] += 1
            elif x < edge or x >= native.width-edge or y < edge or y >= native.height-edge:
                counts["cornerEdge"] += 1
            else:
                counts["nonTextInterior"] += 1
    checks["nonTextInteriorPixelsExact"] = counts["nonTextInterior"] == 0
    return {"scope": "v02-penpot-button-source-native-candidate-audit", "version": "0.2.0",
            "platform": "penpot", "status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
            "sourceLogicalComponentId": button["logicalComponentId"],
            "nativeFileId": capture["fileId"], "nativeComponentId": comp["id"],
            "checks": checks, "pixelDifferenceCounts": counts,
            "comparisonNotes": ["Native transparent PNG composited on white for comparison.",
                                "Text-zone and corner counts diagnose differences; they are not admission tolerances.",
                                "CJK glyph identity and corner rendering require independent fidelity review."],
            "sourceScreenshotSha256": button["screenshot"]["sha256"],
            "nativePngSha256": native_sha,
            "nativeAdmission": "NOT_RUN", "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"status":"FAIL","nativeAdmission":"NOT_RUN","releaseReady":false}\n', encoding="utf-8")
    try:
        inputs = [json.loads(path.read_bytes()) for path in (SOURCE, TARGET, CAPTURE)]
        button = next(item for item in inputs[0]["components"] if item["componentType"] == "Button")
        source_bytes = (SOURCE.parent / "action.button.primary.medium.png").read_bytes()
        if digest(source_bytes) != button["screenshot"]["sha256"]:
            raise ValueError("source_screenshot_changed")
        native_bytes = NATIVE.read_bytes()
        result = audit(*inputs, Image.open(NATIVE).convert("RGBA"),
                       Image.open(SOURCE.parent / "action.button.primary.medium.png").convert("RGBA"),
                       digest(CAPTURE.read_bytes()), digest(native_bytes))
        result["inputSha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes())
                                 for path in (SOURCE, TARGET, CAPTURE, NATIVE)}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "checksPassed": sum(result["checks"].values()),
                          "checksTotal": len(result["checks"]), "releaseReady": False}))
        return 0 if result["status"] == "CANDIDATE_REVIEW" else 2
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
