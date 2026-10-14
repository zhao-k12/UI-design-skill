"""Rebuild only the V0.2 admitted source geometry from locked official runtime evidence."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPLAY = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
FROZEN = ROOT / "examples/acceptance-prototype/source-geometry.json"
CATALOG = ROOT / "registries/components/v0.2.3/catalog.json"
FIDELITY = ROOT / "registries/components/v0.2.3/fidelity-reports.json"
TARGET = ROOT / "examples/acceptance-prototype-v02"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    registry_module = importlib.import_module("core.component-resolver.registry")
    geometry_module = importlib.import_module("core.component-resolver.placement")
    replay, frozen = load(REPLAY), load(FROZEN)
    if replay["status"] != "PASS" or frozen["status"] != "PASS" or replay["componentIrVersion"] != frozen["componentIrVersion"]:
        raise ValueError("Source Component IR bundles are not compatible PASS evidence")
    registry = registry_module.ComponentRegistry(load(CATALOG), load(FIDELITY))
    by_id = {item["logicalComponentId"]: item for item in replay["components"]}
    table = next(item for item in frozen["components"] if item["logicalComponentId"] == "data.table.default")
    by_id["data.table.default"] = table
    expected = load(CATALOG)["components"]
    if set(by_id) != set(expected):
        raise ValueError("Source components differ from admitted Registry")
    components = []
    for logical_id in expected:
        component = by_id[logical_id]
        if registry_module.digest(component) != expected[logical_id]["fidelity"]["componentIrSha256"]:
            raise ValueError("Admitted Component IR changed: " + logical_id)
        components.append(component)
    bundle = {"status": "PASS", "componentIrVersion": replay["componentIrVersion"], "components": components}
    geometry_module.SourceGeometry(bundle, registry)
    lock = {"scope": "v02-source-geometry-only", "status": "PASS", "componentLibraryVersion": registry.library_version,
            "registrySha256": registry.fingerprint,
            "inputsSha256": {"replay": sha(REPLAY), "frozenTableBundle": sha(FROZEN),
                             "catalog": sha(CATALOG), "fidelity": sha(FIDELITY)},
            "componentIrSha256": {item["logicalComponentId"]: registry_module.digest(item) for item in components},
            "fullInputPackageReady": False}
    return bundle, lock


def main():
    bundle, lock = build()
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, data in (("source-geometry.json", bundle), ("source-geometry-lock.json", lock)):
        (TARGET / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "components": list(lock["componentIrSha256"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
