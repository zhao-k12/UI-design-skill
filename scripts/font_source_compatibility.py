"""Audit locked official component typography against observed native default fonts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "Button": "artifacts/task-023/replay-final/first/component_ir.json",
    "Input": "artifacts/task-023/replay-final/first/component_ir.json",
    "Select": "artifacts/task-023/replay-final/first/component_ir.json",
    "Table": "component-builder/runtime-renderer/metadata/headed-table-source/two-column-typography/component_ir.json",
}
TARGETS = {
    "figma": "adapters/figma/metadata/default-font-target-0.2.0.json",
    "penpot": "adapters/penpot/metadata/default-font-target-0.2.0.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def family_tokens(css_family):
    # A CSS stack is a declaration, not proof of the font used for each glyph.
    return tuple(part.strip().strip('"').strip("'").casefold()
                 for part in css_family.split(",") if part.strip())


def observed_text_styles(component):
    styles = {}
    for node in component.get("nodes", []):
        if not node.get("visible"):
            continue
        texts = [item.get("text", "") for item in node.get("textRuns", [])]
        attributes = node.get("attributes") or {}
        texts += [attributes.get("placeholder", ""), attributes.get("value", "")]
        texts = [item for item in texts if isinstance(item, str) and item.strip()]
        if not texts:
            continue
        css = node.get("computedStyle") or {}
        family = css.get("font-family")
        weight = css.get("font-weight")
        if not isinstance(family, str) or not family or not isinstance(weight, str) or not weight:
            raise ValueError("missing_source_text_style:" + component.get("logicalComponentId", ""))
        key = (family, weight)
        styles.setdefault(key, {"fontFamilyDeclaration": family, "fontWeight": weight,
                                "textNodePaths": [], "sampleTexts": []})
        styles[key]["textNodePaths"].append(node["path"])
        styles[key]["sampleTexts"].extend(texts)
    return list(styles.values())


def audit(source_documents, target_documents):
    if set(source_documents) != set(SOURCES) or set(target_documents) != set(TARGETS):
        raise ValueError("missing_source_or_target")
    target_fonts = {}
    for platform, metadata in target_documents.items():
        if (metadata.get("platform") != platform or metadata.get("status") != "PASS"
                or metadata.get("nativeAcceptance") != "NOT_RUN"
                or metadata.get("releaseReady") is not False
                or metadata.get("readyForPageGeneration") is not False):
            raise ValueError("invalid_target_font_metadata:" + platform)
        family = metadata.get("defaultFont", {}).get("family")
        if not isinstance(family, str) or not family:
            raise ValueError("missing_target_font_family")
        target_fonts[platform] = family
    items = []
    for kind, source in source_documents.items():
        if source.get("status") != "PASS" or not isinstance(source.get("components"), list):
            raise ValueError("invalid_source_ir:" + kind)
        components = [item for item in source["components"] if item.get("componentType") == kind]
        if len(components) != 1:
            raise ValueError("missing_or_duplicate_source_component:" + kind)
        component = components[0]
        text_styles = observed_text_styles(component)
        if not text_styles:
            raise ValueError("missing_visible_source_text:" + kind)
        targets = {}
        for platform, family in target_fonts.items():
            absent = [style for style in text_styles
                      if family.casefold() not in family_tokens(style["fontFamilyDeclaration"])]
            targets[platform] = {
                "targetFamily": family,
                "declaredSourceFamilyMatch": not absent,
                "sourceStylesNeedingNewMeasurement": absent,
                "measurement": "NOT_RUN",
                "nativeAdmission": "NOT_RUN",
                "effectiveGlyphFontIdentity": "UNVERIFIED",
            }
        items.append({
            "componentType": kind,
            "logicalComponentId": component["logicalComponentId"],
            "historicalRootBoundsForContextOnly": component.get("rootBounds"),
            "sourceTextStyles": text_styles,
            "targets": targets,
            "measurementReusable": False,
        })
    return {
        "scope": "v02-default-font-source-compatibility",
        "version": "0.2.0",
        "status": "REMEASURE_REQUIRED",
        "components": items,
        "targetFontMetadata": {p: {"family": f, "fileReference": target_documents[p]["fileReference"]}
                               for p, f in target_fonts.items()},
        "nativeAcceptance": "NOT_RUN",
        "readyForPageGeneration": False,
        "releaseReady": False,
        "limitations": [
            "CSS font-family is a declared stack, not proof of the effective font for every glyph.",
            "Native sample dimensions do not replace source-bound component measurements.",
            "Changing font requires a new versioned design comparison and native fidelity admission.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status":"FAIL","nativeAcceptance":"NOT_RUN","releaseReady":false}\n',
                      encoding="utf-8")
    try:
        source_documents, source_hashes = {}, {}
        for kind, relative in SOURCES.items():
            data = (ROOT / relative).read_bytes()
            source_documents[kind] = json.loads(data)
            source_hashes[relative] = digest(data)
        target_documents, target_hashes = {}, {}
        for platform, relative in TARGETS.items():
            data = (ROOT / relative).read_bytes()
            target_documents[platform] = json.loads(data)
            target_hashes[relative] = digest(data)
        result = audit(source_documents, target_documents)
        result["sourceSha256"] = source_hashes
        result["targetMetadataSha256"] = target_hashes
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "components": len(result["components"]),
                          "releaseReady": False}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
