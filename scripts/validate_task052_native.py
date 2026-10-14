"""Independent TASK-052 readback check for the frozen V0.2 page."""
import json
from pathlib import Path
import hashlib
from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "task-052"
PRE = ROOT / "artifacts" / "task-051" / "pipeline-v02-ready"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def close(a, b):
    return isinstance(a, (int, float)) and abs(a - b) < 0.02


def matches_size(actual, size):
    return close(actual, size["value"]) if size["mode"] == "fixed" else isinstance(actual, (int, float)) and actual > 0


def validate():
    figma_plan = read(PRE / "figma_preflight.json")["plan"]
    penpot_plan = read(PRE / "penpot_preflight.json")["plan"]
    figma = read(ART / "figma" / "native-read.json")
    penpot = read(ART / "penpot" / "native-read-final.json")
    execution = read(ART / "penpot" / "native-execution.json")
    issues = []

    def check(ok, code, detail=""):
        if not ok:
            issues.append({"code": code, "detail": detail})

    for key in ("uiIrSha256", "tokensSha256", "componentsSha256", "iconsSha256"):
        check(figma_plan[key] == penpot_plan[key] == execution[key], "input_lock_mismatch", key)
    check(execution["status"] == "EXECUTED" and execution["scope"] == "penpot_native_translation", "penpot_execution_failed")
    check(execution["pageReference"] == penpot["pageId"] and execution["rootReference"] == penpot["root"]["id"], "penpot_identity_mismatch")
    check(figma["root"]["width"] == penpot["root"]["width"] == 1920 and figma["root"]["height"] == penpot["root"]["height"] == 1080, "page_size_mismatch")
    check(len(figma["sections"]) == len(penpot["sections"]) == 3, "section_count_mismatch")
    for f, p in zip(figma["sections"], penpot["sections"]):
        check(f["name"] == p["name"] and all(close(f[k], p[k] - (80 if k in ("x", "y") else 0)) for k in ("x", "y", "width", "height")), "section_geometry_mismatch", f["name"])

    # Check every editable text and native instance in the Adapter plans.
    main_to_library = {
        "4b3abcb2-3ae8-803f-8008-c8485c8b9729": "4b3abcb2-3ae8-803f-8008-c8489b7c9e9a",
        "4b3abcb2-3ae8-803f-8008-c85957bd3a28": "4b3abcb2-3ae8-803f-8008-c8595885b154",
    }
    counts = {}
    for platform, plan, native in (("figma", figma_plan, figma), ("penpot", penpot_plan, penpot)):
        specs = list(walk(plan["pages"][0]))
        texts = [s for s in specs if s["type"] == "Text"]
        instances = [s for s in specs if s.get("componentReference")]
        native_texts = {n["name"]: n for n in native["texts"]}
        native_instances = {n["name"]: n for n in native["instances"] if n["name"] in {s["name"] for s in instances}}
        check(len(native["texts"]) == 24, "native_text_count_mismatch", platform)
        check(len(instances) == len(native_instances) == 6, "instance_count_mismatch", platform)
        for spec in texts:
            actual = native_texts.get(spec["name"])
            check(actual is not None, "missing_text", platform + ":" + spec["name"])
            if actual:
                check(actual["characters"] == spec["text"], "text_content_mismatch", platform + ":" + spec["name"])
                check(matches_size(actual["width"], spec["layout"]["width"]) and matches_size(actual["height"], spec["layout"]["height"]), "text_envelope_mismatch", platform + ":" + spec["name"])
                font_ok = actual["fontName"]["family"] == "Inter" if platform == "figma" else actual["fontId"] == "sourcesanspro"
                check(font_ok, "default_font_mismatch", platform + ":" + spec["name"])
        for spec in instances:
            actual = native_instances.get(spec["name"])
            check(actual is not None, "missing_instance", platform + ":" + spec["name"])
            if actual:
                expected = spec["componentReference"]
                actual_ref = actual["mainComponentId"] if platform == "figma" else actual["componentId"]
                check(actual_ref == (expected if platform == "figma" else main_to_library.get(expected, expected)), "instance_reference_mismatch", platform + ":" + spec["name"])
                if platform == "penpot":
                    check(actual["isCopy"] is True, "flattened_instance", spec["name"])
                check(matches_size(actual["width"], spec["layout"]["width"]) and matches_size(actual["height"], spec["layout"]["height"]), "instance_geometry_mismatch", platform + ":" + spec["name"])
        counts[platform] = {"plannedTextNodes": len(texts), "nativeTextNodes": len(native["texts"]), "nativeInstances": len(native_instances)}

    check(penpot["nodeCount"] == 93 and len(execution["createdNodeIds"]) == 93, "penpot_node_inventory_mismatch")
    images = {}
    for platform in ("figma", "penpot"):
        path = ART / platform / "native-page.png"
        with Image.open(path) as image:
            check(image.format == "PNG" and image.size == (1920, 1080), "native_png_mismatch", platform)
            images[platform] = image.convert("RGB")
        counts[platform]["nativePngSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    diff = ImageChops.difference(images["figma"].crop((0, 0, 1920, 464)), images["penpot"].crop((0, 0, 1920, 464)))
    mean = [round(v, 3) for v in ImageStat.Stat(diff).mean]
    check(all(v < 2 for v in mean), "cross_platform_visual_delta_exceeded", str(mean))
    return {"status": "PASS" if not issues else "FAIL", "scope": "task052_independent_native_readback", "uiIrSha256": figma_plan["uiIrSha256"], "figmaPageId": figma["pageId"], "penpotPageId": penpot["pageId"], "counts": counts, "contentAreaMeanRgbAbsDiff": mean, "issues": issues, "visualReview": "SEPARATE_MANUAL_CHECK", "releaseReady": False}


if __name__ == "__main__":
    report = validate()
    out = ART / "native-qa.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
