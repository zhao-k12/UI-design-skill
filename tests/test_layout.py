from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validators.ui_ir import ROOT, load_json

tokens = import_module("core.design-rules.tokens")
engine = import_module("core.layout.engine")
patterns = import_module("core.layout.patterns")


def fixed(value):
    return {"mode": "fixed", "value": value}


def cell(identifier, width=40, height=20, **extra):
    return {"id": identifier, "type": "Cell", "measurement": {"width": width, "height": height, "source": {"kind": "test-fixture", "reference": "layout-unit-test"}}, **extra}


def tree(children, **layout):
    return {"layoutTreeVersion": "0.1.0", "pattern": "list-page", "page": {"id": "page", "type": "Page", "layout": {"width": fixed(400), "height": {"mode": "hug"}, **layout}, "children": children}}


def nodes(result):
    found = {}
    def visit(node):
        found[node["id"]] = node["box"]
        for child in node["children"]:
            visit(child)
    visit(result["skeleton"])
    return found


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.registry = tokens.TokenRegistry(load_json(ROOT / "registries/tokens/default.json"))
        self.engine = engine.LayoutEngine(self.registry)

    def run_valid(self, document):
        result = self.engine.run(document)
        self.assertEqual(result["status"], "PASS", result["issues"])
        return nodes(result)

    def assert_failure(self, document, code):
        result = self.engine.run(document)
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNone(result["skeleton"])
        self.assertIn(code, {item["code"] for item in result["issues"]}, result["issues"])

    def test_list_fixture_is_deterministic_and_preserves_input(self):
        document = load_json(ROOT / "examples/user-management.layout-tree.json")
        original = deepcopy(document)
        outputs = [self.engine.run(document) for _ in range(5)]
        self.assertTrue(all(result == outputs[0] for result in outputs))
        self.assertEqual(outputs[0]["status"], "PASS", outputs[0]["issues"])
        self.assertEqual(document, original)
        boxes = nodes(outputs[0])
        self.assertEqual(boxes["pattern.page"], {"x": 0, "y": 0, "width": 1440, "height": 620})
        self.assertEqual(boxes["fixture.field.0"]["width"], 336)
        self.assertEqual(boxes["fixture.field.3"]["x"], 1080)

    def test_vertical_stack_hug_padding_and_gap(self):
        document = tree([cell("a", 40, 20), cell("b", 60, 30)], gap=8, padding={side: 4 for side in ("top", "right", "bottom", "left")})
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["y"], 4)
        self.assertEqual(boxes["b"]["y"], 32)
        self.assertEqual(boxes["page"]["height"], 66)

    def test_horizontal_stack_and_space_between(self):
        boxes = self.run_valid(tree([cell("a", 40), cell("b", 60)], direction="horizontal", gap=8, alignment={"main": "space-between", "cross": "start"}))
        self.assertEqual(boxes["a"]["x"], 0)
        self.assertEqual(boxes["b"]["x"], 340)
        self.assertEqual(boxes["page"]["height"], 20)

    def test_fill_distributes_remaining_space_in_both_directions(self):
        document = tree([cell("a", layout={"width": {"mode": "fill"}}), cell("b", layout={"width": {"mode": "fill"}}), cell("c", 100)], direction="horizontal", gap=8)
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["width"], 142)
        self.assertEqual(boxes["b"]["x"], 150)
        self.assertEqual(boxes["c"]["x"], 300)
        document = tree([cell("a", layout={"height": {"mode": "fill"}}), cell("b", layout={"height": {"mode": "fill"}})], height=fixed(100), gap=8)
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["height"], 46)
        self.assertEqual(boxes["b"]["y"], 54)

    def test_alignment_center_end_and_stretch(self):
        for main, expected in (("center", 180), ("end", 360)):
            boxes = self.run_valid(tree([cell("a", 40, 20)], direction="horizontal", height=fixed(100), alignment={"main": main, "cross": "center"}))
            self.assertEqual(boxes["a"]["x"], expected)
            self.assertEqual(boxes["a"]["y"], 40)
        boxes = self.run_valid(tree([cell("a", 40, 20)], direction="horizontal", height=fixed(100), alignment={"main": "start", "cross": "stretch"}))
        self.assertEqual(boxes["a"]["height"], 100)

    def test_horizontal_and_vertical_wrap(self):
        boxes = self.run_valid(tree([cell("a", 140, 20), cell("b", 140, 30), cell("c", 140, 40)], width=fixed(300), direction="horizontal", gap=8, wrap=True))
        self.assertEqual(boxes["b"]["x"], 148)
        self.assertEqual(boxes["c"]["y"], 38)
        self.assertEqual(boxes["page"]["height"], 78)
        boxes = self.run_valid(tree([cell("a", 20, 40), cell("b", 30, 40), cell("c", 40, 40)], width={"mode": "hug"}, height=fixed(100), direction="vertical", gap=8, wrap=True))
        self.assertEqual(boxes["c"]["x"], 38)
        self.assertEqual(boxes["page"]["width"], 78)

    def test_wrapped_fill_uses_minimum_basis(self):
        document = tree([cell(name, 160, 20, role="field", layout={"width": {"mode": "fill"}}) for name in ("a", "b", "c")], width=fixed(400), direction="horizontal", gap=8, wrap=True)
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["width"], 196)
        self.assertEqual(boxes["b"]["x"], 204)
        self.assertEqual(boxes["c"]["width"], 400)
        self.assertEqual(boxes["c"]["y"], 28)

    def grid(self, children, **layout):
        return tree([{"id": "grid", "type": "Grid", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "gridColumns": 24, "gap": 8, "wrap": True, **layout}, "children": children}], width=fixed(1200))

    def test_grid_24_columns_and_row_wrap(self):
        document = self.grid([cell(f"field.{index}", 180, 32, role="field", layout={"span": 6, "width": {"mode": "fill"}}) for index in range(5)])
        boxes = self.run_valid(document)
        self.assertEqual(boxes["field.0"]["width"], 294)
        self.assertEqual(boxes["field.3"]["x"], 906)
        self.assertEqual(boxes["field.4"]["y"], 40)
        self.assertEqual(boxes["grid"]["height"], 72)

    def test_grid_hug_width_and_bounded_fill_rows(self):
        document = self.grid([cell("a", 100, 20, layout={"span": 12}), cell("b", 100, 30, layout={"span": 12})], width={"mode": "hug"})
        boxes = self.run_valid(document)
        self.assertEqual(boxes["grid"]["width"], 208)
        document = self.grid([cell("a", layout={"span": 24, "width": {"mode": "fill"}, "height": {"mode": "fill"}}), cell("b", layout={"span": 24, "width": {"mode": "fill"}, "height": {"mode": "fill"}})], height=fixed(100))
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["height"], 46)
        self.assertEqual(boxes["b"]["y"], 54)

    def test_grid_errors_include_span_width_and_wrap(self):
        document = self.grid([cell("a", layout={"span": 25})])
        self.assert_failure(document, "invalid_span")
        self.assert_failure(self.grid([cell("a", layout={"span": 24}), cell("b", layout={"span": 24})], wrap=False), "grid_span_overflow")
        self.assert_failure(self.grid([cell("a", 400, layout={"span": 6})]), "grid_cell_overflow")
        document = self.grid([cell("a")])
        document["page"]["layout"]["width"] = fixed(100)
        self.assert_failure(document, "grid_too_narrow")

    def test_fields_minimum_padding_and_overflow(self):
        self.assert_failure(tree([cell("field", 100, role="field")]), "field_too_narrow")
        self.assert_failure(tree([cell("a", 500)]), "container_overflow")
        self.assert_failure(tree([], width=fixed(20), padding={side: 16 for side in ("top", "right", "bottom", "left")}), "invalid_padding")
        self.assert_failure(tree([], padding={side: -1 for side in ("top", "right", "bottom", "left")}), "invalid_padding")

    def test_field_constraints_cannot_weaken_project_minimum(self):
        self.assert_failure(tree([cell("field", 120, role="field", constraints={"minWidth": 100})]), "field_too_narrow")
        document = tree([cell(name, 160, role="field", constraints={"minWidth": 100}, layout={"width": {"mode": "fill"}}) for name in ("a", "b", "c")], direction="horizontal", gap=8, wrap=True)
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["width"], 196)
        self.assertEqual(boxes["c"]["y"], 28)

    def test_missing_measurement_and_unbounded_cycles_fail(self):
        self.assert_failure(tree([{"id": "missing", "type": "Cell"}]), "missing_measurement")
        self.assert_failure(tree([cell("a", layout={"height": {"mode": "fill"}})]), "unbounded_fill")
        self.assert_failure(tree([cell("a")], width={"mode": "hug"}, direction="horizontal", wrap=True), "unbounded_wrap")
        self.assert_failure(tree([cell("a", layout={"width": {"mode": "fill"}})], direction="horizontal", wrap=True), "missing_wrap_basis")
        self.assert_failure(tree([cell("a", layout={"height": {"mode": "fill"}})], height=fixed(100), direction="horizontal", wrap=True), "unsupported_wrap_cross_fill")

    def test_coordinates_bad_tokens_and_duplicate_ids_fail(self):
        document = tree([cell("a"), cell("a")])
        self.assert_failure(document, "duplicate_node_id")
        document = tree([cell("a")])
        document["page"]["x"] = 10
        self.assert_failure(document, "invalid_layout_tree")
        self.assert_failure(tree([cell("a")], gap={"token": "spacing.missing"}), "missing_token")
        self.assert_failure(tree([cell("a")], gap=17), "unregistered_visual_value")

    def test_grid_properties_in_wrong_context_are_not_silently_ignored(self):
        self.assert_failure(tree([cell("a", layout={"span": 6})]), "invalid_span_context")
        self.assert_failure(tree([cell("a")], gridColumns=24), "invalid_grid_context")
        self.assert_failure(self.grid([cell("a")], direction="vertical"), "invalid_grid_direction")
        self.assert_failure(self.grid([cell("a")], alignment={"main": "center", "cross": "start"}), "unsupported_grid_alignment")

    def test_nested_absolute_coordinates_minimum_height_and_depth_limit(self):
        document = tree([{"id": "outer", "type": "Column", "layout": {"padding": {side: 4 for side in ("top", "right", "bottom", "left")}}, "children": [cell("a")]}], padding={side: 8 for side in ("top", "right", "bottom", "left")})
        boxes = self.run_valid(document)
        self.assertEqual(boxes["a"]["x"], 12)
        self.assertEqual(boxes["a"]["y"], 12)
        self.assert_failure(tree([cell("a", constraints={"minHeight": 40})]), "minimum_size_violation")
        nested = cell("leaf")
        for index in range(13):
            nested = {"id": f"nested.{index}", "type": "Column", "children": [nested]}
        self.assert_failure(tree([nested]), "excessive_nesting")

    def test_section_gap_and_unnecessary_nesting(self):
        children = [{"id": f"section.{index}", "type": "Section", "children": [cell(f"a.{index}")]} for index in range(2)]
        self.assert_failure(tree(children, gap=8), "inconsistent_section_gap")
        self.run_valid(tree(children, gap={"token": "spacing.section"}))
        document = tree([{"id": "outer", "type": "Column", "children": [{"id": "inner", "type": "Column", "children": [cell("a")]}]}])
        result = self.engine.run(document)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("unnecessary_nesting", {item["code"] for item in result["issues"]})
        self.assertEqual(result["issues"][0]["severity"], "warning")

    def test_all_five_patterns_execute_and_preserve_supplied_regions(self):
        for name, names in patterns.PATTERNS.items():
            with self.subTest(pattern=name):
                regions = {region: [cell(f"input.{region}", 180, 32)] for region in names}
                original = deepcopy(regions)
                document = patterns.instantiate(name, regions)
                boxes = self.run_valid(document)
                self.assertTrue(all(f"input.{region}" in boxes for region in names))
                self.assertEqual(regions, original)
                self.assertEqual(document, patterns.instantiate(name, regions))
        with self.assertRaises(ValueError):
            patterns.instantiate("unknown", {})
        with self.assertRaises(ValueError):
            patterns.instantiate("form-page", {"header": []})

    def test_cli_persists_repeatable_success_and_clears_stale_skeleton(self):
        command = [sys.executable, "-X", "utf8", "-m", "validators.layout"]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            args = command + [str(ROOT / "examples/user-management.layout-tree.json"), "--output-dir", str(output)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(first.returncode, 0, first.stderr)
            bytes_before = (output / "layout_skeleton.json").read_bytes()
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(bytes_before, (output / "layout_skeleton.json").read_bytes())
            invalid = Path(directory) / "invalid.json"
            invalid.write_text(json.dumps(tree([{"id": "missing", "type": "Cell"}])), encoding="utf-8")
            failed = subprocess.run(command + [str(invalid), "--output-dir", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertIsNone(load_json(output / "layout_skeleton.json")["skeleton"])
            self.assertEqual(load_json(output / "layout_qa_report.json")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
