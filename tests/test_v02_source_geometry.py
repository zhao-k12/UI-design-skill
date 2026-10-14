"""The independent source bundle contains exactly the four admitted Component IRs."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import unittest

from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]
registry_module = import_module("core.component-resolver.registry")
placement = import_module("core.component-resolver.placement")


class V02SourceGeometryTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_json(ROOT / "examples/acceptance-prototype-v02/source-geometry.json")
        self.lock = load_json(ROOT / "examples/acceptance-prototype-v02/source-geometry-lock.json")
        self.catalog = load_json(ROOT / "registries/components/v0.2.3/catalog.json")
        fidelity = load_json(ROOT / "registries/components/v0.2.3/fidelity-reports.json")
        self.registry = registry_module.ComponentRegistry(self.catalog, fidelity)

    def test_bundle_matches_admitted_registry_and_lock(self):
        placement.SourceGeometry(self.bundle, self.registry)
        self.assertEqual(self.lock["registrySha256"], self.registry.fingerprint)
        self.assertFalse(self.lock["fullInputPackageReady"])
        ids = [item["logicalComponentId"] for item in self.bundle["components"]]
        self.assertEqual(ids, list(self.catalog["components"]))
        for item in self.bundle["components"]:
            logical_id = item["logicalComponentId"]
            self.assertEqual(self.lock["componentIrSha256"][logical_id], registry_module.digest(item))

    def test_changed_component_is_rejected(self):
        changed = deepcopy(self.bundle)
        changed["components"][0]["rootBounds"]["width"] += 1
        with self.assertRaisesRegex(ValueError, "Source geometry does not match admitted Component IR"):
            placement.SourceGeometry(changed, self.registry)


if __name__ == "__main__":
    unittest.main()
