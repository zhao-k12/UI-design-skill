"""Independent native readback validation. Structural PASS is not final fidelity acceptance."""
import argparse
import base64
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image
from validators.ui_ir import load_json


def validate_output(plan, execution, capture, page_index=0):
    issues = []
    def fail(code, node_id="", detail=""):
        issues.append({"code":code, "uiIrId":node_id, "detail":detail})
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    def equal(a, b):
        return number(a) and number(b) and abs(a-b) <= 1e-6
    def name(value):return '/'.join(part.strip() for part in value.split('/')) if isinstance(value,str) else value
    def index(rows, key, code):
        if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get(key), str) for r in rows):
            fail(code); return {}
        result = {r[key]:r for r in rows}
        if len(result) != len(rows): fail(code)
        return result
    report = {"scope":"penpot_independent_structure_qa", "status":"FAIL", "structuralStatus":"FAIL",
              "finalAcceptance":"NOT_RUN", "fidelityGate":"NOT_RUN", "issues":issues}
    if not all(isinstance(v, dict) for v in (plan, execution, capture)):
        fail("invalid_qa_input"); return report
    if plan.get("platform") != "penpot" or execution.get("status") != "EXECUTED" or execution.get("scope") != "penpot_native_translation":
        fail("native_execution_missing")
    for key in ("adapterVersion", "uiIrSha256", "tokensSha256", "componentsSha256", "iconsSha256", "fileReference"):
        if not plan.get(key) or execution.get(key) != plan[key]: fail("execution_input_mismatch", detail=key)
    if (capture.get("status") != "CAPTURED" or capture.get("platform") != "penpot" or
        capture.get("scope") != "production" or capture.get("evidenceKind") != "native-platform-export" or
        capture.get("exporterVersion") not in ("penpot-native-output-v0.1.0","penpot-native-output-v0.1.1")):
        fail("native_capture_missing")
    for key in ("fileReference", "pageReference", "rootReference"):
        if not execution.get(key) or capture.get(key) != execution[key]: fail("capture_identity_mismatch", detail=key)
    if capture.get("createdNodeIds") != [] or capture.get("mutatedNodeIds") != []: fail("capture_wrote_canvas")
    if type(capture.get("fileRevision")) is not int or capture["fileRevision"] < 0: fail("invalid_capture_revision")
    if execution.get("mutatedNodeIds") != []: fail("execution_mutated_existing_nodes")
    actual = index(capture.get("evidence"), "uiIrId", "invalid_readback_nodes")
    tree = index(capture.get("topology"), "nodeId", "invalid_native_tree")
    node_map = execution.get("nodeMap")
    if not isinstance(node_map, dict): fail("invalid_execution_node_map"); node_map = {}
    if any(not isinstance(k,str) or not isinstance(v,str) for k,v in node_map.items()):
        fail("invalid_execution_node_map"); node_map = {}
    if len(set(node_map.values())) != len(node_map): fail("duplicate_execution_nodes")
    created = execution.get("createdNodeIds", [])
    if not isinstance(created, list) or any(not isinstance(v,str) for v in created) or len(set(created)) != len(created):
        fail("invalid_creation_ledger"); created = []
    if set(created) - {execution.get("pageReference")} != set(tree): fail("creation_ledger_tree_mismatch")
    helpers = execution.get("helperNodeIds", [])
    if not isinstance(helpers, list) or any(not isinstance(v,str) or v not in tree for v in helpers):
        fail("invalid_helper_ledger"); helpers = []
    root_id = execution.get("rootReference")
    if root_id not in tree: fail("missing_root")
    for node_id, item in tree.items():
        child_ids = item.get("childNodeIds")
        if 'nativeStackChildNodeIds' in item and (item.get('childOrderNormalization')!='penpot-stack-to-layout-reverse' or item['nativeStackChildNodeIds']!=list(reversed(child_ids or []))):fail('invalid_child_order_normalization',detail=node_id)
        if (not isinstance(child_ids,list) or any(not isinstance(c,str) for c in child_ids) or
            len(set(child_ids)) != len(child_ids) or
            set(child_ids) != {i for i,n in tree.items() if n.get("parentReference") == node_id}):
            fail("invalid_native_children",detail=node_id)
        if not isinstance(item.get("parentReference"), str):
            fail("invalid_native_parent", detail=node_id); continue
        ancestor, visited = node_id, set()
        while ancestor != root_id:
            if not isinstance(ancestor,str) or ancestor not in tree or ancestor in visited:
                fail("native_node_outside_root", detail=node_id); break
            visited.add(ancestor); ancestor = tree[ancestor].get("parentReference")
    modes = {"fixed":"fix", "fill":"fill", "hug":"auto"}
    expected_ids = set()
    try: page = plan["pages"][page_index]
    except (KeyError, IndexError, TypeError): fail("missing_plan_page"); return report
    if node_map.get(page.get("id")) != root_id: fail("logical_root_mismatch")
    def walk(spec, parent=None):
        logical_id = spec["id"]; expected_ids.add(logical_id)
        entry = actual.get(logical_id)
        if not entry: fail("missing_readback_node", logical_id); return
        if capture.get('exporterVersion')=='penpot-native-output-v0.1.1' and (entry.get('rotation')!=0 or entry.get('flipX') is not False or entry.get('flipY') is not False or entry.get('hidden') is not False or entry.get('visible') is not True or entry.get('blendMode')!='normal' or entry.get('shadows')!=[] or entry.get('blur') is not None):fail('native_render_state_mismatch',logical_id)
        node_id = entry.get("nodeId")
        if node_map.get(logical_id) != node_id or node_id not in tree: fail("readback_identity_mismatch", logical_id)
        expected_type = "text" if spec["type"] == "Text" else None if spec.get("componentReference") else "board"
        if expected_type and entry.get("type") != expected_type: fail("native_type_mismatch", logical_id)
        if name(entry.get("name")) != name(f"UI-IR/{plan['documentId']}/{logical_id}" if spec["type"] == "Page" else spec["name"]): fail("native_name_mismatch", logical_id)
        for key in ("type","name","parentReference","x","y","width","height"):
            if node_id in tree and entry.get(key) != tree[node_id].get(key): fail("readback_tree_mismatch", logical_id, key)
        if parent:
            chain = entry.get("parentReference")
            if parent["type"] == "Grid":
                cell = tree.get(chain, {}); row = tree.get(cell.get("parentReference"), {})
                expected_cell = next(c for c in parent["gridCells"] if c["id"] == logical_id)
                if (chain not in helpers or row.get("nodeId") not in helpers or row.get("parentReference") != node_map.get(parent["id"]) or
                    not equal(cell.get("width"), expected_cell["width"]) or
                    name(cell.get("name")) != f"{parent['id']}/grid-cell/{logical_id}" or
                    name(row.get("name")) != f"{parent['id']}/grid-row/{expected_cell['row']}"):
                    fail("native_grid_structure_mismatch", logical_id)
                if spec["layout"]["width"]["mode"] == "fill" and not equal(entry.get("width"),expected_cell["width"]):
                    fail("native_grid_span_mismatch", logical_id)
            elif chain != node_map.get(parent["id"]): fail("native_parent_mismatch", logical_id)
        for axis, prop in (("width","horizontalSizing"),("height","verticalSizing")):
            size = spec["layout"][axis]; mode = modes[size["mode"]]
            if parent and parent["type"] != "Grid" and parent["layout"]["alignment"]["cross"] == "stretch":
                cross = "width" if parent["layout"]["direction"] == "vertical" else "height"
                if axis == cross and mode == "auto": mode = "fill"
            if entry.get(prop) != mode: fail("native_sizing_mismatch", logical_id, axis)
            if not number(entry.get(axis)) or entry[axis] <= 0: fail("invalid_native_size", logical_id, axis)
            elif size["mode"] == "fixed" and not equal(entry[axis], size["value"]): fail("native_fixed_size_mismatch", logical_id, axis)
        if expected_type == "board":
            f = entry.get("flex", {}); l = spec["layout"]
            if (f.get("dir") != ("column" if spec["type"] == "Grid" or l["direction"] == "vertical" else "row") or
                f.get("wrap") != ("wrap" if l["wrap"] else "nowrap") or
                f.get("rowGap") != l["gap"] or f.get("columnGap") != l["gap"] or
                f.get("justifyContent") != l["alignment"]["main"] or f.get("alignItems") != l["alignment"]["cross"] or
                entry.get("clipContent") is not False): fail("native_layout_mismatch", logical_id)
            for side, value in l["padding"].items():
                if f.get(side + "Padding") != value: fail("native_padding_mismatch", logical_id, side)
            if spec["type"] != "Grid":
                if tree.get(node_id,{}).get("childNodeIds") != [node_map.get(c["id"]) for c in spec.get("children",[])]:
                    fail("native_child_order_mismatch",logical_id)
            else:
                rows = {}
                for cell in spec["gridCells"]:
                    cell_id = actual.get(cell["id"],{}).get("parentReference")
                    wrapper = tree.get(cell_id,{})
                    row_id = wrapper.get("parentReference")
                    rows.setdefault(row_id,[]).append(cell_id)
                    if wrapper.get("childNodeIds") != [node_map.get(cell["id"])]: fail("native_grid_structure_mismatch",cell["id"])
                if tree.get(node_id,{}).get("childNodeIds") != list(rows): fail("native_child_order_mismatch",logical_id)
                for row_id,children in rows.items():
                    if tree.get(row_id,{}).get("childNodeIds") != children: fail("native_child_order_mismatch",logical_id)
        if expected_type == "text":
            b, t = spec["fontBinding"], spec["style"]["typographyToken"]
            pairs = {"characters":spec["text"], "fontId":b["fontId"], "fontFamily":b["family"], "fontVariantId":b["fontVariantId"],
                     "fontStyle":b["style"], "fontWeight":str(b["weight"]), "fontSize":str(t["fontSize"]),
                     "lineHeight":str(t["lineHeight"]/t["fontSize"]), "letterSpacing":str(t["letterSpacing"])}
            for key, value in pairs.items():
                if key in ("fontWeight","fontSize","lineHeight","letterSpacing"):
                    try: matches = isinstance(entry.get(key),str) and math.isfinite(float(entry[key])) and float(entry[key]) == float(value)
                    except (ValueError, TypeError): matches = False
                else: matches = entry.get(key) == value
                if not matches: fail("native_text_mismatch", logical_id, key)
            grow = "auto-width" if spec["layout"]["width"]["mode"] == "hug" else "fixed" if spec["layout"]["height"]["mode"] == "fixed" else "auto-height"
            if entry.get("growType") != grow: fail("native_text_growth_mismatch",logical_id)
        if not spec.get("componentReference"):
            style = spec["style"]
            hex_color = style.get("colorToken",style.get("fill")) if expected_type == "text" else style.get("fill")
            if hex_color:
                opacity = int(hex_color[7:9],16)/255 if len(hex_color)==9 else 1
                fills = entry.get("fills")
                if (not isinstance(fills,list) or len(fills)!=1 or not isinstance(fills[0],dict) or
                    str(fills[0].get("fillColor","")).lower()!=hex_color[:7].lower() or fills[0].get("fillOpacity")!=opacity):
                    fail("native_paint_mismatch",logical_id)
            elif expected_type == "board" and entry.get("fills")!=[]: fail("native_paint_mismatch",logical_id)
            if entry.get("opacity")!=style.get("opacity",1): fail("native_opacity_mismatch",logical_id)
            if expected_type == "board" and entry.get("borderRadius")!=style.get("radius",0): fail("native_radius_mismatch",logical_id)
            if style.get("stroke"):
                strokes=entry.get("strokes"); source=style["stroke"]; color=source["color"]
                if (not isinstance(strokes,list) or len(strokes)!=1 or not isinstance(strokes[0],dict) or
                    str(strokes[0].get("strokeColor","")).lower()!=color[:7].lower() or
                    strokes[0].get("strokeOpacity")!=(int(color[7:9],16)/255 if len(color)==9 else 1) or
                    strokes[0].get("strokeWidth")!=source["width"] or strokes[0].get("strokeStyle")!="solid" or
                    strokes[0].get("strokeAlignment")!="inner"): fail("native_stroke_mismatch",logical_id)
            elif expected_type == "board" and entry.get("strokes")!=[]: fail("native_stroke_mismatch",logical_id)
        if spec.get("componentReference"):
            if entry.get("isComponentCopy") is not True or entry.get("componentReference") != spec["componentReference"] or not entry.get("mainReference"):
                fail("native_instance_mismatch", logical_id)
            if spec["type"] == "ComponentInstance" and (type(entry.get("editableTextCount")) is not int or entry["editableTextCount"] <= 0):
                fail("flattened_component_text", logical_id)
        for child in spec.get("children", []): walk(child, spec)
    try: walk(page)
    except (KeyError, TypeError, ValueError, StopIteration): fail("invalid_plan_or_readback")
    if set(actual) != expected_ids or set(node_map) != expected_ids: fail("logical_node_inventory_mismatch")
    try:
        raw = base64.b64decode(capture.get("nativePngBase64", ""), validate=True)
        if len(raw) > 32 * 1024 * 1024: raise ValueError("PNG exceeds capture limit")
        root = tree[root_id]
        with Image.open(BytesIO(raw)) as image:
            if (image.format != "PNG" or not equal(image.width,root["width"]) or not equal(image.height,root["height"]) or
                image.width > 4096 or image.height > 4096 or image.width * image.height > 4000000): raise ValueError("PNG dimensions differ from root")
            image.load()
        report["nativePngSha256"] = hashlib.sha256(raw).hexdigest()
    except (ValueError, TypeError, KeyError, OSError, OverflowError): fail("invalid_native_png")
    if not issues:
        report.update(status="REVIEW", structuralStatus="PASS", logicalNodeCount=len(expected_ids))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--page-index", type=int, default=0)
    args = parser.parse_args()
    try:
        plan = load_json(args.plan)
        if isinstance(plan,dict) and "plan" in plan:
            if plan.get("status") != "PASS" or not isinstance(plan["plan"],dict): raise ValueError("Adapter preflight did not pass")
            plan = plan["plan"]
        if args.page_index < 0: raise ValueError("Page index must be nonnegative")
        report = validate_output(plan, load_json(args.execution), load_json(args.capture),args.page_index)
    except (OSError, ValueError) as exc:
        report = {"status":"FAIL", "structuralStatus":"FAIL", "finalAcceptance":"NOT_RUN", "issues":[{"code":"invalid_qa_input", "detail":str(exc)}]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["structuralStatus"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
