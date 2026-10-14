"""Read-only migration audit for the frozen V0.1 source package and V0.2 targets."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_SOURCE = ROOT / "examples/acceptance-prototype"
TARGET_FIGMA = "0vGWSRoLxBiVPXiZ8xJAX9"
TARGET_PENPOT = "57949053-620f-8001-8008-c804c8d61529"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(source=DEFAULT_SOURCE, penpot_file=TARGET_PENPOT, geometry_path=None):
    source = Path(source).resolve()
    files = {
        "versions": source / "versions.json",
        "geometry": Path(geometry_path).resolve() if geometry_path is not None else source / "source-geometry.json",
        "measurements": source / "runtime-measurements.json",
        "content": source / "content.json",
        "catalog": ROOT / "registries/components/v0.2.3/catalog.json",
        "fidelity": ROOT / "registries/components/v0.2.3/fidelity-reports.json",
        "tokens": ROOT / "registries/tokens/v0.2.2/default.json",
        "iconBindings": ROOT / "adapters/penpot/metadata/icon-bindings-0.2.0.json",
        "runnerCli": ROOT / "scripts/run_pipeline.py",
    }
    versions, geometry, content = (load(files[k]) for k in ("versions", "geometry", "content"))
    catalog, fidelity, tokens = (load(files[k]) for k in ("catalog", "fidelity", "tokens"))
    icons = load(files["iconBindings"])["bindings"]
    blockers = []

    def block(code, detail, next_action):
        blockers.append({"code": code, "detail": detail, "nextAction": next_action})

    if versions["component_library_version"] != catalog["libraryVersion"] or versions["design_token_version"] != tokens["registryVersion"]:
        block("legacy_input_lock", "Source package locks V0.1 components and tokens.",
              "Create a new source-bound V0.2 input package and manifest; preserve the old package.")

    registry_type = importlib.import_module("core.component-resolver.registry").ComponentRegistry
    geometry_type = importlib.import_module("core.component-resolver.placement").SourceGeometry
    registry = registry_type(catalog, fidelity)
    try:
        geometry_type(geometry, registry)
    except ValueError as exc:
        block("source_geometry_mismatch", str(exc),
              "Re-measure and lock V0.2.3 admitted component geometry from its source evidence.")

    declared_icons = sorted({n["iconId"] for item in content["items"]
                             for slot in item.get("cellSlots", {}).values()
                             for n in slot if n["type"] == "IconInstance"})
    icon_registry = importlib.import_module("core.icon-resolver.registry").IconRegistry(
        importlib.import_module("icon-manager.remix-sync.manager").current())
    verify_icon = importlib.import_module("adapters.penpot.icon_admission").verify_binding
    stale_icons = []
    for icon_id in declared_icons:
        binding = icons.get(icon_id)
        if binding is None or binding["fileReference"] != penpot_file:
            stale_icons.append(icon_id)
            continue
        try:
            verify_icon(icon_id, binding, penpot_file, icon_registry.fingerprint)
        except ValueError:
            stale_icons.append(icon_id)
    if stale_icons:
        block("penpot_icon_target_mismatch", ", ".join(stale_icons),
              "Admit these native Remix icon components in the current Penpot target file, or use a new source that does not require them.")

    page_width = tokens["tokens"]["size.page"]["value"]
    if page_width != 1920:
        block("canvas_width_policy_unresolved", f"V0.2 size.page={page_width}; target canvas=1920.",
              "Version the Canvas/Layout policy and test the 1920-wide deterministic layout.")
    token_registry = importlib.import_module("core.design-rules.tokens").TokenRegistry(tokens)
    policy = "0.2.0-static-grow" if token_registry.version == "0.2.2" else "0.1.0"
    pattern = importlib.import_module("core.layout.patterns").instantiate(
        "list-page", {name: [] for name in ("header", "query", "toolbar", "table", "pagination")},
        canvas_policy=policy)
    canvas = importlib.import_module("core.layout.engine").LayoutEngine(token_registry).run(pattern)
    if canvas["status"] != "PASS" or canvas["skeleton"]["box"]["height"] < 1080:
        block("canvas_min_height_unresolved", "The V0.2 list Page does not resolve to at least 1080px.",
              "Version the Page height rule to guarantee at least 1080px.")

    runner_cli = importlib.import_module("scripts.run_pipeline")
    selected = runner_cli.profile_resources("v0.2")
    if (selected.get("tokens") != "registries/tokens/v0.2.2/default.json"
            or selected.get("components") != "registries/components/v0.2.3/catalog.json"
            or selected.get("componentBindings") != "component-bindings-0.2.3.json"
            or selected.get("fontBindings") != "page-default-font-bindings-0.2.0.json"):
        block("pipeline_cli_v01_pinned", "The production CLI loads V0.1 registries and adapter bindings unconditionally.",
              "Add an explicit V0.2 version route with an independent input and checkpoint lock.")

    if versions["design_token_version"] != tokens["registryVersion"] and files["measurements"].exists():
        block("text_measurements_need_rebind", "Runtime text measurements belong to the frozen V0.1 source package.",
              "Measure free text and composed cells using the target-file default fonts, then lock the new capture.")

    return {
        "task": "TASK-044", "status": "BLOCKED" if blockers else "READY_FOR_PREFLIGHT",
        "scope": "v02_pipeline_migration_readiness", "nativeExecution": "NOT_RUN",
        "targets": {"figma": TARGET_FIGMA, "penpot": penpot_file},
        "source": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
        "geometry": files["geometry"].relative_to(ROOT).as_posix() if files["geometry"].is_relative_to(ROOT) else str(files["geometry"]),
        "inputSha256": {k: digest(v) for k, v in files.items() if v.is_file()},
        "targetRegistrySha256": registry.fingerprint,
        "declaredIcons": declared_icons, "blockers": blockers,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geometry", type=Path, help="Explicit versioned Component IR geometry bundle")
    parser.add_argument("--penpot-file", default=TARGET_PENPOT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/task-044/readiness_report.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in project artifacts")
    report = audit(args.source, args.penpot_file, args.geometry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "blockers": [b["code"] for b in report["blockers"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
