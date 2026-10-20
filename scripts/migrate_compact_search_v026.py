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


def verify_existing(target, prior, components, tokens, catalog):
    """Reject drift without rewriting an already materialized migration."""
    manifest_path = target / "input-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Existing migration target has no input manifest")
    manifest = load_json(manifest_path)
    expected_header = {
        "kind": "v02-versioned-profile-migration", "status": "READY_FOR_PREFLIGHT",
        "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
        "targetComponentRegistrySha256": components.fingerprint,
        "policy": "same-approved-semantics/new-v0.2.6-component-registry/no-native-evidence-reuse",
    }
    if any(manifest.get(key) != value for key, value in expected_header.items()) \
            or set(manifest.get("files", {})) != set(prior["files"]):
        raise ValueError("Existing migration target manifest differs")
    if any(digest(target / name) != manifest["files"][name] for name in prior["files"]):
        raise ValueError("Existing migration target file hash differs")
    changed = {"decisions.json", "content.json", "versions.json"}
    if any(digest(target / name) != digest(SOURCE / name) for name in prior["files"] if name not in changed):
        raise ValueError("Existing migration target source copy differs")
    decisions = load_json(SOURCE / "decisions.json")
    decisions["registrySha256"] = components.fingerprint
    versions = load_json(SOURCE / "versions.json")
    versions["component_library_version"] = catalog["libraryVersion"]
    if load_json(target / "decisions.json") != decisions or load_json(target / "versions.json") != versions:
        raise ValueError("Existing migration target version decision differs")
    analysis = parse(load_json(target / "observations.json"), target)
    review = load_json(target / "review.json")
    page_tree = builder.build(analysis)
    if check(analysis, page_tree, target, review)["status"] != "PASS":
        raise ValueError("Human-approved semantics did not survive migration")
    plan = load_json(target / "layout-plan.json")
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, page_tree, target, review, plan, decisions, components, tokens,
        allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError("Seven-component mapping failed: " + str(mapping["issues"]))
    content = load_json(SOURCE / "content.json")
    content["mappingSha256"] = builder.fingerprint(mapping)
    if load_json(target / "content.json") != content:
        raise ValueError("Existing migration target content mapping differs")


def migrate(target=TARGET):
    target = Path(target)
    prior = load_json(SOURCE / "input-manifest.json")
    if prior["status"] != "READY_FOR_PREFLIGHT" or any(
            digest(SOURCE / name) != expected for name, expected in prior["files"].items()):
        raise ValueError("Approved source package changed")
    admission = load_json(ROOT / "registries/components/v0.2.6/admission.json")
    if admission["status"] != "PASS" or len(admission["components"]) != 7:
        raise ValueError("Seven-component Registry is not admitted")
    catalog = load_json(CATALOG)
    components = import_module("core.component-resolver.registry").ComponentRegistry(
        catalog, load_json(FIDELITY))
    if components.fingerprint != admission["registrySha256"]:
        raise ValueError("Registry admission hash changed")
    tokens = import_module("core.design-rules.tokens").TokenRegistry(
        load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
    if target.exists():
        verify_existing(target, prior, components, tokens, catalog)
        return {"status": "PASS", "action": "REUSED", "sourcePrototypeSha256": digest(target / "prototype.txt"),
                "componentRegistryVersion": catalog["registryVersion"],
                "componentCount": len(admission["components"])}
    target.mkdir(parents=True)
    for name in prior["files"]:
        shutil.copyfile(SOURCE / name, target / name)
    analysis = parse(load_json(target / "observations.json"), target)
    review = load_json(target / "review.json")
    page_tree = builder.build(analysis)
    if check(analysis, page_tree, target, review)["status"] != "PASS":
        raise ValueError("Human-approved semantics did not survive migration")
    plan = load_json(target / "layout-plan.json")
    decisions = load_json(target / "decisions.json")
    decisions["registrySha256"] = components.fingerprint
    save(target / "decisions.json", decisions)
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, page_tree, target, review, plan, decisions, components, tokens,
        allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError("Seven-component mapping failed: " + str(mapping["issues"]))
    content = load_json(target / "content.json")
    content["mappingSha256"] = builder.fingerprint(mapping)
    save(target / "content.json", content)
    versions = load_json(target / "versions.json")
    versions["component_library_version"] = catalog["libraryVersion"]
    save(target / "versions.json", versions)
    save(target / "input-manifest.json", {
        "kind": "v02-versioned-profile-migration", "status": "READY_FOR_PREFLIGHT",
        "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
        "targetComponentRegistrySha256": components.fingerprint,
        "policy": "same-approved-semantics/new-v0.2.6-component-registry/no-native-evidence-reuse",
        "files": {name: digest(target / name) for name in prior["files"]},
    })
    verify_existing(target, prior, components, tokens, catalog)
    return {"status": "PASS", "action": "CREATED", "sourcePrototypeSha256": digest(target / "prototype.txt"),
            "componentRegistryVersion": catalog["registryVersion"],
            "componentCount": len(admission["components"])}


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False))
