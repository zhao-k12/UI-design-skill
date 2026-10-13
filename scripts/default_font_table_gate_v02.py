"""Native fidelity gate for the exact fixed-content default-font Table."""

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_table_candidate_audit_v02 import (
    CELLS, REFERENCE, ROOT, TASK, TEXT_X, TEXT_Y, audit, pixel_review, read, sha,
)


POLICY = ROOT / "validators/visual/DEFAULT_FONT_TABLE_POLICY.md"


def native_svg_check(platform, path):
    root = ET.fromstring(path.read_bytes())
    if (root.tag.split("}")[-1] != "svg" or root.attrib.get("width") != "1392"
            or root.attrib.get("height") != "144"):
        return False
    descendants = list(root.iter())
    if platform == "figma":
        paths = [node for node in descendants if node.tag.split("}")[-1] == "path"]
        rectangles = [node for node in descendants if node.tag.split("}")[-1] == "rect"]
        return (len(paths) == 9 and len(rectangles) == 14
                and all(node.attrib.get("fill", "").upper() == "#515A6E" and node.attrib.get("d")
                        for node in paths))
    texts = [node for node in descendants if node.tag.split("}")[-1] == "text"]
    return (tuple("".join(node.itertext()) for node in texts) == CELLS
            and all("font-family: sourcesanspro" in node.attrib.get("style", "")
                    and "font-weight: 400" in node.attrib.get("style", "") for node in texts))


def visible_ink_by_character(path):
    image = Image.open(path).convert("RGB")
    counts = []
    for index, word in enumerate(CELLS):
        x0 = round(TEXT_X[index % 3])
        y0 = TEXT_Y[index // 3]
        for glyph in range(len(word)):
            count = 0
            for y in range(y0, y0 + 21):
                for x in range(x0 + glyph * 14, x0 + (glyph + 1) * 14):
                    color = image.getpixel((x, y))
                    count += max(abs(color[i] - (81, 90, 110)[i]) for i in range(3)) < 45
            counts.append(count)
    return counts


def run():
    candidate = audit()
    saved = read(TASK / "candidate-audit.json")
    if candidate != saved or candidate["status"] != "CANDIDATE_REVIEW":
        raise ValueError("Table candidate audit changed or failed")
    review = read(TASK / "visual-review.json")
    rows = {}
    for platform, previous in candidate["platforms"].items():
        folder = TASK / platform
        metadata_path = ROOT / f"adapters/{platform}/metadata/table-default-font-candidate-0.2.0.json"
        metadata = read(metadata_path)
        png = folder / "component-native.png"
        svg = folder / "component-native.svg"
        metrics = pixel_review(REFERENCE, png)
        ink = visible_ink_by_character(png)
        checks = {
            "candidateEvidenceLocked": (
                metadata["status"] == "CANDIDATE_REVIEW"
                and metadata["componentId"] == previous["componentId"]
                and metadata["fileReference"] == previous["fileReference"]
                and metadata["evidenceSha256"]["candidate-audit.json"] == sha(TASK / "candidate-audit.json")
                and all(metadata["evidenceSha256"][name] == sha(folder / name)
                        for name in previous["evidenceSha256"])),
            "sameNativeMainAndInstance": previous["checks"]["sameNativeMainAndInstance"],
            "fixedDataAndDefaultFont": previous["checks"]["fixedDataAndDefaultFont"],
            "nativeHierarchy": previous["checks"]["nativeHierarchy"],
            "nativeRepeatStable": previous["checks"]["nativeRepeatStable"],
            "nonTextExact": metrics["nonTextDifferences"] == 0,
            "nineteenVisibleGlyphs": len(ink) == sum(map(len, CELLS)) and all(count > 10 for count in ink),
            "independentNativeSvg": native_svg_check(platform, svg),
            "hashBoundVisualReview": (review["status"] == "PASS"
                                      and review["effectiveCjkFontIdentity"] == "UNVERIFIED"
                                      and review["platforms"][platform]["nativePngSha256"] == sha(png)
                                      and tuple(review["platforms"][platform]["legibleCells"]) == CELLS
                                      and review["platforms"][platform]["glyphsComplete"] is True
                                      and review["platforms"][platform]["clippedText"] is False
                                      and review["platforms"][platform]["tofuOrMissingGlyph"] is False),
        }
        rows[platform] = {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "fileReference": previous["fileReference"],
            "componentId": previous["componentId"],
            "nativePngSha256": sha(png),
            "nativeSvgSha256": sha(svg),
            "visibleInkByCharacter": ink,
            "pixelDiagnostics": metrics,
            "candidateMetadataSha256": sha(metadata_path),
        }
    passed = all(row["status"] == "PASS" for row in rows.values())
    return {
        "scope": "production", "gateVersion": "0.2.5", "status": "PASS" if passed else "FAIL",
        "logicalComponentId": "data.table.default", "componentType": "Table", "variants": ["default"],
        "sourceVersion": candidate["sourceVersion"], "componentIrSha256": candidate["componentIrSha256"],
        "candidateEvidenceKind": "native-design-capture", "admissionEligible": passed,
        "issues": [] if passed else ["table_fidelity_failed"], "platforms": rows,
        "evidenceSha256": {"sourceScreenshot": candidate["sourceScreenshotSha256"],
                           "candidateAudit": sha(TASK / "candidate-audit.json"),
                           "visualReview": candidate["visualReviewSha256"], "policy": sha(POLICY)},
        "contentScopeProposal": {"kind": "fixed-native-content", **read(ROOT / "adapters/figma/metadata/table-default-font-candidate-0.2.0.json")["contentScope"]},
        "effectiveCjkFontIdentity": "UNVERIFIED", "registryAdmission": "NOT_RUN",
        "readyForPageGeneration": False, "releaseReady": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "admissionEligible": report["admissionEligible"],
                      "platforms": {k: v["status"] for k, v in report["platforms"].items()}}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
