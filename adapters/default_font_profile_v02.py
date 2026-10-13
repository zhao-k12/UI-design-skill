"""Validate native font observations without admitting components or page layouts."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import struct

ROLES = {"body": (400, 14), "heading": (600, 20)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png_dimensions(data):
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("invalid_native_png")
    width, height = struct.unpack(">II", data[16:24])
    if not width or not height:
        raise ValueError("empty_native_png")
    return width, height


def build_profile(observation, review, platform, file_reference, page_reference):
    if platform not in ("figma", "penpot"):
        raise ValueError("unsupported_platform")
    for key, expected in (("scope", "platform-default-font-observation"),
                          ("version", "0.2.0"), ("platform", platform),
                          ("fileReference", file_reference), ("pageReference", page_reference)):
        if observation.get(key) != expected:
            raise ValueError("observation_identity_mismatch:" + key)
    if observation.get("status") != "PASS" or observation.get("issues"):
        raise ValueError("native_observation_failed")
    created = observation.get("createdNodeIds", [])
    if (not created or len(set(created)) != len(created)
            or created != observation.get("removedNodeIds")
            or observation.get("cleanupVerified") is not True
            or observation.get("mutatedNodeIds") != []):
        raise ValueError("native_cleanup_failed")
    if observation.get("nativeAcceptance") != "NOT_RUN" or observation.get("releaseReady") is not False:
        raise ValueError("unsupported_acceptance_claim")
    default = observation.get("defaultFont", {})
    family = default.get("family")
    if not isinstance(family, str) or not family:
        raise ValueError("missing_default_family")
    samples = observation.get("samples", [])
    if len(samples) != len(ROLES) or {s.get("role") for s in samples} != set(ROLES):
        raise ValueError("missing_or_duplicate_roles")
    bindings, measurements, issues = {}, [], []
    if set(review) != set(ROLES):
        raise ValueError("missing_visual_review")
    for sample in samples:
        role = sample["role"]
        weight, size = ROLES[role]
        binding = sample.get("binding", {})
        if (binding.get("family") != family or sample.get("weight") != weight
                or sample.get("fontSize") != size or not sample.get("text")):
            raise ValueError("sample_binding_mismatch")
        if platform == "figma":
            valid = any(v.get("family") == family and v.get("style") == binding.get("style")
                        and v.get("weight") == weight and v.get("fontStyle") != "ITALIC"
                        for v in observation.get("variants", []))
        else:
            valid = (binding.get("fontId") == default.get("fontId")
                     and binding.get("weight") == weight and binding.get("style") == "normal"
                     and any(v.get("fontId") == binding.get("fontId")
                             and v.get("fontVariantId") == binding.get("fontVariantId")
                             and v.get("weight") == weight and v.get("style") == "normal"
                             for v in observation.get("variants", [])))
        if not valid:
            raise ValueError("unobserved_font_variant")
        for dimension in ("width", "height"):
            value = sample.get(dimension)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("invalid_native_geometry")
        png = base64.b64decode(sample["nativePngBase64"], validate=True)
        dimensions = png_dimensions(png)
        check = review[role]
        if (check.get("pngSha256") != sha(png) or check.get("status") not in ("PASS", "FAIL")
                or not check.get("detail")):
            raise ValueError("visual_review_not_bound")
        if check["status"] != "PASS":
            issues.append({"code": "native_text_visual_failed", "role": role, "detail": check["detail"]})
        bindings[f"{family}:{weight}"] = dict(binding)
        measurements.append({"role": role, "width": sample["width"], "height": sample["height"],
                             "pngDimensions": list(dimensions), "pngSha256": sha(png),
                             "layoutMode": sample.get("layoutMode", "native-auto-width"),
                             "visualReview": dict(check), "componentMeasurementReady": False})
    return {"scope": "adapter-default-font-profile", "version": "0.2.0",
            "platform": platform, "fileReference": file_reference, "pageReference": page_reference,
            "defaultFont": dict(default), "bindings": bindings, "measurements": measurements,
            "fontBindingReady": True, "textSampleReview": "FAIL" if issues else "PASS",
            "status": "REVIEW" if issues else "PASS", "issues": issues,
            "effectiveCjkFontIdentity": "UNVERIFIED",
            "readyForPageGeneration": False, "nativeAcceptance": "NOT_RUN", "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--platform", choices=("figma", "penpot"), required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--page", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to((root / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # A failed recheck must invalidate any previous passing profile.
    args.output.write_text('{"status":"FAIL","fontBindingReady":false,"releaseReady":false}\n', encoding="utf-8")
    try:
        raw = args.observation.read_bytes()
        result = build_profile(json.loads(raw), json.loads(args.review.read_bytes()),
                               args.platform, args.file, args.page)
        result["observationSha256"] = sha(raw)
        result["reviewSha256"] = sha(args.review.read_bytes())
        result["policySha256"] = sha((root / "policies/font-selection-0.2.0.json").read_bytes())
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("platform", "status", "fontBindingReady", "textSampleReview", "releaseReady")}))
        return 0 if result["status"] == "PASS" else 2
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
