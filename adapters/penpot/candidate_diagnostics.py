"""Reject incomplete native candidate evidence; this is not a fidelity gate."""
import base64
import hashlib
import re
import xml.etree.ElementTree as ET


def diagnose_candidate(capture, outline):
    """Accept raw host receipts and independently check observed export defects."""
    native = capture["result"]
    probe = outline["result"]
    issues = []
    for field in ("fileReference", "pageReference", "textReference"):
        expected = native.get(field)
        if field == "textReference":
            expected = next(n["reference"] for n in native["nodes"] if n["type"] == "text")
        if probe.get(field) != expected:
            issues.append({"code": "probe_identity_mismatch", "field": field})
    svg = base64.b64decode(native["nativeTextSvgBase64"], validate=True)
    ET.fromstring(svg)  # Do not infer font binding from a malformed export.
    urls = re.findall(r"url\(([^)]+)\)", svg.decode("utf-8"))
    complete = bool(urls) and all(re.fullmatch(
        r"https://design\.penpot\.app/assets/by-id/[0-9a-f-]{36}", url.strip("\"'")) for url in urls)
    if not complete:
        issues.append({"code": "native_font_asset_url_incomplete", "observedUrls": urls})
    frame_only = False
    observations = probe.get("observations", [])
    if len(observations) == 1:
        path = observations[0]
        d = path.get("d", "")
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
        x, y, w, h = (path[k] for k in ("x", "y", "width", "height"))
        frame_only = not re.search(r"[ACQSTHV]", d, re.I) and numbers == [x, y, x+w, y, x+w, y+h, x, y+h, x, y]
    if frame_only:
        issues.append({"code": "outline_is_text_frame", "nativePath": observations[0]["d"]})
    if not probe.get("originalEditableTextUnchanged"):
        issues.append({"code": "editable_text_changed"})
    # Valid-looking URLs or arbitrary paths alone never establish any of the
    # eight required proofs. A separate complete production gate remains mandatory.
    return {"status": "FAIL" if issues else "REVIEW", "platform": "penpot",
            "evidenceKind": "native-candidate-diagnostic", "fileReference": native["fileReference"],
            "componentReference": native["componentReference"], "penpotVersion": native.get("penpotVersion"),
            "nativeTextSvgSha256": hashlib.sha256(svg).hexdigest(), "issues": issues,
            "admissionEligible": False, "fidelityGate": "NOT_RUN", "requiredProofsComplete": False}
