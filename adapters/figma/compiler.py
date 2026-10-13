"""Deterministic UI-IR preflight and Figma Plugin API translation payload."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path

from validators.ui_ir import ROOT, validate_document
from adapters.component_bindings import validate_instance_scope
from adapters.default_font import binding_for

tokens_module = import_module("core.design-rules.tokens")
components_module = import_module("core.component-resolver.registry")
ADAPTER_VERSION = "0.1.0"
CONTAINERS = {"Page", "Frame", "Section", "Grid", "Row", "Column", "VerticalStack", "HorizontalStack"}


def prepare(document, tokens, components, component_bindings, icons, icon_bindings=None, font_bindings=None, *, file_reference=None):
    """Return no executable plan on any failed preflight. Does not mutate input or canvas."""
    issues = validate_document(document)
    report = {"scope": "figma_adapter_preflight", "adapterVersion": ADAPTER_VERSION, "status": "FAIL",
              "nativeExecution": "NOT_RUN", "issues": issues, "plan": None}
    if issues:
        return report
    issues.extend(tokens_module.check_references(document, tokens))
    icon_bindings = icon_bindings or {"bindings": {}}
    font_bindings = font_bindings or {}
    def issue(code, node_id, detail):
        issues.append({"code": code, "nodeId": node_id, "detail": detail})
    def value(item):
        if isinstance(item, dict):
            return tokens.resolve(item["token"]) if set(item) == {"token"} else {key: value(child) for key, child in item.items()}
        if isinstance(item, list):
            return [value(child) for child in item]
        return deepcopy(item)
    def size(item):
        item = deepcopy(item or {"mode": "hug"})
        if item["mode"] == "fixed":
            item["value"] = value(item["value"])
        return item
    if getattr(components, "scope", "production") != "production" or icons.snapshot["scope"] != "production":
        issue("test_fixture_forbidden", "", "Production adapters reject test registries")
    pages = []
    def translate(node, available_width=None, parent_direction=None):
        layout = node.get("layout", {})
        style = node.get("style", {})
        kind, node_id = node["type"], node["id"]
        direction = layout.get("direction", "horizontal" if kind in ("Row", "HorizontalStack", "Grid") else "vertical")
        width, height = size(layout.get("width")), size(layout.get("height"))
        padding = {side: value(layout.get("padding", {}).get(side, 0)) for side in ("top", "right", "bottom", "left")}
        actual_width = width.get("value") if width["mode"] == "fixed" else available_width if width["mode"] == "fill" else None
        result = {"id": node_id, "name": node.get("name", node_id), "type": kind,
                  "layout": {"width": width, "height": height, "padding": padding,
                             "gap": value(layout.get("gap", 0)), "direction": direction,
                             "wrap": layout.get("wrap", False), "alignment": layout.get("alignment", {"main": "start", "cross": "start"})},
                  "style": {key: value(item) for key, item in style.items()}}
        if "spacingToken" in style:
            issue("unsupported_spacing_role", node_id, "spacingToken has no unambiguous native property; use layout gap/padding")
        if layout.get("wrap") and direction != "horizontal":
            issue("unsupported_vertical_wrap", node_id, "Native wrapping is horizontal only")
        if style.get("colorToken") and kind != "Text":
            issue("unsupported_color_target", node_id, "Container paint must use style.fill explicitly")
        if kind == "Text" and "radius" in style:
            issue("unsupported_text_radius", node_id, "Native text does not expose corner radius")
        if kind == "Page" and (width["mode"] == "fill" or height["mode"] == "fill"):
            issue("unbounded_page_fill", node_id, "Top-level Page has no auto-layout parent")
        if kind == "Text":
            result["text"] = node["text"]
            typography = result["style"].get("typographyToken")
            if not typography:
                issue("missing_typography", node_id, "Text must declare a registered typographyToken")
            else:
                key = f"{typography['fontFamily']}:{typography['fontWeight']}"
                binding = binding_for(typography, font_bindings, platform="figma", file_reference=file_reference)
                valid_binding = (isinstance(binding, dict) and set(binding) in ({"family", "style"}, {"family", "style", "variationSettings"}) and
                                 (typography["fontFamily"] == "platform-default" or binding.get("family") == typography["fontFamily"])
                                 and isinstance(binding.get("style"), str) and bool(binding["style"]))
                if valid_binding and "variationSettings" in binding:
                    valid_binding = binding["variationSettings"] == {"wght": typography["fontWeight"]}
                if not valid_binding:
                    issue("missing_font_binding", node_id, "Discover exact native font style: " + key)
                else:
                    result["fontName"] = deepcopy(binding)
            if width["mode"] != "hug" and height["mode"] == "fill":
                issue("unsupported_text_height_fill", node_id, "Wrapped text requires content-driven height")
        elif kind == "ComponentInstance":
            try:
                choice = components.resolve(node["componentId"], node.get("variant"))
                validate_instance_scope(node, choice["descriptor"], width, height)
                reference = component_bindings.resolve(node["componentId"], node.get("variant"))
                if reference["fileReference"] != file_reference:
                    issue("unsupported_remote_component", node_id, "V0.1 requires an admitted component in this target file")
                result["componentReference"] = reference["componentReference"]
                result["fidelityReportSha256"] = choice["descriptor"]["fidelity"]["reportSha256"]
            except ValueError as exc:
                issue(getattr(exc, "code", "invalid_component_binding"), node_id, str(exc))
            if node.get("props") or node.get("slots"):
                issue("unsupported_component_content", node_id, "Props/slot injection needs declared native property mappings; no visual replacement")
            if style:
                issue("unsupported_component_style_override", node_id, "Do not alter admitted component visuals")
            if width["mode"] == "hug" or height["mode"] == "hug":
                issue("unsupported_instance_hug", node_id, "Declare explicit fixed/fill instance size; do not detach to emulate Hug")
        elif kind == "IconInstance":
            try:
                entry = icons.resolve(node["iconId"])["descriptor"]
                binding = icon_bindings.get("bindings", {}).get(node["iconId"])
                if not binding:
                    issue("missing_icon_reference", node_id, "Source-ready SVG still requires a verified native component")
                elif (icon_bindings.get("registrySha256") != icons.fingerprint or icon_bindings.get("scope") != "production" or
                      binding.get("svgSha256") != entry["svgSha256"] or binding.get("fileReference") != file_reference or
                      not isinstance(binding.get("componentReference"), str) or not binding["componentReference"]):
                    issue("icon_binding_mismatch", node_id, "Native icon must match exact source hash, scope, registry and file")
                else:
                    result["componentReference"] = binding["componentReference"]
                    result["svgSha256"] = entry["svgSha256"]
            except ValueError as exc:
                issue(getattr(exc, "code", "invalid_icon_binding"), node_id, str(exc))
            if width["mode"] != "fixed" or height["mode"] != "fixed":
                issue("unsupported_icon_sizing", node_id, "Icon instances require fixed declared geometry")
            if style:
                issue("unsupported_icon_style_override", node_id, "Use source component paint; no arbitrary SVG modification")
        elif kind in ("Image", "Divider"):
            issue("unsupported_node", node_id, kind + " translation not implemented in TASK-009")
        if kind not in CONTAINERS and any(k in layout for k in ("gap", "padding", "wrap", "direction", "gridColumns", "alignment")):
            issue("unsupported_leaf_layout", node_id, "Container layout on a leaf would be silently ignored")
        if style.get("typographyToken") and kind != "Text":
            issue("unsupported_typography_target", node_id, "Typography only applies to native text")
        if kind == "Grid":
            if layout.get("wrap"):
                issue("unsupported_grid_wrap", node_id, "Grid uses explicit span-based row grouping; native vertical Wrap is not equivalent")
            if direction != "horizontal" or layout.get("alignment", {"main": "start", "cross": "start"}) != {"main": "start", "cross": "start"}:
                issue("unsupported_grid_alignment", node_id, "Grid24 supports horizontal start/start")
            if actual_width is None:
                issue("unbounded_grid_width", node_id, "Grid needs resolved fixed or vertical-parent Fill width")
            else:
                inner = actual_width - padding["left"] - padding["right"]
                gap = result["layout"]["gap"]
                unit = (inner - 23 * gap) / 24
                if unit <= 0:
                    issue("grid_overflow", node_id, "Grid padding/gaps exhaust available width")
                result["gridWidth"] = actual_width
                result["gridCells"] = []
                row, occupied = 0, 0
                for child in node["children"]:
                    span = child.get("layout", {}).get("span", 24)
                    if occupied + span > 24:
                        row, occupied = row + 1, 0
                    result["gridCells"].append({"id": child["id"], "row": row, "width": unit * span + gap * (span - 1)})
                    occupied += span
        elif "gridColumns" in layout or ("span" in layout and parent_direction != "grid"):
            issue("unsupported_grid_context", node_id, "Grid columns/span require a Grid24 parent")
        if kind in CONTAINERS:
            inner_width = actual_width - padding["left"] - padding["right"] if actual_width is not None else None
            children = []
            for child in node["children"]:
                child_width = inner_width if direction == "vertical" else None
                if kind == "Grid" and "gridCells" in result:
                    child_width = next(cell["width"] for cell in result["gridCells"] if cell["id"] == child["id"])
                children.append(translate(child, child_width, "grid" if kind == "Grid" else direction))
            result["children"] = children
        return result
    if issues:
        return report
    for page in document["pages"]:
        try:
            pages.append(translate(page))
        except (ValueError, KeyError, TypeError) as exc:
            issue(getattr(exc, "code", "invalid_translation"), page["id"], str(exc))
    if issues:
        return report
    report["status"] = "PASS"
    report["plan"] = {"adapterVersion": ADAPTER_VERSION, "documentId": document["documentId"],
                      "uiIrSha256": components_module.digest(document), "tokensSha256": tokens.fingerprint,
                      "componentsSha256": components.fingerprint, "iconsSha256": icons.fingerprint,
                      "fileReference": file_reference, "pages": pages}
    return report


def script_for_page(plan, page_index=0, *, page_reference=None):
    """One page per host call; literal serialized payload, never interpolated source strings."""
    payload = {key: deepcopy(value) for key, value in plan.items() if key != "pages"}
    payload["page"] = deepcopy(plan["pages"][page_index])
    payload["pageReference"] = page_reference
    runtime = (Path(__file__).parent / "runtime.js").read_text(encoding="utf-8")
    return "const payload = " + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ";\n" + runtime + "\nreturn await executeFigmaAdapter(figma, payload);\n"
