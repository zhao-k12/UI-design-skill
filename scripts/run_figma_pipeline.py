"""Run the approved static-page pipeline for the active Figma-only scope."""
import argparse
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.byte_lock import VERSION, build_platform
from adapters.component_bindings import ComponentBindings
from adapters.figma.compiler import prepare as prepare_v02
from scripts.run_pipeline import profile_resources
from validators.ui_ir import load_json

FIGMA_BATCH_PROFILE = {
    "tokens": "registries/tokens/v0.2.2/default.json",
    "components": "registries/components/v0.2.7/catalog.json",
    "fidelity": "registries/components/v0.2.7/fidelity-reports.json",
    "componentBindings": "component-bindings-0.2.7-figma.json",
    "fontBindings": "page-default-font-bindings-0.2.0.json",
}
FIGMA_BATCH_PROFILE_028 = {
    "tokens": "registries/tokens/v0.2.3/default.json",
    "components": "registries/components/v0.2.8/catalog.json",
    "fidelity": "registries/components/v0.2.8/fidelity-reports.json",
    "componentBindings": "component-bindings-0.2.8-figma.json",
    "fontBindings": "page-default-font-bindings-0.2.0.json",
}


def run(input_dir, output_dir, figma_file, profile="v0.2.6"):
    base, output = Path(input_dir).resolve(), Path(output_dir).resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Use an artifact task directory")
    if profile not in ("v0.2", "v0.2.6", "v0.2.7-figma", "v0.2.8-figma"):
        raise ValueError("Figma-only entry supports V0.2 profiles")
    read = lambda path: load_json(ROOT / path)
    paths = (FIGMA_BATCH_PROFILE_028 if profile == "v0.2.8-figma" else
             FIGMA_BATCH_PROFILE if profile == "v0.2.7-figma" else profile_resources(profile))
    resolver = importlib.import_module("core.component-resolver.resolver")
    tokens = resolver.tokens.TokenRegistry(read(paths["tokens"]))
    components = resolver.registry_module.ComponentRegistry(
        read(paths["components"]), read(paths["fidelity"]))
    versions = load_json(base / "versions.json")
    if (versions["component_library_version"] != components.library_version or
            versions["design_token_version"] != tokens.version):
        raise ValueError("Input versions do not match the selected profile; use an independent migrated input package")
    icon_lock = read("registries/icons/current.json")
    icons = importlib.import_module("core.icon-resolver.registry").IconRegistry(
        read("registries/icons/snapshots/" + icon_lock["snapshotSha256"] + "/registry.json"))
    assets = importlib.import_module("core.asset-resolver.registry").AssetRegistry(
        read("registries/assets/catalog.json"), ROOT / "registries/assets")
    geometry = importlib.import_module("core.component-resolver.placement").SourceGeometry(
        load_json(base / "source-geometry.json"), components)
    binding = None
    if profile == "v0.2.8-figma":
        # Resolve deterministic resource gaps before the longer Core run and
        # before creating any Figma page. This is diagnostic, not a QA bypass.
        binding = ComponentBindings(read("adapters/figma/metadata/" + paths["componentBindings"]),
                                    components, platform="figma")
        from workflow_v03.readiness import audit as audit_readiness
        readiness = audit_readiness(base, tokens, components, geometry, binding, figma_file)
        output.mkdir(parents=True, exist_ok=True)
        runner = importlib.import_module("core.pipeline.runner")
        runner.write(output / "readiness_preflight.json", readiness)
        if readiness["status"] != "READY":
            qa = {"scope": "figma-resource-readiness", "status": readiness["status"],
                  "blockedStage": "resource-readiness", "readyForAdapter": False,
                  "nativeExecution": "NOT_RUN", "issues": readiness["issues"],
                  "activePlatforms": ["figma"]}
            runner.write(output / "qa_report.json", qa)
            return qa
    content = load_json(base / "content.json")
    icon_ids = {node["iconId"] for item in content["items"]
                for children in item.get("cellSlots", {}).values()
                for node in children if node["type"] == "IconInstance"}
    svg = {icon_id: (ROOT / "registries/icons/objects" /
                     (icons.resolve(icon_id)["descriptor"]["svgSha256"] + ".svg")).read_bytes()
           for icon_id in icon_ids}
    runner = importlib.import_module("core.pipeline.runner")
    qa = runner.run(load_json(base / "observations.json"), base,
                    load_json(base / "review.json"), load_json(base / "layout-plan.json"),
                    load_json(base / "decisions.json"), content, components, tokens,
                    icons, assets, geometry, svg, versions, output,
                    measurement_evidence=load_json(base / "runtime-measurements.json"),
                    evidence_root=ROOT)
    qa["activePlatforms"] = ["figma"]
    qa["developmentScope"] = "FIGMA_ONLY"
    if not qa["readyForAdapter"]:
        runner.write(output / "qa_report.json", qa)
        return qa

    binding = binding or ComponentBindings(
        read("adapters/figma/metadata/" + paths["componentBindings"]),
        components, platform="figma")
    common = [load_json(output / "final_ui_ir.json"), tokens, components, binding,
              icons, read("adapters/figma/metadata/icon-bindings.json"),
              read("adapters/figma/metadata/" + paths["fontBindings"])]
    report = prepare_v02(*common, file_reference=figma_file)
    if report["status"] == "PASS" and report["plan"]["adapterVersion"] != versions["figma_adapter_version"]:
        report = {"status": "FAIL", "plan": None,
                  "issues": [{"code": "adapter_version_changed",
                              "message": "Native plan differs from locked adapter version"}]}
    runner.write(output / "figma_preflight.json", report)
    qa["adapterPreflights"] = {"figma": report["status"]}
    qa["readyForAdapter"] = report["status"] == "PASS"
    if qa["readyForAdapter"]:
        plan = report["plan"]
        lock = {"lockSchemaVersion": VERSION,
                "scope": "v02-adapter-preflight-byte-lock",
                "activePlatforms": ["figma"],
                "nativeExecution": "NOT_RUN", "releaseReady": False,
                "platforms": {"figma": build_platform("figma", plan)}}
        lock_path = output / "adapter-execution-lock.json"
        if lock_path.exists() and load_json(lock_path) != lock:
            qa.update(status="MIGRATION_REQUIRED", readyForAdapter=False,
                      adapterLockIssues=["Adapter byte lock changed; use a new task directory"])
        else:
            if not lock_path.exists():
                runner.write(lock_path, lock)
            qa["adapterExecutionLockSha256"] = sha256(lock_path.read_bytes()).hexdigest()
    else:
        qa["status"] = "FAIL"
    runner.write(output / "qa_report.json", qa)
    return qa


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--figma-file", required=True)
    parser.add_argument("--profile", choices=("v0.2", "v0.2.6", "v0.2.7-figma", "v0.2.8-figma"),
                        default="v0.2.6")
    args = parser.parse_args()
    try:
        qa = run(args.input_dir, args.output_dir, args.figma_file, args.profile)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(qa, ensure_ascii=False))
    return 0 if qa["readyForAdapter"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
