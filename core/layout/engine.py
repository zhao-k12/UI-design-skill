"""Deterministic, platform-neutral 24-grid and stack geometry for Layout Trees."""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

token_rules = import_module("core.design-rules.tokens")

AXES = ("width", "height")
EPSILON = 1e-6


class LayoutError(ValueError):
    def __init__(self, code, path, message):
        self.code, self.path = code, path
        super().__init__(message)


def pointer(parts):
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


class LayoutEngine:
    version = "0.1.0"

    def __init__(self, registry):
        self.registry = registry

    def run(self, tree):
        issues = []

        def issue(code, path, message, severity="error"):
            issues.append({"code": code, "path": pointer(path), "message": message, "severity": severity})

        try:
            json.dumps(tree, allow_nan=False)
            schema = json.loads((Path(__file__).resolve().parents[2] / "schemas" / "layout-tree.schema.json").read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            for error in Draft202012Validator(schema).iter_errors(tree):
                parts = tuple(error.absolute_path)
                code = "invalid_span" if "span" in parts else "invalid_padding" if "padding" in parts else "invalid_layout_tree"
                issue(code, parts, error.message)
        except (ValueError, TypeError) as exc:
            issue("invalid_layout_tree", (), str(exc))
        if issues:
            return self._result(tree, None, issues)

        for diagnostic in token_rules.check_references({"pages": [tree["page"]]}, self.registry):
            issues.append({**diagnostic, "path": diagnostic["path"].replace("/pages/0", "/page", 1), "severity": "error"})
        if issues:
            return self._result(tree, None, issues)

        seen = set()

        def preflight(node, path, depth, parent_type=None):
            if node["id"] in seen:
                issue("duplicate_node_id", (*path, "id"), node["id"])
            seen.add(node["id"])
            if depth > 12:
                issue("excessive_nesting", path, "Layout depth exceeds the V0.1 limit of 12")
            layout = node.get("layout", {})
            if "span" in layout and parent_type != "Grid":
                issue("invalid_span_context", (*path, "layout", "span"), "Span is only meaningful for direct Grid children")
            if "gridColumns" in layout and node["type"] != "Grid":
                issue("invalid_grid_context", (*path, "layout", "gridColumns"), "Grid columns require a Grid container")
            if node["type"] == "Grid":
                if layout.get("direction", "horizontal") != "horizontal":
                    issue("invalid_grid_direction", (*path, "layout", "direction"), "The 24 Grid flows in horizontal column order")
                if layout.get("alignment", {"main": "start", "cross": "start"}) != {"main": "start", "cross": "start"}:
                    issue("unsupported_grid_alignment", (*path, "layout", "alignment"), "V0.1 Grid uses start/start alignment; use an inner stack for other alignment")
            for index, child in enumerate(node.get("children", [])):
                if node["type"] == child["type"] and node["type"] in ("Frame", "Row", "Column", "HorizontalStack", "VerticalStack") and len(node["children"]) == 1 and not node.get("role") and not node.get("sourceIds"):
                    issue("unnecessary_nesting", path, "Single-child wrapper duplicates its child layout type", "warning")
                preflight(child, (*path, "children", index), depth + 1, node["type"])

        preflight(tree["page"], ("page",), 0)
        if any(item["severity"] == "error" for item in issues):
            return self._result(tree, None, issues)

        def scalar(value, path, categories=("size", "spacing", "radius")):
            if isinstance(value, dict):
                token_id = value["token"]
                try:
                    category = self.registry.token_type(token_id)
                    if category not in categories:
                        raise LayoutError("token_type_mismatch", path, f"Invalid geometry token type: {category}")
                    value = self.registry.resolve(token_id)
                except ValueError as exc:
                    if isinstance(exc, LayoutError):
                        raise
                    raise LayoutError(getattr(exc, "code", "invalid_token"), path, str(exc)) from exc
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise LayoutError("invalid_layout_value", path, "Expected a finite nonnegative numeric geometry value")
            return float(value)

        def mode(node, axis):
            return node.get("layout", {}).get(axis, {}).get("mode", "hug")

        def solve(node, assigned=(None, None), force=(False, False), path=("page",)):
            layout = node.get("layout", {})
            dimensions = []
            for index, axis in enumerate(AXES):
                spec = layout.get(axis, {"mode": "hug"})
                if spec["mode"] == "fixed":
                    value = scalar(spec["value"], (*path, "layout", axis, "value"))
                    if value <= 0:
                        raise LayoutError("invalid_fixed_size", (*path, "layout", axis), "Fixed dimensions must be positive")
                elif spec["mode"] == "fill" or force[index]:
                    if assigned[index] is None:
                        raise LayoutError("unbounded_fill", (*path, "layout", axis), "Fill needs a bounded parent dimension; no size is guessed")
                    value = assigned[index]
                else:
                    value = None
                dimensions.append(value)
            padding = [scalar(layout.get("padding", {}).get(edge, 0), (*path, "layout", "padding", edge), ("spacing",)) for edge in ("left", "top", "right", "bottom")]
            totals = (padding[0] + padding[2], padding[1] + padding[3])
            content = [None if dimensions[a] is None else max(0, dimensions[a] - totals[a]) for a in range(2)]
            for a in range(2):
                if dimensions[a] is not None and totals[a] > dimensions[a] + EPSILON:
                    issue("invalid_padding", (*path, "layout", "padding"), f"Padding exceeds {AXES[a]}")
            gap = scalar(layout.get("gap", 0), (*path, "layout", "gap"), ("spacing",))
            children = []
            if node["type"] == "Cell":
                for a in range(2):
                    if dimensions[a] is None:
                        measurement = node.get("measurement")
                        if measurement is None:
                            raise LayoutError("missing_measurement", path, f"Hug {AXES[a]} needs measured content size")
                        dimensions[a] = float(measurement[AXES[a]]) + totals[a]
            elif node["type"] == "Grid":
                inputs = node["children"]
                rows, current, spans = [], [], 0
                for index, child in enumerate(inputs):
                    span = child.get("layout", {}).get("span", 24)
                    if current and spans + span > 24:
                        if not layout.get("wrap", False):
                            raise LayoutError("grid_span_overflow", path, "Grid exceeds 24 columns while wrap is disabled")
                        rows.append(current)
                        current, spans = [], 0
                    current.append((index, child, span, spans))
                    spans += span
                if current:
                    rows.append(current)
                if content[0] is None:
                    unit = 0.0
                    for index, child in enumerate(inputs):
                        span = child.get("layout", {}).get("span", 24)
                        measured = solve(child, path=(*path, "children", index))
                        unit = max(unit, (measured["box"]["width"] - gap * (span - 1)) / span)
                    content[0] = max(0, unit) * 24 + (23 * gap if inputs else 0)
                    dimensions[0] = content[0] + totals[0]
                unit = (content[0] - 23 * gap) / 24 if inputs else 0
                if unit < -EPSILON:
                    raise LayoutError("grid_too_narrow", path, "Grid width cannot contain its declared column gaps")
                unit = max(0, unit)
                row_bound = None if content[1] is None or not rows else max(0, (content[1] - gap * (len(rows) - 1)) / len(rows))
                cursor = padding[1]
                for row in rows:
                    solved = []
                    for index, child, span, column in row:
                        slot_width = unit * span + gap * (span - 1)
                        result = solve(child, (slot_width, row_bound), path=(*path, "children", index))
                        if result["box"]["width"] > slot_width + EPSILON:
                            issue("grid_cell_overflow", (*path, "children", index), "Child exceeds its assigned span width")
                        result["box"].update(x=padding[0] + column * (unit + gap), y=cursor)
                        solved.append(result)
                    row_height = max((child["box"]["height"] for child in solved), default=0)
                    if row_bound is not None:
                        if row_height > row_bound + EPSILON:
                            issue("grid_row_overflow", path, "Content exceeds a bounded grid row")
                        row_height = row_bound
                    cursor += row_height + gap
                    children.extend(solved)
                if dimensions[1] is None:
                    dimensions[1] = (cursor - gap if rows else padding[1]) + padding[3]
            else:
                horizontal = layout.get("direction", "horizontal" if node["type"] in ("Row", "HorizontalStack") else "vertical") == "horizontal"
                main, cross = (0, 1) if horizontal else (1, 0)
                main_axis, cross_axis = AXES[main], AXES[cross]
                wrap = layout.get("wrap", False)
                if wrap and content[main] is None:
                    raise LayoutError("unbounded_wrap", path, "Wrap needs a bounded main dimension")
                records = []
                for index, child in enumerate(node["children"]):
                    child_path = (*path, "children", index)
                    fill = mode(child, main_axis) == "fill"
                    if wrap and mode(child, cross_axis) == "fill":
                        raise LayoutError("unsupported_wrap_cross_fill", child_path, "Wrapped cross-axis Fill requires explicit row metrics, not a guessed line height")
                    if fill:
                        if content[main] is None:
                            raise LayoutError("unbounded_fill", child_path, "Main-axis Fill cannot depend on a Hug parent")
                        constraint = child.get("constraints", {}).get("min" + main_axis.title())
                        if constraint is None and child.get("role") == "field" and main == 0:
                            constraint = {"token": "size.field-min"}
                        if wrap and constraint is None:
                            raise LayoutError("missing_wrap_basis", child_path, "Wrapped Fill needs an explicit minimum main size")
                        basis = scalar(constraint, child_path) if constraint is not None else 0
                        if child.get("role") == "field" and main == 0:
                            basis = max(basis, scalar({"token": "size.field-min"}, child_path))
                        records.append([index, child, fill, basis, None])
                    else:
                        assigned_child = [None, None]
                        assigned_child[cross] = content[cross]
                        result = solve(child, tuple(assigned_child), path=child_path)
                        records.append([index, child, fill, result["box"][main_axis], result])
                lines, line, used = [], [], 0.0
                for record in records:
                    addition = record[3] + (gap if line else 0)
                    if wrap and line and used + addition > content[main] + EPSILON:
                        lines.append(line)
                        line, used = [], 0.0
                    used += record[3] + (gap if line else 0)
                    line.append(record)
                if line:
                    lines.append(line)
                align = layout.get("alignment", {"main": "start", "cross": "start"})
                cross_cursor = padding[cross]
                widest = 0.0
                for line in lines:
                    occupied = sum(record[3] for record in line) + gap * (len(line) - 1)
                    remaining = 0 if content[main] is None else max(0, content[main] - occupied)
                    fills = sum(record[2] for record in line)
                    for record in line:
                        if record[2]:
                            assigned_child = [None, None]
                            assigned_child[main] = record[3] + remaining / fills
                            assigned_child[cross] = content[cross]
                            record[4] = solve(record[1], tuple(assigned_child), path=(*path, "children", record[0]))
                    actual_main = sum(record[4]["box"][main_axis] for record in line) + gap * (len(line) - 1)
                    natural_cross = max(record[4]["box"][cross_axis] for record in line)
                    line_cross = content[cross] if not wrap and content[cross] is not None else natural_cross
                    extra = 0 if content[main] is None else max(0, content[main] - actual_main)
                    step = gap + (extra / (len(line) - 1) if align["main"] == "space-between" and len(line) > 1 else 0)
                    main_cursor = padding[main] + (extra / 2 if align["main"] == "center" else extra if align["main"] == "end" else 0)
                    for index, child, _, _, result in line:
                        if align["cross"] == "stretch" and mode(child, cross_axis) != "fixed":
                            assigned_child = [result["box"]["width"], result["box"]["height"]]
                            assigned_child[cross] = line_cross
                            forced_child = [False, False]
                            forced_child[cross] = True
                            result = solve(child, tuple(assigned_child), tuple(forced_child), (*path, "children", index))
                        offset = max(0, line_cross - result["box"][cross_axis])
                        cross_position = cross_cursor + (offset / 2 if align["cross"] == "center" else offset if align["cross"] == "end" else 0)
                        result["box"]["x" if main == 0 else "y"] = main_cursor
                        result["box"]["y" if main == 0 else "x"] = cross_position
                        main_cursor += result["box"][main_axis] + step
                        children.append(result)
                    widest = max(widest, actual_main)
                    cross_cursor += line_cross + gap
                if dimensions[main] is None:
                    dimensions[main] = widest + totals[main]
                if dimensions[cross] is None:
                    dimensions[cross] = (cross_cursor - gap if lines else padding[cross]) + padding[cross + 2]
            result = {"id": node["id"], "type": node["type"], "box": {"x": 0.0, "y": 0.0, "width": dimensions[0], "height": dimensions[1]}, "children": children}
            if "role" in node:
                result["role"] = node["role"]
            if "sourceIds" in node:
                result["sourceIds"] = deepcopy(node["sourceIds"])
            for index, axis in enumerate(AXES):
                threshold = node.get("constraints", {}).get("min" + axis.title())
                if threshold is None and axis == "width" and node.get("role") == "field":
                    threshold = {"token": "size.field-min"}
                minimum = scalar(threshold, (*path, "constraints", "min" + axis.title())) if threshold is not None else None
                if axis == "width" and node.get("role") == "field":
                    minimum = max(minimum or 0, scalar({"token": "size.field-min"}, path))
                if minimum is not None and dimensions[index] + EPSILON < minimum:
                    issue("field_too_narrow" if axis == "width" and node.get("role") == "field" else "minimum_size_violation", path, f"Allocated {axis} is below the declared minimum")
            for index, child in enumerate(children):
                box = child["box"]
                if box["x"] < padding[0] - EPSILON or box["y"] < padding[1] - EPSILON or box["x"] + box["width"] > dimensions[0] - padding[2] + EPSILON or box["y"] + box["height"] > dimensions[1] - padding[3] + EPSILON:
                    issue("container_overflow", (*path, "children", index), "Child exceeds the parent content box")
            if node["type"] == "Page" and sum(child["type"] == "Section" for child in node["children"]) > 1:
                expected_gap = scalar({"token": "spacing.section"}, (*path, "layout", "gap"), ("spacing",))
                if abs(gap - expected_gap) > EPSILON:
                    issue("inconsistent_section_gap", (*path, "layout", "gap"), "Page section gap must use the declared section spacing")
                for a, b in zip(children, children[1:]):
                    if a["type"] == b["type"] == "Section" and not wrap:
                        actual_gap = b["box"]["x" if horizontal else "y"] - a["box"]["x" if horizontal else "y"] - a["box"][main_axis]
                        if abs(actual_gap - expected_gap) > EPSILON:
                            issue("inconsistent_section_gap", path, "Actual section distance differs from declared section spacing")
            return result

        skeleton = None
        try:
            skeleton = solve(tree["page"])
            def absolute(node, x=0, y=0):
                box = node["box"]
                origin_x, origin_y = x + box["x"], y + box["y"]
                box.update(x=origin_x, y=origin_y)
                for child in node["children"]:
                    absolute(child, origin_x, origin_y)
                for key in box:
                    box[key] = round(box[key], 6)
            absolute(skeleton)
        except LayoutError as exc:
            issue(exc.code, exc.path, str(exc))
        return self._result(tree, skeleton, issues)

    def _result(self, tree, skeleton, issues):
        unique = {json.dumps(item, sort_keys=True): item for item in issues}
        issues = sorted(unique.values(), key=lambda item: (item["path"], item["code"], item["message"]))
        failed = any(item["severity"] == "error" for item in issues)
        return {"scope": "layout", "status": "FAIL" if failed else "PASS", "engineVersion": self.version,
                "tokenRegistryVersion": self.registry.version, "tokenRegistrySha256": self.registry.fingerprint,
                "pattern": tree.get("pattern") if isinstance(tree, dict) else None,
                "skeleton": None if failed else skeleton, "issues": issues}
