"""Plan a Figma component batch without changing admitted components or evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.ui_ir import ROOT, load_json

CATALOG = Path("registries/components/v0.2.7/catalog.json")


def plan(request, *, root=ROOT):
    catalog = load_json(Path(root) / CATALOG)
    entries = request.get("components")
    if not isinstance(entries, list) or not entries:
        raise ValueError("components must be a nonempty list")
    existing = catalog["components"]
    supported_types = {component["componentType"] for component in existing.values()}
    seen = set()
    rows = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"logicalComponentId", "componentType", "variant", "contentScope"}:
            raise ValueError("Each component requires logicalComponentId, componentType, variant, contentScope")
        logical_id, kind, variant, scope = (entry[name] for name in
                                            ("logicalComponentId", "componentType", "variant", "contentScope"))
        if not all(isinstance(value, str) and value for value in (logical_id, kind, variant)) \
                or not isinstance(scope, dict) or not scope or logical_id in seen:
            raise ValueError("Invalid or duplicate component request")
        if kind not in supported_types:
            raise ValueError("Component type is outside the admitted Figma scope: " + kind)
        seen.add(logical_id)
        previous = existing.get(logical_id)
        if previous is None:
            state = "NEEDS_OFFICIAL_CAPTURE"
        elif (previous["componentType"] == kind and previous["defaultVariant"] == variant
              and previous["contentScope"] == scope):
            state = "REUSE_ADMITTED"
        else:
            state = "MIGRATION_REQUIRED"
        rows.append({**entry, "state": state})
    counts = {state: sum(row["state"] == state for row in rows) for state in
              ("REUSE_ADMITTED", "NEEDS_OFFICIAL_CAPTURE", "MIGRATION_REQUIRED")}
    return {"scope": "figma-component-batch-plan", "catalogVersion": catalog["registryVersion"],
            "sourceVersion": catalog["sourceVersion"], "counts": counts,
            "readyForCapture": counts["MIGRATION_REQUIRED"] == 0,
            "rows": rows,
            "captureQueue": [row["logicalComponentId"] for row in rows
                             if row["state"] == "NEEDS_OFFICIAL_CAPTURE"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    try:
        result = plan(load_json(args.request))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": result["counts"], "readyForCapture": result["readyForCapture"]},
                     ensure_ascii=False))
    return 0 if result["readyForCapture"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
