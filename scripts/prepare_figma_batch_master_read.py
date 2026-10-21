"""Prepare a single read-only Figma host script for all 18 admitted component masters."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.ui_ir import ROOT, load_json

TEMPLATE = Path("scripts/figma_batch_master_read.js")


def prepare(root=ROOT):
    root = Path(root)
    catalog = load_json(root / "registries/components/v0.2.7/catalog.json")
    binding = load_json(root / "adapters/figma/metadata/component-bindings-0.2.7-figma.json")
    components = catalog["components"]
    if len(components) != 18 or set(components) != set(binding["bindings"]):
        raise ValueError("The 18-component Registry/binding scope changed")
    specs = []
    for logical_id, component in components.items():
        variant = component["defaultVariant"]
        reference = binding["bindings"][logical_id]["variants"][variant]
        if reference["kind"] != "component" or reference["fileReference"] != "0vGWSRoLxBiVPXiZ8xJAX9" \
                or reference["fidelityReportSha256"] != component["fidelity"]["reportSha256"]:
            raise ValueError("Binding does not match admitted component: " + logical_id)
        specs.append({"logicalId": logical_id, "reference": reference["componentReference"]})
    template = (root / TEMPLATE).read_text(encoding="utf-8")
    marker = "const specs = __SPECS__;"
    if template.count(marker) != 1:
        raise ValueError("Batch read template marker changed")
    script = template.replace(marker, "const specs = " + json.dumps(specs, ensure_ascii=True,
                                                           separators=(",", ":")) + ";")
    return script, {"scope": "figma-batch-master-read-preparation", "status": "PASS",
                    "componentCount": len(specs), "registryVersion": catalog["registryVersion"],
                    "templateSha256": sha256(template.encode("utf-8")).hexdigest(),
                    "scriptSha256": sha256(script.encode("utf-8")).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    directory = args.output_dir.resolve()
    if not directory.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    script, report = prepare()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "batch-master-read.js").write_text(script, encoding="utf-8")
    (directory / "batch-master-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
