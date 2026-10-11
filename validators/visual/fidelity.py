"""Conservative, platform-neutral fidelity comparison; never constructs components."""
from copy import deepcopy
import hashlib
from pathlib import Path

from PIL import Image, ImageChops

from validators.component_ir import verify_artifacts
from validators.ui_ir import load_json

POLICY_VERSION = "0.1.0"
STYLE_FIELDS = (
    "padding-top", "padding-right", "padding-bottom", "padding-left",
    "gap", "row-gap", "column-gap", "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width", "border-top-style",
    "border-right-style", "border-bottom-style", "border-left-style",
    "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius",
    "border-bottom-right-radius", "background-color", "color", "font-size",
    "font-family", "font-weight", "line-height", "letter-spacing", "text-align",
    "align-items", "justify-content", "opacity", "transform", "box-shadow",
    "font-style", "text-transform", "vertical-align", "flex-direction", "flex-wrap",
)


def digest(value):
    import json
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measurement(reference):
    """Export expected observations, for inspection only, never a native capture."""
    return {"rootBounds": deepcopy(reference["rootBounds"]), "nodes": [
        {"path": n["path"], "bounds": deepcopy(n["bounds"]),
         "computedStyle": {k: n["computedStyle"][k] for k in STYLE_FIELDS if k in n["computedStyle"]},
         "textRuns": deepcopy(n.get("textRuns", [])),
         "pseudoElements": deepcopy(n.get("pseudoElements", {})),
         "value": n.get("value")}
        for n in reference["nodes"] if n["visible"]]}


