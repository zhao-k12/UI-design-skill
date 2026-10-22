"""Copy a V0.2.8 Figma input to an independent V0.2.9 sizing-policy run."""
import argparse
from importlib import import_module
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validators.ui_ir import load_json
from workflow_v03.core import write

FILES = ("prototype.txt", "observations.json", "review.json", "layout-plan.json",
         "decisions.json", "content.json", "runtime-measurements.json",
         "source-geometry.json", "versions.json")


def migrate(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not destination.is_relative_to((ROOT / "artifacts").resolve()) or destination.exists():
        raise ValueError("Use a new independent artifact directory")
    if load_json(source / "versions.json")["component_library_version"] != "0.2.8-figma-iview-list-page":
        raise ValueError("Only the V0.2.8 Figma input can be migrated")
    destination.mkdir(parents=True)
    try:
        for name in FILES:
            shutil.copyfile(source / name, destination / name)
        read = lambda path: load_json(ROOT / path)
        resolver = import_module("core.component-resolver.resolver")
        components = resolver.registry_module.ComponentRegistry(
            read("registries/components/v0.2.9/catalog.json"),
            read("registries/components/v0.2.9/fidelity-reports.json"))
        tokens = resolver.tokens.TokenRegistry(read("registries/tokens/v0.2.3/default.json"))
        versions = load_json(destination / "versions.json")
        versions["component_library_version"] = components.library_version
        write(destination / "versions.json", versions)
        decisions = load_json(destination / "decisions.json")
        decisions["registrySha256"] = components.fingerprint
        write(destination / "decisions.json", decisions)
        analysis = import_module("core.prototype.parser").parse(
            load_json(destination / "observations.json"), destination)
        tree = import_module("validators.structure.gate").builder.build(analysis)
        mapping = import_module("core.component-resolver.primitive_mapping").resolve(
            analysis, tree, destination, load_json(destination / "review.json"),
            load_json(destination / "layout-plan.json"), decisions, components, tokens,
            allow_text_primitives=True)
        if mapping["status"] != "PASS":
            raise ValueError("Migrated component mapping failed: " + str(mapping["issues"]))
        content = load_json(destination / "content.json")
        content["mappingSha256"] = import_module("validators.structure.gate").builder.fingerprint(mapping)
        write(destination / "content.json", content)
        return {"status": "READY", "registrySha256": components.fingerprint,
                "mappingSha256": content["mappingSha256"]}
    except Exception:
        shutil.rmtree(destination)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(migrate(args.source, args.destination))
