"""Compile the three Figma actions without conflating their QA gates."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

from adapters.component_bindings import ComponentBindings
from adapters.figma.compiler import prepare, script_for_page
from workflow_v03.core import fingerprint
from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]


def _embed(payload, runtime, call):
    source = (Path(__file__).parent / runtime).read_text(encoding="utf-8")
    return ("const payload = " + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ";\n"
            + source + "\nreturn await " + call + "(figma, payload);\n")


def skeleton_script(skeleton, file_reference, revision):
    if not skeleton["cells"] or not file_reference or not revision:
        raise ValueError("A source-bound skeleton, Figma file and revision are required")
    payload = deepcopy(skeleton)
    payload.update(fileReference=file_reference, revision=revision)
    return _embed(payload, "skeleton_runtime.js", "executeAnnotatedSkeleton")


def _resources(file_reference):
    resolver = importlib.import_module("core.component-resolver.resolver")
    from scripts.run_figma_pipeline import FIGMA_BATCH_PROFILE
    paths = FIGMA_BATCH_PROFILE
    read = lambda relative: load_json(ROOT / relative)
    tokens = resolver.tokens.TokenRegistry(read(paths["tokens"]))
    components = resolver.registry_module.ComponentRegistry(
        read(paths["components"]), read(paths["fidelity"]))
    icon_lock = read("registries/icons/current.json")
    icons = importlib.import_module("core.icon-resolver.registry").IconRegistry(
        read("registries/icons/snapshots/" + icon_lock["snapshotSha256"] + "/registry.json"))
    bindings = ComponentBindings(read("adapters/figma/metadata/" + paths["componentBindings"]),
                                 components, platform="figma")
    return (tokens, components, bindings, icons,
            read("adapters/figma/metadata/icon-bindings.json"),
            read("adapters/figma/metadata/" + paths["fontBindings"]))


def component_script(default_document, skeleton, file_reference, revision, skeleton_qa):
    if (skeleton_qa.get("status") != "PASS" or
        skeleton_qa.get("skeletonSha256") != fingerprint(skeleton) or
        not skeleton_qa.get("independentReadback") or
        not skeleton_qa.get("pageReference")):
        raise ValueError("Independent native skeleton QA must PASS before component construction")
    document = deepcopy(default_document)
    document["documentId"] += ".default." + revision
    report = prepare(document, *_resources(file_reference), file_reference=file_reference)
    if report["status"] != "PASS":
        raise ValueError("Default component page preflight failed: " + str(report["issues"]))
    return script_for_page(report["plan"]), report


def fill_script(fill, file_reference, default_qa):
    if (default_qa.get("status") != "PASS" or
        default_qa.get("defaultPageSha256") != fill["defaultPageSha256"] or
        not default_qa.get("independentReadback") or
        not default_qa.get("pageReference") or
        not default_qa.get("nodeMap")):
        raise ValueError("Independent default-component page QA must PASS before filling content")
    payload = deepcopy(fill)
    payload.update(fileReference=file_reference, pageReference=default_qa["pageReference"],
                   nodeMap=default_qa["nodeMap"])
    return _embed(payload, "fill_runtime.js", "fillPrototypeContent")