def compare(reference, candidate, reference_png, candidate_png, *, scope="production"):
    report = {"gateVersion": POLICY_VERSION, "scope": scope,
              "logicalComponentId": reference["logicalComponentId"],
              "componentType": reference["componentType"], "variants": [reference["variant"]],
              "sourceVersion": reference["provenance"]["sourceVersion"],
              "componentIrSha256": digest(reference), "status": "WARNING",
              "admissionEligible": False, "issues": [], "checks": {}}
    issues = report["issues"]
    def issue(code, severity, detail):
        issues.append({"code": code, "severity": severity, "detail": detail})
    if scope not in ("production", "test-fixture"):
        raise ValueError("Unknown evidence scope")
    if candidate is None:
        issue("missing_design_candidate", "WARNING", "Independent native component measurements and screenshot required")
        return report
    if not isinstance(candidate, dict):
        issue("invalid_candidate", "FAIL", "Capture manifest must be an object")
        report["status"] = "FAIL"
        return report
    report["candidateSha256"] = digest(candidate)
    if candidate.get("scope") != scope or candidate.get("evidenceKind") != "native-design-capture":
        issue("invalid_candidate_provenance", "FAIL", "Reference exports and test fixtures cannot serve as production candidates")
    for key, expected in (("logicalComponentId", reference["logicalComponentId"]),
                          ("variant", reference["variant"]), ("state", reference["state"]),
                          ("props", reference["props"]), ("content", reference["content"]),
                          ("fixtureContext", reference["fixtureContext"]),
                          ("sourceVersion", reference["provenance"]["sourceVersion"])):
        if candidate.get(key) != expected:
            issue("capture_context_mismatch", "FAIL", key)
    provenance = candidate.get("capture", {})
    report["capture"] = deepcopy(provenance)
    report["candidateEvidenceKind"] = candidate.get("evidenceKind")
    if not isinstance(provenance, dict) or not all(isinstance(provenance.get(k), str) and provenance[k].strip()
                                                  for k in ("captureId", "exporterVersion", "nativeEvidenceSha256")):
        issue("missing_capture_evidence", "WARNING", "Adapter capture identity, exporter version and native evidence hash required")
    elif len(provenance["nativeEvidenceSha256"]) != 64 or any(c not in "0123456789abcdef" for c in provenance["nativeEvidenceSha256"]):
        issue("invalid_capture_hash", "FAIL", "Native evidence must use SHA256")
    expected = measurement(reference)
    actual = candidate.get("measurements")
    # Exact normalized observation equality includes every visible node, text run and pseudo element.
    # No guessed CSS conversion or geometry tolerance can hide a mismatch.
    report["checks"]["geometryAndStyle"] = "PASS" if actual == expected else "FAIL"
    if actual != expected:
        issue("geometry_or_style_mismatch", "FAIL", "Visible node bounds, padding, gap, borders, radius, paint, typography or alignment differ")
    env = candidate.get("rasterContext", {})
    if env != {"deviceScaleFactor": reference["environment"]["deviceScaleFactor"], "background": "white"}:
        issue("raster_context_mismatch", "WARNING", "Matching scale and white export background required; no resizing is performed")
    try:
        if Path(reference_png).resolve() == Path(candidate_png).resolve():
            issue("reference_reused_as_candidate", "FAIL", "Candidate screenshot must be independently exported")
        if file_hash(candidate_png) != candidate.get("screenshotSha256"):
            issue("candidate_screenshot_hash_mismatch", "FAIL", "Screenshot differs from capture manifest")
        with Image.open(reference_png) as a, Image.open(candidate_png) as b:
            a, b = a.convert("RGBA"), b.convert("RGBA")
            report["referenceScreenshotSha256"] = file_hash(reference_png)
            report["candidateScreenshotSha256"] = file_hash(candidate_png)
            if a.size != b.size:
                issue("screenshot_size_mismatch", "FAIL", f"{a.size} != {b.size}")
            else:
                pixels = list(ImageChops.difference(a, b).getdata())
                changed = sum(any(p) for p in pixels)
                report["checks"]["screenshot"] = {"changedPixels": changed, "totalPixels": len(pixels),
                                                     "maxChannelDelta": max((max(p) for p in pixels), default=0)}
                if changed:
                    # Only known text rectangles may explain AA; changed geometry never qualifies.
                    boxes = [run["bounds"] for n in reference["nodes"] if n["visible"]
                             for run in n.get("textRuns", []) if "bounds" in run]
                    def text_pixel(index):
                        x, y = index % a.width, index // a.width
                        scale = reference["environment"]["deviceScaleFactor"]
                        return any(r["x"] * scale <= x < (r["x"] + r["width"]) * scale and
                                   r["y"] * scale <= y < (r["y"] + r["height"]) * scale for r in boxes)
                    minor = all(max(p) <= 16 and text_pixel(i) for i, p in enumerate(pixels) if any(p))
                    issue("text_antialiasing_review" if minor else "screenshot_mismatch",
                          "WARNING" if minor else "FAIL",
                          "Small text-only pixel differences require review" if minor else "Raster differs outside conservative text AA allowance")
    except (OSError, TypeError, ValueError) as exc:
        issue("missing_or_invalid_screenshot", "WARNING", str(exc))
    report["status"] = "FAIL" if any(i["severity"] == "FAIL" for i in issues) else "WARNING" if issues else "PASS"
    report["admissionEligible"] = report["status"] == "PASS" and scope == "production"
    return report


def run(reference_dir, candidate_dir=None):
    reference_dir = Path(reference_dir)
    verification = verify_artifacts(reference_dir)
    # The evidence validator returns issues; any invalid reference aborts comparison.
    if verification:
        raise ValueError(f"Invalid official runtime evidence: {verification}")
    bundle = load_json(reference_dir / "component_ir.json")
    results = []
    for reference in bundle["components"]:
        candidate_path = Path(candidate_dir) / (reference["logicalComponentId"] + ".json") if candidate_dir else None
        candidate = load_json(candidate_path) if candidate_path and candidate_path.exists() else None
        results.append(compare(reference, candidate, reference_dir / reference["screenshot"]["path"],
                               candidate_path.with_suffix(".png") if candidate_path else None))
    return {"scope": "component_fidelity_gate", "gateVersion": POLICY_VERSION,
            "status": "FAIL" if any(r["status"] == "FAIL" for r in results) else
                      "WARNING" if any(r["status"] == "WARNING" for r in results) else "PASS",
            "referenceBundleSha256": file_hash(reference_dir / "component_ir.json"), "components": results}
