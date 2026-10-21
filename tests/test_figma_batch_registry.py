"""The approved Figma batch becomes one immutable, narrowly scoped profile."""
from copy import deepcopy
from importlib import import_module
import unittest
from pathlib import Path
import tempfile

from adapters.component_bindings import BindingError, ComponentBindings
from scripts.build_figma_batch_registry import build, write
from scripts.migrate_compact_search_v027_figma import migrate
from scripts.run_figma_pipeline import run
from validators.ui_ir import ROOT, load_json

registry_module = import_module("core.component-resolver.registry")


class FigmaBatchRegistryTests(unittest.TestCase):
    def test_eighteen_fixed_components_are_admitted_in_one_profile(self):
        outputs = build()
        catalog, reports = outputs["catalog.json"], outputs["fidelity-reports.json"]
        registry = registry_module.ComponentRegistry(catalog, reports)
        self.assertEqual(len(catalog["components"]), 18)
        self.assertEqual(len(outputs["component-bindings-0.2.7-figma.json"]["bindings"]), 18)
        self.assertEqual(set(outputs["admission.json"]["bindings"]), {"figma"})
        self.assertEqual(catalog["components"]["form.datepicker.date.selected"]
                         ["contentScope"]["visibleText"], ["2024-01-01"])
        self.assertEqual(registry.fingerprint, outputs["admission.json"]["registrySha256"])
        binding = ComponentBindings(outputs["component-bindings-0.2.7-figma.json"],
                                    registry, platform="figma")
        for logical_id, entry in catalog["components"].items():
            self.assertEqual(registry.resolve(logical_id)["logicalId"], logical_id)
            self.assertEqual(binding.resolve(logical_id)["kind"], "component")
            self.assertEqual(entry["contentScope"]["kind"] in
                             ("fixed-native-content", "fixed-native-snapshot"), True)
        self.assertEqual(write(outputs), write(build()))
        self.assertEqual(load_json(ROOT / "registries/components/v0.2.6/catalog.json")
                         ["registryVersion"], "0.2.6")

    def test_scope_or_native_reference_tampering_is_rejected(self):
        outputs = build()
        catalog = deepcopy(outputs["catalog.json"])
        reports = deepcopy(outputs["fidelity-reports.json"])
        logical_id = "navigation.tree.expanded.departments"
        catalog["components"][logical_id]["contentScope"]["width"] += 1
        with self.assertRaisesRegex(registry_module.ComponentError,
                                    "Figma batch proof or fixed scope"):
            registry_module.ComponentRegistry(catalog, reports)
        registry = registry_module.ComponentRegistry(outputs["catalog.json"], reports)
        binding = deepcopy(outputs["component-bindings-0.2.7-figma.json"])
        binding["bindings"][logical_id]["variants"]["expanded"]["componentReference"] = "wrong"
        with self.assertRaisesRegex(BindingError, "audited native component"):
            ComponentBindings(binding, registry, platform="figma")

    def test_new_profile_runs_core_and_only_figma_preflight(self):
        self.assertEqual(migrate()["status"], "PASS")
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            output = Path(directory) / "run"
            qa = run(ROOT / "examples/user-management-compact-search-v027-figma",
                     output, "0vGWSRoLxBiVPXiZ8xJAX9", "v0.2.7-figma")
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["adapterPreflights"], {"figma": "PASS"})
            self.assertEqual(qa["developmentScope"], "FIGMA_ONLY")
            self.assertFalse((output / "penpot_preflight.json").exists())
            self.assertEqual(run(ROOT / "examples/user-management-compact-search-v027-figma",
                                 output, "0vGWSRoLxBiVPXiZ8xJAX9",
                                 "v0.2.7-figma")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
