import tempfile
import unittest
from pathlib import Path

from validators.architecture import check_core


class ArchitectureTests(unittest.TestCase):
    def scan(self, source, name="module.py"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core").mkdir()
            (root / "core" / name).write_text(source, encoding="utf-8")
            return check_core(root)

    def test_project_core_has_no_platform_dependency(self):
        self.assertEqual(check_core(Path(__file__).resolve().parents[1]), [])

    def test_platform_independent_python_is_allowed(self):
        self.assertEqual(self.scan('import json\nfrom pathlib import Path\nlogical_id = "form.input.default.medium"'), [])

    def test_platform_and_adapter_imports_are_rejected(self):
        for source in ("import figma", "from penpot.api import Client", "from adapters import figma", "from ..adapters.figma import emit", "import figma_sdk"):
            with self.subTest(source=source):
                self.assertTrue(self.scan(source))

    def test_dynamic_platform_import_is_rejected(self):
        self.assertTrue(self.scan('import importlib\nimportlib.import_module("penpot")'))
        self.assertTrue(self.scan('__import__("figma")'))
        self.assertTrue(self.scan('__import__(module_name)'))

    def test_platform_fields_are_rejected_in_python_and_json(self):
        for source in ('data = {"figmaNodeId": "123"}', 'def f(penpotShapeId): pass', 'node.figma_node_id = "1"'):
            with self.subTest(source=source):
                self.assertTrue(self.scan(source))
        self.assertTrue(self.scan('{"children": [{"penpotShapeId": "x"}]}', "tree.json"))

    def test_adapter_metadata_is_outside_core(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core").mkdir()
            metadata = root / "adapters" / "figma" / "metadata.json"
            metadata.parent.mkdir(parents=True)
            metadata.write_text('{"figmaNodeId": "real-platform-id"}', encoding="utf-8")
            self.assertEqual(check_core(root), [])

    def test_unparseable_and_uninspected_sources_fail_closed(self):
        self.assertTrue(self.scan("def ("))
        self.assertTrue(self.scan("{", "tree.json"))
        self.assertTrue(self.scan('import { figma } from "figma"', "module.js"))

    def test_missing_core_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(check_core(Path(directory)))


if __name__ == "__main__":
    unittest.main()
