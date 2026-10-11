"""Synthetic structural fixtures only; no actual Penpot acceptance is asserted."""
from copy import deepcopy
from io import BytesIO
import base64
import unittest

from PIL import Image
from adapters.penpot.qa import validate_output


class PenpotQATests(unittest.TestCase):
    def fixture(self):
        layout = {"direction":"vertical", "gap":0,"wrap":False,"padding":dict.fromkeys(("top","right","bottom","left"),0),
            "alignment":{"main":"start","cross":"start"},"width":{"mode":"fixed","value":100},"height":{"mode":"fixed","value":100}}
        spec = {"id":"page","name":"page","type":"Page","layout":layout,"style":{},"children":[]}
        plan = {"platform":"penpot", "documentId":"test-only", "pages":[spec],"fileReference":"test-file",
            "adapterVersion":"0.1.0", **{k:"a"*64 for k in ("uiIrSha256","tokensSha256","componentsSha256","iconsSha256")}}
        execution = {k:v for k,v in plan.items() if k not in ("pages","platform","documentId")}
        execution.update(status="EXECUTED",scope="penpot_native_translation",pageReference="test-page",rootReference="test-root",
            nodeMap={"page":"test-root"},createdNodeIds=["test-root"],mutatedNodeIds=[],helperNodeIds=[])
        tree = {"nodeId":"test-root","parentReference":"test-page-root","type":"board","name":"UI-IR/test-only/page",
            "x":80,"y":80,"width":100,"height":100,"childNodeIds":[]}
        entry = {**tree,"uiIrId":"page","horizontalSizing":"fix","verticalSizing":"fix","clipContent":False,
            "fills":[],"strokes":[],"opacity":1,"borderRadius":0,
            "flex":{"dir":"column","wrap":"nowrap","rowGap":0,"columnGap":0,"topPadding":0,"rightPadding":0,"bottomPadding":0,"leftPadding":0,"justifyContent":"start","alignItems":"start"}}
        png = BytesIO(); Image.new("RGBA",(100,100),"white").save(png,format="PNG")
        capture = {"status":"CAPTURED","platform":"penpot","scope":"production","evidenceKind":"native-platform-export",
            "exporterVersion":"penpot-native-output-v0.1.0","fileReference":"test-file","pageReference":"test-page","rootReference":"test-root",
            "fileRevision":1,
            "createdNodeIds":[],"mutatedNodeIds":[],"topology":[tree],"evidence":[entry],"nativePngBase64":base64.b64encode(png.getvalue()).decode()}
        return plan,execution,capture

    def codes(self, report): return {i["code"] for i in report["issues"]}

    def test_structural_success_still_requires_final_acceptance(self):
        args = self.fixture(); original = deepcopy(args)
        r = validate_output(*args)
        self.assertEqual(r["structuralStatus"],"PASS"); self.assertEqual(r["status"],"REVIEW")
        self.assertEqual(r["finalAcceptance"],"NOT_RUN"); self.assertEqual(r["fidelityGate"],"NOT_RUN")
        self.assertEqual(args,original)

    def test_capture_identity_and_execution_hashes_are_bound(self):
        p,e,c = self.fixture(); c["fileReference"] = "another-file"; e["uiIrSha256"] = "b"*64
        codes = self.codes(validate_output(p,e,c))
        self.assertIn("capture_identity_mismatch",codes); self.assertIn("execution_input_mismatch",codes)

    def test_duplicate_and_extra_logical_nodes_are_rejected(self):
        p,e,c = self.fixture(); c["evidence"].append(deepcopy(c["evidence"][0]))
        self.assertIn("invalid_readback_nodes",self.codes(validate_output(p,e,c)))
        p,e,c = self.fixture(); c["evidence"].append({"uiIrId":"unknown","nodeId":"unknown"})
        self.assertIn("logical_node_inventory_mismatch",self.codes(validate_output(p,e,c)))

    def test_wrong_layout_and_sizing_modes_are_rejected(self):
        p,e,c = self.fixture(); c["evidence"][0]["flex"]["leftPadding"] = 16; c["evidence"][0]["verticalSizing"] = "auto"
        codes = self.codes(validate_output(p,e,c))
        self.assertIn("native_padding_mismatch",codes); self.assertIn("native_sizing_mismatch",codes)

    def test_ledger_missing_nodes_and_stray_or_cyclic_tree_are_rejected(self):
        p,e,c = self.fixture(); c["topology"].append({"nodeId":"stray","parentReference":"stray"})
        codes = self.codes(validate_output(p,e,c))
        self.assertIn("creation_ledger_tree_mismatch",codes); self.assertIn("native_node_outside_root",codes)

    def test_capture_mutation_and_invalid_or_resized_png_are_rejected(self):
        p,e,c = self.fixture(); c["mutatedNodeIds"] = ["test-root"]; c["nativePngBase64"] = "bad"
        codes = self.codes(validate_output(p,e,c))
        self.assertIn("capture_wrote_canvas",codes); self.assertIn("invalid_native_png",codes)
        p,e,c = self.fixture(); image = BytesIO(); Image.new("RGB",(200,200)).save(image,format="PNG")
        c["nativePngBase64"] = base64.b64encode(image.getvalue()).decode()
        self.assertIn("invalid_native_png",self.codes(validate_output(p,e,c)))

    def test_flattened_or_wrong_master_instance_cannot_pass(self):
        p,e,c = self.fixture(); s=p["pages"][0]; s["type"]="ComponentInstance"; s["componentReference"]="verified-master"; s["name"]="page"
        c["evidence"][0].update(name="page",isComponentCopy=True,componentReference="wrong-master",mainReference="test-main",editableTextCount=0)
        c["topology"][0]["name"]="page"
        codes=self.codes(validate_output(p,e,c))
        self.assertIn("native_instance_mismatch",codes); self.assertIn("flattened_component_text",codes)

    def test_malformed_topology_and_node_map_fail_without_crashing(self):
        p,e,c=self.fixture(); e["nodeMap"]={"page":{}}; c["topology"][0]["parentReference"]={}
        r=validate_output(p,e,c); self.assertEqual(r["status"],"FAIL")
        self.assertIn("invalid_execution_node_map",self.codes(r)); self.assertIn("invalid_native_parent",self.codes(r))

    def test_paint_stroke_opacity_and_radius_cannot_silently_change(self):
        p,e,c=self.fixture(); p["pages"][0]["style"]={"fill":"#ffffff80","radius":4,"stroke":{"color":"#abcdef","width":1},"opacity":.8}
        codes=self.codes(validate_output(p,e,c))
        for code in ("native_paint_mismatch","native_radius_mismatch","native_stroke_mismatch","native_opacity_mismatch"):
            self.assertIn(code,codes)

    def test_text_is_exact_and_numeric_serialization_is_equivalent(self):
        p,e,c=self.fixture(); spec=p["pages"][0]; spec.update(type="Text",text="固定输入",name="page")
        spec["fontBinding"]={"fontId":"test-font","fontVariantId":"test-regular","family":"Noto Sans SC","weight":400,"style":"normal"}
        spec["style"]={"typographyToken":{"fontSize":14,"lineHeight":14,"letterSpacing":0}}
        c["topology"][0].update(type="text",name="page")
        c["evidence"][0].update(type="text",name="page",characters="固定输入",fontId="test-font",fontFamily="Noto Sans SC",
            fontVariantId="test-regular",fontWeight="400",fontStyle="normal",fontSize="14",lineHeight="1",letterSpacing="0",growType="fixed")
        self.assertEqual(validate_output(p,e,c)["structuralStatus"],"PASS")
        c["evidence"][0]["fontWeight"]="400.0000001"
        self.assertIn("native_text_mismatch",self.codes(validate_output(p,e,c)))

    def test_native_children_and_revision_must_be_explicit(self):
        p,e,c=self.fixture(); c["topology"][0]["childNodeIds"]=["missing"]; c.pop("fileRevision")
        codes=self.codes(validate_output(p,e,c))
        self.assertIn("invalid_native_children",codes); self.assertIn("invalid_capture_revision",codes)

    def test_new_capture_requires_explicit_effects_and_bound_child_order(self):
        p,e,c=self.fixture();c['exporterVersion']='penpot-native-output-v0.1.1'
        self.assertIn('native_render_state_mismatch',self.codes(validate_output(p,e,c)))
        c['evidence'][0].update(rotation=0,flipX=False,flipY=False,hidden=False,visible=True,blendMode='normal',shadows=[],blur=None)
        c['topology'][0].update(nativeStackChildNodeIds=[],childOrderNormalization='penpot-stack-to-layout-reverse')
        self.assertEqual(validate_output(p,e,c)['structuralStatus'],'PASS')
        c['topology'][0]['nativeStackChildNodeIds']=['invented']
        self.assertIn('invalid_child_order_normalization',self.codes(validate_output(p,e,c)))
