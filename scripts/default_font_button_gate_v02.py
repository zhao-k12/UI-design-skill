"""Evidence-bound, fixture-scoped native fidelity gate for the V0.2 default-font Button."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.button_fidelity_diagnostics_v02 import inspect
from validators.visual.fidelity import digest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
SOURCE_PNG = SOURCE.parent / "action.button.primary.medium.png"
MANIFEST = ROOT / "artifacts/task-029/font-adaptation-manifest.json"
POLICY = ROOT / "policies/font-adaptation-0.2.0.json"
REVIEW = ROOT / "artifacts/task-031/visual-review.json"
PLATFORMS = {
    "figma": {"dir": ROOT / "artifacts/task-027/figma", "repeat": ROOT / "artifacts/task-031/figma",
              "target": ROOT / "adapters/figma/metadata/default-font-target-0.2.0.json",
              "candidate": ROOT / "adapters/figma/metadata/button-default-font-candidate-0.2.0.json",
              "svg": "button-outline.svg"},
    "penpot": {"dir": ROOT / "artifacts/task-028/penpot", "repeat": ROOT / "artifacts/task-031/penpot",
               "target": ROOT / "adapters/penpot/metadata/default-font-target-0.2.1.json",
               "candidate": ROOT / "adapters/penpot/metadata/button-default-font-candidate-0.2.0.json",
               "svg": "button-native.svg"},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def svg_checks(platform, svg_bytes, expected_text):
    root = ET.fromstring(svg_bytes)
    if root.tag.split("}")[-1] != "svg":
        return False
    if root.attrib.get("width") != "60" or root.attrib.get("height") != "32":
        return False
    if platform == "figma":
        return any(node.tag.split("}")[-1] == "path" and node.attrib.get("fill") == "white"
                   and bool(node.attrib.get("d")) for node in root.iter())
    return any(node.tag.split("}")[-1] == "text" and "".join(node.itertext()) == expected_text
               and "font-family: sourcesanspro" in node.attrib.get("style", "")
               and "font-weight: 400" in node.attrib.get("style", "") for node in root.iter())


def evaluate_platform(platform, source, candidate, target, prior, current, visual, native, repeated,
                      svg_bytes, span, source_png):
    label = current.get("label", {})
    expected_text = source["content"]["text"]
    binding = target["defaultFont"]
    current_font = (label.get("fontName", {}).get("family") if platform == "figma"
                    else label.get("fontId"))
    current_weight = label.get("fontWeight")
    current_style = (label.get("fontName", {}).get("style") if platform == "figma"
                     else label.get("fontVariantId"))
    expected_style = ("Regular" if platform == "figma" else binding["fontVariantId"])
    expected_weight = (400 if platform == "figma" else "400")
    css = next(n for n in source["nodes"] if n["path"] == "0")["computedStyle"]
    expected_size = float(css["font-size"][:-2])
    expected_line_height = float(css["line-height"][:-2])
    current_size = float(label.get("fontSize", -1))
    current_line_height = (label.get("lineHeight") == {"unit": "PIXELS", "value": expected_line_height}
                           if platform == "figma" else
                           float(label.get("lineHeight", -1)) * current_size == expected_line_height)
    metrics = inspect(Image.open(native), source_png, span)
    text = metrics["textZone"]
    within = all(box and box["x"] >= span["x"] and box["y"] >= span["y"]
                 and box["x"] + box["width"] <= span["x"] + span["width"]
                 and box["y"] + box["height"] <= span["y"] + span["height"]
                 for box in text["inkBoundsByHalf"])
    checks = {
        "lockedSourceAndNativeCandidate": (candidate.get("status") == "CANDIDATE_REVIEW"
            and prior.get("status") == "CANDIDATE_REVIEW" and all(prior.get("checks", {}).values())
            and len(prior.get("checks", {})) >= 11 and prior.get("nativeAdmission") == "NOT_RUN"
            and candidate.get("nativeAdmission") == "NOT_RUN"),
        "currentNativeComponentAndInstance": (current.get("fileReference") == candidate.get("fileReference")
            and current.get("componentId") == candidate.get("componentId")
            and current.get("instanceId") == candidate.get("instanceId")
            and current.get("instanceMainComponentId", current.get("instanceComponentId")) == candidate.get("componentId")
            and current.get("nativeAdmission") == "NOT_RUN"),
        "currentNativeTextAndFont": (label.get("characters") == expected_text
            and current_font == binding["family"] and current_style == expected_style
            and current_weight == expected_weight and current_size == expected_size and current_line_height
            and (label.get("hasMissingFont") is False if platform == "figma" else current.get("fileValidation") == [])),
        "currentNativeGeometry": (current.get("componentBounds") == source["rootBounds"]
            and current.get("padding") == {edge: float(css["padding-" + edge][:-2])
                                                for edge in ("left", "right", "top", "bottom")}
            and current.get("radius") == float(css["border-top-left-radius"][:-2])
            and current.get("strokeWeight") == float(css["border-top-width"][:-2])),
        "stableIndependentNativePng": native.read_bytes() == repeated.read_bytes(),
        "independentNativeSvg": svg_checks(platform, svg_bytes, expected_text),
        "nonTextPixelsExact": metrics["nonTextInterior"]["different"] == 0,
        "roundedCornerPaintBound": (metrics["cornerEdge"]["outOfPalettePixels"] == 0
            and metrics["cornerEdge"]["maxPaletteResidual"] <= 2),
        "separateVisibleUnclippedGlyphs": (all(count > 0 for count in text["brightInkPixelsByHalf"])
            and all(fraction is not None and 0 < fraction < .75 for fraction in text["inkFillFractionByHalf"])
            and within),
        "hashBoundVisualReview": (visual.get("legibleText") == expected_text
            and visual.get("glyphsComplete") is True and visual.get("tofuOrMissingGlyph") is False
            and visual.get("clippedText") is False and visual.get("nativePngSha256") == file_sha(native)
            and visual.get("nativeSvgSha256") == sha(svg_bytes)),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "fileReference": candidate["fileReference"], "componentId": candidate["componentId"],
            "pixelDiagnostics": metrics, "nativePngSha256": file_sha(native), "nativeSvgSha256": sha(svg_bytes),
            "repeatNativePngSha256": file_sha(repeated)}


def run():
    source_bundle = json.loads(SOURCE.read_bytes())
    source = next(c for c in source_bundle["components"] if c["componentType"] == "Button")
    manifest = json.loads(MANIFEST.read_bytes())
    policy = json.loads(POLICY.read_bytes())
    review = json.loads(REVIEW.read_bytes())
    if (source_bundle.get("status") != "PASS" or file_sha(SOURCE_PNG) != source["screenshot"]["sha256"]
            or manifest.get("version") != "0.2.1"
            or manifest.get("status") != "TARGET_REPLACED_BUTTON_CANDIDATES_PENDING_ADMISSION"
            or policy.get("decisionStatus") != "USER_APPROVED"
            or review.get("status") != "PASS" or review.get("expectedText") != source["content"]["text"]
            or review.get("effectiveCjkFontIdentity") != "UNVERIFIED"):
        raise ValueError("invalid_source_policy_or_review")
    for relative, expected in manifest["inputSha256"].items():
        if file_sha(ROOT / relative) != expected:
            raise ValueError("manifest_input_changed:" + relative)
    span = next(n for n in source["nodes"] if n["path"] == "0.0")["bounds"]
    image = Image.open(SOURCE_PNG).convert("RGBA")
    outputs = {}
    evidence = {"sourceComponentIrSha256": digest(source), "sourceScreenshotSha256": file_sha(SOURCE_PNG),
                "manifestSha256": file_sha(MANIFEST), "policySha256": file_sha(POLICY),
                "visualReviewSha256": file_sha(REVIEW)}
    for platform, paths in PLATFORMS.items():
        candidate = json.loads(paths["candidate"].read_bytes())
        target = json.loads(paths["target"].read_bytes())
        if (candidate["fileReference"] != manifest["targets"][platform]["fileReference"]
                or candidate["componentId"] != manifest["candidateComponentIds"][platform]
                or candidate["fontBinding"]["family"] != target["defaultFont"]["family"]):
            raise ValueError("candidate_manifest_target_mismatch:" + platform)
        for name, expected in candidate["evidenceSha256"].items():
            if file_sha(paths["dir"] / name) != expected:
                raise ValueError("native_evidence_changed:" + platform + ":" + name)
        prior = json.loads((paths["dir"] / "audit.json").read_bytes())
        for relative, expected in prior["inputSha256"].items():
            if file_sha(ROOT / relative) != expected:
                raise ValueError("prior_audit_input_changed:" + relative)
        current = json.loads((paths["repeat"] / "repeat-native-read.json").read_bytes())
        native = paths["dir"] / "component-native.png"
        repeated = paths["repeat"] / "button-repeat.png"
        svg = (paths["repeat"] / paths["svg"]).read_bytes()
        outputs[platform] = evaluate_platform(platform, source, candidate, target, prior, current,
                                              review["platforms"][platform], native, repeated, svg, span, image)
        evidence[platform] = {"candidateMetadataSha256": file_sha(paths["candidate"]),
                              "targetMetadataSha256": file_sha(paths["target"]),
                              "priorAuditSha256": file_sha(paths["dir"] / "audit.json"),
                              "repeatNativeReadSha256": file_sha(paths["repeat"] / "repeat-native-read.json")}
    passed = all(row["status"] == "PASS" for row in outputs.values())
    return {"scope": "production", "evidenceKind": "v02-default-font-button-native-fidelity",
            "gateVersion": "0.2.2", "componentType": source["componentType"],
            "variants": [source["variant"]], "logicalComponentId": source["logicalComponentId"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source), "status": "PASS" if passed else "FAIL",
            "admissionEligible": passed, "issues": [] if passed else ["platform_fidelity_failed"],
            "candidateEvidenceKind": "native-design-capture",
            "checks": {"geometryAndStyle": "PASS" if passed else "FAIL",
                       "screenshot": {"policy": "source-locked-default-font-regions-0.2.2",
                                      "changedPixelsOutsidePermittedRegions": sum(
                                          row["pixelDiagnostics"]["nonTextInterior"]["different"]
                                          + row["pixelDiagnostics"]["cornerEdge"]["outOfPalettePixels"]
                                          for row in outputs.values())}},
            "platforms": outputs, "evidenceSha256": evidence,
            "effectiveCjkFontIdentity": "UNVERIFIED", "registryAdmission": "NOT_RUN",
            "readyForPageGeneration": False, "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"status":"FAIL","admissionEligible":false,"releaseReady":false}\n', encoding="utf-8")
    try:
        report = run()
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "admissionEligible": report["admissionEligible"],
                          "platforms": {p: row["status"] for p, row in report["platforms"].items()},
                          "registryAdmission": "NOT_RUN"}))
        return 0 if report["status"] == "PASS" else 2
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
