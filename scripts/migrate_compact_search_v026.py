"""Migrate the approved compact-search source into an isolated 7-component profile."""
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.prototype.parser import parse
from validators.structure.gate import builder, check
from validators.ui_ir import load_json

SOURCE = ROOT / "examples/user-management-compact-search"
TARGET = ROOT / "examples/user-management-compact-search-v026"
CATALOG = ROOT / "registries/components/v0.2.6/catalog.json"
FIDELITY = ROOT / "registries/components/v0.2.6/fidelity-reports.json"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate():
    prior = load_json(SOURCE / "input-manifest.json")
    if prior["status"] != "READY_FOR_PREFLIGHT" or any(
            digest(SOURCE / name) != expected for name, expected in prior["files"].items()):
        raise ValueError("Approved source package changed")
    admission = load_json(ROOT / "registries/components/v0.2.6/admission.json")
    if admission["status"] != "PASS" or len(admission["components"]) != 7:
        raise ValueError("Seven-component Registry is not admitted")
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in prior["files"]:
        shutil.copyfile(SOURCE / name, TARGET / name)
    analysis = parse(load_json(TARGET / "observations.json"), TARGET)
    review = load_json(TARGET / "review.json")
    page_tree = builder.build(analysis)
    if check(analysis, page_tree, TARGET, review)["status"] != "PASS":
        raise ValueError("Human-approved semantics did not survive migration")
    catalog = load_json(CATALOG)
    components = import_module("core.component-resolver.registry").ComponentRegistry(
        catalog, load_json(FIDELITY))
    if components.fingerprint != admission["registrySha256"]:
        raise ValueError("Registry admission hash changed")
    tokens = import_module("core.design-rules.tokens").TokenRegistry(
        load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
    plan = load_json(TARGET / "layout-plan.json")
    decisions = load_json(TARGET / "decisions.json")
    decisions["registrySha256"] = components.fingerprint
    save(TARGET / "decisions.json", decisions)
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, page_tree, TARGET, review, plan, decisions, components, tokens,
        allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError("Seven-component mapping failed: " + str(mapping["issues"]))
    content = load_json(TARGET / "content.json")
    content["mappingSha256"] = builder.fingerprint(mapping)
    save(TARGET / "content.json", content)
    versions = load_json(TARGET / "versions.json")
    versions["component_library_version"] = catalog["libraryVersion"]
    save(TARGET / "versions.json", versions)
    save(TARGET / "input-manifest.json", {
        "kind": "v02-versioned-profile-migration", "status": "READY_FOR_PREFLIGHT",
        "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
        "targetComponentRegistrySha256": components.fingerprint,
        "policy": "same-approved-semantics/new-v0.2.6-component-registry/no-native-evidence-reuse",
        "files": {name: digest(TARGET / name) for name in prior["files"]},
    })
    return {"status": "PASS", "sourcePrototypeSha256": digest(TARGET / "prototype.txt"),
            "componentRegistryVersion": catalog["registryVersion"],
            "componentCount": len(admission["components"])}


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False))
