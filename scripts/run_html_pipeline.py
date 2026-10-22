"""Run the source-bound Core pipeline for HTML rendered with official components."""
from __future__ import annotations

import argparse
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validators.ui_ir import load_json
from scripts.run_figma_pipeline import FIGMA_ADAPTIVE_PROFILE_029


def run(source_dir: Path, output_dir: Path) -> dict:
    source_dir, output_dir = source_dir.resolve(), output_dir.resolve()
    if not output_dir.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Use an artifact task directory")
    paths = FIGMA_ADAPTIVE_PROFILE_029
    resolver = import_module("core.component-resolver.resolver")
    tokens = resolver.tokens.TokenRegistry(load_json(ROOT / paths["tokens"]))
    components = resolver.registry_module.ComponentRegistry(
        load_json(ROOT / paths["components"]), load_json(ROOT / paths["fidelity"]))
    versions = load_json(source_dir / "versions.json")
    if (versions["component_library_version"] != components.library_version or
            versions["design_token_version"] != tokens.version):
        raise ValueError("Input versions require an independent HTML profile migration")
    current = load_json(ROOT / "registries/icons/current.json")
    icons = import_module("core.icon-resolver.registry").IconRegistry(
        load_json(ROOT / "registries/icons/snapshots" / current["snapshotSha256"] / "registry.json"))
    assets = import_module("core.asset-resolver.registry").AssetRegistry(
        load_json(ROOT / "registries/assets/catalog.json"), ROOT / "registries/assets")
    geometry = import_module("core.component-resolver.placement").SourceGeometry(
        load_json(source_dir / "source-geometry.json"), components)
    content = load_json(source_dir / "content.json")
    icon_ids = {node["iconId"] for item in content["items"]
                for children in item.get("cellSlots", {}).values()
                for node in children if node["type"] == "IconInstance"}
    svg = {icon_id: (ROOT / "registries/icons/objects" /
                     (icons.resolve(icon_id)["descriptor"]["svgSha256"] + ".svg")).read_bytes()
           for icon_id in icon_ids}
    runner = import_module("core.pipeline.runner")
    qa = runner.run(load_json(source_dir / "observations.json"), source_dir,
                    load_json(source_dir / "review.json"), load_json(source_dir / "layout-plan.json"),
                    load_json(source_dir / "decisions.json"), content, components, tokens,
                    icons, assets, geometry, svg, versions, output_dir,
                    measurement_evidence=load_json(source_dir / "runtime-measurements.json"),
                    evidence_root=ROOT, delivery_mode="html-official-runtime")
    qa["activePlatforms"] = ["html"]
    qa["deliveryMode"] = "html-official-runtime"
    qa["htmlRenderStatus"] = "NOT_RUN"
    runner.write(output_dir / "qa_report.json", qa)
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        qa = run(args.source_dir, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps({"status": qa["status"], "readyForHtml": qa["readyForAdapter"],
                      "blockedStage": qa.get("blockedStage")}, ensure_ascii=False))
    return 0 if qa["readyForAdapter"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
