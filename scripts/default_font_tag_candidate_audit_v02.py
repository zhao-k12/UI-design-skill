"""Audit the fixed Tag candidate evidence without claiming native fidelity admission."""
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_review(source, candidate):
    with Image.open(source) as original_image, Image.open(candidate) as native_image:
        original = original_image.convert("RGBA")
        native = native_image.convert("RGBA")
        if original.size != (42, 22) or native.size != original.size:
            raise ValueError("tag_candidate_size_mismatch")
        composited = Image.new("RGBA", native.size, "white")
        composited.alpha_composite(native)
        non_text = []
        glyph_pixels = [0, 0]
        for y in range(22):
            for x in range(42):
                native_rgb = composited.getpixel((x, y))[:3]
                if 9 <= x < 33 and 3 <= y < 19 and max(abs(c - t) for c, t in zip(native_rgb, (81, 90, 110))) <= 35:
                    glyph_pixels[0 if x < 21 else 1] += 1
                if 7 <= x < 35 and 3 <= y < 19:
                    continue
                source_rgb = original.getpixel((x, y))[:3]
                delta = max(abs(a - b) for a, b in zip(source_rgb, native_rgb))
                if delta:
                    non_text.append((x, y, delta))
        corner = lambda x, y: (x < 4 or x >= 38) and (y < 4 or y >= 18)
        return {
            "sourceSize": list(original.size),
            "nativeSize": list(native.size),
            "nonTextChangedPixels": len(non_text),
            "nonTextMaximumChannelDelta": max((row[2] for row in non_text), default=0),
            "nonTextChangesOutsideFourCorners": sum(not corner(x, y) for x, y, _ in non_text),
            "glyphPixelsByCharacterZone": glyph_pixels,
        }


def audit():
    source = ROOT / "artifacts/task-054/tag-source"
    root = ROOT / "artifacts/task-055"
    issues = verify_artifacts(source, expected_types={"Tag"})
    component = read_json(source / "component_ir.json")["components"][0]
    if component["logicalComponentId"] != "data.tag.default.enabled" or component["content"]["text"] != "启用":
        issues.append({"code": "wrong_source_scope"})
    result = {"scope": "v02-default-font-tag-candidate", "status": "CANDIDATE_REVIEW",
              "fidelityGate": "NOT_RUN", "registryAdmission": "NOT_RUN",
              "sourceComponentIrSha256": sha256(source / "component_ir.json"), "platforms": {}, "issues": issues}
    for platform in ("figma", "penpot"):
        folder = root / platform
        created = read_json(folder / "creation.json")
        observed = read_json(folder / "independent-read.json")
        png = folder / "component-native.png"
        repeat = folder / "repeat-native.png"
        svg = folder / "component-native.svg"
        svg_source = svg.read_text(encoding="utf-8").lower()
        main = created["component"] if platform == "figma" else created["main"]
        label = observed["label"]
        target_font = "Inter" if platform == "figma" else "sourcesanspro"
        actual_font = label["fontName"]["family"] if platform == "figma" else label["fontId"]
        check = {
            "fileAndNodeIdentity": created["componentId"] == (observed["component"]["id"] if platform == "figma" else observed["instance"]["componentId"]),
            "fixedGeometry": main["width"] == 42 and main["height"] == 22,
            "fixedContentAndDefaultFont": label["text" if platform == "penpot" else "characters"] == "启用" and actual_font == target_font and str(label["fontSize"]) == "12",
            "nativeMainAndInstance": (observed["instance"]["mainComponentId"] == created["componentId"] if platform == "figma" else observed["instance"]["componentId"] == created["componentId"]),
            "repeatNativePngStable": sha256(png) == sha256(repeat),
            "nativeSvgPresent": svg.stat().st_size > 100,
            "nativeSvgSemantics": all(any(color in svg_source for color in forms) for forms in
                (("#f7f7f7", "rgb(247, 247, 247)"),
                 ("#e8eaec", "rgb(232, 234, 236)"),
                 ("#515a6e", "rgb(81, 90, 110)"))) and
                ("<text" in svg_source and "启用" in svg_source and "sourcesanspro" in svg_source
                 if platform == "penpot" else svg_source.count("<path") >= 3),
        }
        pixels = pixel_review(source / component["screenshot"]["path"], png)
        check["visualCandidateReview"] = (pixels["nonTextChangesOutsideFourCorners"] == 0 and
                                           pixels["nonTextMaximumChannelDelta"] <= 3 and
                                           min(pixels["glyphPixelsByCharacterZone"]) >= 3)
        metadata_path = ROOT / f"adapters/{platform}/metadata/tag-default-font-candidate-0.2.0.json"
        metadata = read_json(metadata_path)
        check["candidateMetadataConsistent"] = (
            metadata["status"] == "CANDIDATE_REVIEW" and
            metadata["nativeAdmission"] == "NOT_RUN" and
            metadata["readyForPageGeneration"] is False and
            metadata["componentIrSha256"] == result["sourceComponentIrSha256"] and
            metadata["componentId"] == created["componentId"] and
            metadata["instanceId"] == created["instanceId"] and
            metadata["contentScope"] == {"text": "启用", "size": "default", "color": "default",
                                         "closable": False, "checkable": False, "checked": True,
                                         "width": 42, "height": 22} and
            metadata["evidenceSha256"] == {name: sha256(folder / name) for name in
                ("creation.json", "independent-read.json", "component-native.png", "repeat-native.png", "component-native.svg")})
        if not all(check.values()):
            issues.append({"code": "candidate_check_failed", "platform": platform,
                           "checks": [name for name, passed in check.items() if not passed]})
        result["platforms"][platform] = {
            "fileReference": created["fileReference" if platform == "figma" else "fileId"],
            "pageReference": created["pageId"], "componentId": created["componentId"],
            "instanceId": created["instanceId"], "font": target_font,
            "checks": check, "pixelReview": pixels,
            "candidateMetadataSha256": sha256(metadata_path),
            "evidenceSha256": {name: sha256(folder / name) for name in
                ("creation.json", "independent-read.json", "component-native.png", "repeat-native.png", "component-native.svg")},
        }
    if issues:
        result["status"] = "FAIL"
    report = root / "candidate-audit.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    report = audit()
    print(json.dumps({"status": report["status"], "issues": report["issues"],
                      "pixelReview": {key: value["pixelReview"] for key, value in report["platforms"].items()}}, ensure_ascii=False))
    raise SystemExit(report["status"] == "FAIL")
