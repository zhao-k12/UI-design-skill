"""Apply fixed structural templates to caller-supplied regions; no semantics/AI."""
from copy import deepcopy

PATTERNS = {
    "list-page": ("header", "query", "toolbar", "table", "pagination"),
    "detail-page": ("header", "summary", "detail"),
    "form-page": ("header", "form", "actions"),
    "dashboard-basic": ("header", "metrics", "content"),
    "sidebar-content": ("sidebar", "content"),
}


def instantiate(pattern: str, regions: dict[str, list[dict]], *, canvas_policy: str = "0.1.0") -> dict:
    if pattern not in PATTERNS:
        raise ValueError(f"unsupported_pattern: {pattern}")
    if canvas_policy not in ("0.1.0", "0.2.0-static-grow"):
        raise ValueError(f"unsupported_canvas_policy: {canvas_policy}")
    expected = set(PATTERNS[pattern])
    if set(regions) != expected or any(not isinstance(value, list) for value in regions.values()):
        raise ValueError(f"pattern_regions_mismatch: expected {', '.join(PATTERNS[pattern])}")
    token = lambda name: {"token": name}
    size = lambda mode: {"mode": mode}
    fixed = lambda name: {"mode": "fixed", "value": token(name)}
    fill_hug = {"width": size("fill"), "height": size("hug")}
    sections = []
    for region in PATTERNS[pattern]:
        children = deepcopy(regions[region])
        if region in ("query", "form", "metrics"):
            children = [{"id": f"pattern.{region}.grid", "type": "Grid", "layout": {**fill_hug, "gridColumns": 24, "gap": token("spacing.md"), "wrap": True}, "children": children}]
        elif region in ("toolbar", "actions"):
            children = [{"id": f"pattern.{region}.row", "type": "HorizontalStack", "layout": {**fill_hug, "gap": token("spacing.sm"), "wrap": True}, "children": children}]
        sections.append({"id": f"pattern.{region}", "type": "Section", "role": region, "layout": {**fill_hug, "direction": "vertical", "gap": token("spacing.md")}, "children": children})
    if pattern == "sidebar-content":
        sections[0]["layout"]["width"] = fixed("size.sidebar")
        sections = [{"id": "pattern.shell", "type": "HorizontalStack", "layout": {**fill_hug, "gap": token("spacing.md")}, "children": sections}]
    page = {
        "id": "pattern.page", "type": "Page",
        "layout": {"width": fixed("size.page"), "height": size("hug"), "direction": "vertical", "gap": token("spacing.section"), "padding": {edge: token("spacing.page") for edge in ("top", "right", "bottom", "left")}},
        "children": sections,
    }
    if canvas_policy == "0.2.0-static-grow":
        page["constraints"] = {"minHeight": token("size.page-min-height")}
    return {"layoutTreeVersion": "0.1.0", "pattern": pattern, "page": page}
