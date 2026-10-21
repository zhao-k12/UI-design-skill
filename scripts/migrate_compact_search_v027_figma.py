"""Migrate the approved compact-search input to the 18-component Figma profile."""
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.prototype.parser import parse
from validators.structure.gate import builder, check
from validators.ui_ir import load_json

SOURCE = ROOT / "examples/user-management-compact-search-v026"
TARGET = ROOT / "examples/user-management-compact-search-v027-figma"
CATALOG = ROOT / "registries/components/v0.2.7/catalog.json"
REPORTS = ROOT / "registries/components/v0.2.7/fidelity-reports.json"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify(target, prior, registry, tokens):
    target = Path(target)
    manifest = load_json(target / "input-manifest.json")
    if (manifest.get("kind") != "figma-only-profile-migration" or
            manifest.get("sourcePackage") != SOURCE.relative_to(ROOT).as_posix() or
            manifest.get("targetComponentRegistrySha256") != registry.fingerprint or
            set(manifest.get("files", {})) != set(prior["files"]) or
            any(digest(target / name) != expected for name, expected in manifest["files"].items())):
        raise ValueError("Figma migration manifest or file bytes changed")
    changed = {"decisions.json", "content.json", "versions.json"}
    if any(digest(target / name) != digest(SOURCE / name)
           for name in prior["files"] if name not in changed):
        raise ValueError("Approved source semantics changed")
    decisions = load_json(target / "decisions.json")
    versions = load_json(target / "versions.json")
    if (decisions.get("registrySha256") != registry.fingerprint or
            versions.get("component_library_version") != registry.library_version):
        raise ValueError("Migrated Registry version lock changed")
    analysis = parse(load_json(target / "observations.json"), target)
    page_tree = builder.build(analysis)
    review = load_json(target / "review.json")
    if check(analysis, page_tree, target, review)["status"] != "PASS":
        raise ValueError("Approved structure did not survive migration")
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, page_tree, target, review, load_json(target / "layout-plan.json"),
        decisions, registry, tokens, allow_text_primitives=True)
    if (mapping["status"] != "PASS" or
            load_json(target / "content.json")["mappingSha256"] != builder.fingerprint(mapping)):
        raise ValueError("Migrated mapping/content did not survive migration")
    return True


def migrate(target=TARGET):
    target = Path(target).resolve()
    if not target.is_relative_to((ROOT / "examples").resolve()):
        raise ValueError("Migration target must stay inside examples")
    prior = load_json(SOURCE / "input-manifest.json")
    if (prior["status"] != "READY_FOR_PREFLIGHT" or
            any(digest(SOURCE / name) != expected for name, expected in prior["files"].items())):
        raise ValueError("Approved V0.2.6 source package changed")
    catalog = load_json(CATALOG)
    registry = import_module("core.component-resolver.registry").ComponentRegistry(
        catalog, load_json(REPORTS))
    admission = load_json(ROOT / "registries/components/v0.2.7/admission.json")
    if (registry.fingerprint != admission["registrySha256"] or
            len(admission["components"]) != 18):
        raise ValueError("18-component Registry admission changed")
    tokens = import_module("core.design-rules.tokens").TokenRegistry(
        load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
    if target.exists():
        verify(target, prior, registry, tokens)
        return {"status": "PASS", "action": "REUSED", "componentCount": 18}
    stage = Path(tempfile.mkdtemp(prefix=".v027-figma-stage-", dir=target.parent)).resolve()
    try:
        for name in prior["files"]:
            shutil.copyfile(SOURCE / name, stage / name)
        decisions = load_json(stage / "decisions.json")
        decisions["registrySha256"] = registry.fingerprint
        save(stage / "decisions.json", decisions)
        versions = load_json(stage / "versions.json")
        versions["component_library_version"] = registry.library_version
        save(stage / "versions.json", versions)
        analysis = parse(load_json(stage / "observations.json"), stage)
        page_tree = builder.build(analysis)
        review = load_json(stage / "review.json")
        if check(analysis, page_tree, stage, review)["status"] != "PASS":
            raise ValueError("Approved structure did not survive migration")
        mapping = import_module("core.component-resolver.primitive_mapping").resolve(
            analysis, page_tree, stage, review, load_json(stage / "layout-plan.json"),
            decisions, registry, tokens, allow_text_primitives=True)
        if mapping["status"] != "PASS":
            raise ValueError("18-component mapping failed: " + str(mapping["issues"]))
        content = load_json(stage / "content.json")
        content["mappingSha256"] = builder.fingerprint(mapping)
        save(stage / "content.json", content)
        save(stage / "input-manifest.json", {
            "kind": "figma-only-profile-migration", "status": "READY_FOR_PREFLIGHT",
            "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
            "targetComponentRegistrySha256": registry.fingerprint,
            "policy": "same-approved-semantics/new-18-component-figma-registry/no-native-evidence-reuse",
            "files": {name: digest(stage / name) for name in prior["files"]}})
        verify(stage, prior, registry, tokens)
        if target.exists():
            raise ValueError("Migration target appeared during staging")
        stage.rename(target)
    finally:
        if stage.exists():
            if (not stage.is_relative_to((ROOT / "examples").resolve()) or
                    not stage.name.startswith(".v027-figma-stage-")):
                raise ValueError("Unsafe migration staging cleanup target")
            shutil.rmtree(stage)
    return {"status": "PASS", "action": "CREATED", "componentCount": 18}


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False))
