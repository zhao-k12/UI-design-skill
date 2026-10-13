"""Logical component catalog. Platform references never enter this module."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def valid_default_font_button_report(report):
    """Validate the platform-neutral proof shape for the approved V0.2 Button fixture."""
    hex_hash = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (report.get("gateVersion") != "0.2.2" or report.get("logicalComponentId") != "action.button.primary.medium"
            or report.get("componentType") != "Button" or report.get("variants") != ["default"]
            or report.get("candidateEvidenceKind") != "native-design-capture"
            or report.get("admissionEligible") is not True or report.get("issues") != []
            or report.get("effectiveCjkFontIdentity") != "UNVERIFIED"
            or report.get("registryAdmission") != "NOT_RUN"
            or report.get("readyForPageGeneration") is not False or report.get("releaseReady") is not False):
        return False
    checks = report.get("checks", {})
    if not isinstance(checks, dict):
        return False
    screenshot = checks.get("screenshot", {})
    if (checks.get("geometryAndStyle") != "PASS" or not isinstance(screenshot, dict)
            or screenshot.get("policy") != "source-locked-default-font-regions-0.2.2"
            or type(screenshot.get("changedPixelsOutsidePermittedRegions")) is not int
            or screenshot["changedPixelsOutsidePermittedRegions"] != 0):
        return False
    rows = report.get("platforms", {})
    evidence = report.get("evidenceSha256", {})
    if (not isinstance(rows, dict) or len(rows) != 2 or not isinstance(evidence, dict)
            or set(rows) != {k for k, v in evidence.items() if isinstance(v, dict)}
            or not all(hex_hash(evidence.get(k)) for k in ("sourceComponentIrSha256", "sourceScreenshotSha256",
                                                     "manifestSha256", "policySha256", "visualReviewSha256"))):
        return False
    for name, row in rows.items():
        if not isinstance(row, dict) or row.get("status") != "PASS":
            return False
        if (name not in ("figma", "penpot") or not isinstance(row.get("fileReference"), str)
                or not row["fileReference"] or not isinstance(row.get("componentId"), str)
                or not row["componentId"]):
            return False
        row_checks = row.get("checks", {})
        if (not isinstance(row_checks, dict) or len(row_checks) < 10
                or not all(value is True for value in row_checks.values())
                or not all(hex_hash(row.get(key)) for key in ("nativePngSha256", "nativeSvgSha256",
                                                                 "repeatNativePngSha256"))
                or row["nativePngSha256"] != row["repeatNativePngSha256"]):
            return False
        pixels = row.get("pixelDiagnostics", {})
        if not isinstance(pixels, dict):
            return False
        corners, text, interior = (pixels.get(key, {}) for key in ("cornerEdge", "textZone", "nonTextInterior"))
        if not all(isinstance(item, dict) for item in (corners, text, interior)):
            return False
        if (interior.get("different") != 0 or corners.get("outOfPalettePixels") != 0
                or type(corners.get("maxPaletteResidual")) not in (int, float)
                or corners["maxPaletteResidual"] > 2
                or len(text.get("brightInkPixelsByHalf", [])) != 2
                or not all(type(count) is int and count > 0 for count in text["brightInkPixelsByHalf"])
                or len(text.get("inkFillFractionByHalf", [])) != 2
                or not all(type(value) in (int, float) and 0 < value < .75
                           for value in text["inkFillFractionByHalf"])):
            return False
        platform_evidence = evidence[name]
        if (not isinstance(platform_evidence, dict)
                or not all(hex_hash(platform_evidence.get(key)) for key in
                           ("candidateMetadataSha256", "targetMetadataSha256", "priorAuditSha256",
                            "repeatNativeReadSha256"))):
            return False
    return True


def valid_default_font_input_report(report):
    """Validate the exact five-glyph, empty-value Input native gate."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    expected_scope = {"kind": "fixed-native-content", "placeholder": "请输入姓名",
                      "value": "", "width": 240, "height": 32}
    if (report.get("gateVersion") != "0.2.3" or report.get("status") != "PASS"
            or report.get("logicalComponentId") != "form.input.default.medium"
            or report.get("componentType") != "Input" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != expected_scope
            or report.get("candidateEvidenceKind") != "native-design-capture"
            or report.get("admissionEligible") is not True or report.get("issues") != []
            or report.get("registryAdmission") != "NOT_RUN"
            or report.get("readyForPageGeneration") is not False
            or report.get("releaseReady") is not False
            or report.get("effectiveCjkFontIdentity") != "UNVERIFIED"):
        return False
    evidence = report.get("evidenceSha256", {})
    if not isinstance(evidence, dict) or not all(hash_ok(evidence.get(key)) for key in
            ("sourceScreenshot", "candidateAudit", "visualReview", "policy")):
        return False
    rows = report.get("platforms", {})
    if not isinstance(rows, dict) or set(rows) != {"figma", "penpot"}:
        return False
    for row in rows.values():
        checks, pixels = row.get("checks", {}), row.get("pixelDiagnostics", {})
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 9
                or not all(value is True for value in checks.values())
                or not isinstance(pixels, dict) or pixels.get("nonTextDifferences") != 0
                or len(pixels.get("visibleInkByCharacter", [])) != 5
                or not all(type(n) is int and n > 2 for n in pixels["visibleInkByCharacter"])
                or type(row.get("maxCornerPaletteResidual")) not in (int, float)
                or row["maxCornerPaletteResidual"] > 2
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not all(hash_ok(row.get(key)) for key in
                           ("nativePngSha256", "nativeSvgSha256", "candidateMetadataSha256"))):
            return False
    return True


def valid_default_font_select_report(report):
    """Validate the exact selected-value Select native gate."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    expected_scope = {"kind": "fixed-native-content", "modelValue": "enabled",
                      "selectedText": "启用", "width": 240, "height": 32}
    if (report.get("gateVersion") != "0.2.4" or report.get("status") != "PASS"
            or report.get("logicalComponentId") != "form.select.default.medium"
            or report.get("componentType") != "Select" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != expected_scope
            or report.get("candidateEvidenceKind") != "native-design-capture"
            or report.get("admissionEligible") is not True or report.get("issues") != []
            or report.get("registryAdmission") != "NOT_RUN"
            or report.get("readyForPageGeneration") is not False
            or report.get("releaseReady") is not False
            or report.get("effectiveCjkFontIdentity") != "UNVERIFIED"):
        return False
    evidence = report.get("evidenceSha256", {})
    if not isinstance(evidence, dict) or not all(hash_ok(evidence.get(key)) for key in
            ("sourceScreenshot", "candidateAudit", "visualReview", "policy")):
        return False
    rows = report.get("platforms", {})
    if not isinstance(rows, dict) or set(rows) != {"figma", "penpot"}:
        return False
    for row in rows.values():
        checks, pixels = row.get("checks", {}), row.get("pixelDiagnostics", {})
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 10
                or not all(value is True for value in checks.values())
                or not isinstance(pixels, dict) or pixels.get("nonTextDifferences") != 0
                or type(pixels.get("arrowAbsoluteError")) is not int or pixels["arrowAbsoluteError"] > 1500
                or len(row.get("visibleInkByCharacter", [])) != 2
                or not all(type(n) is int and n > 10 for n in row["visibleInkByCharacter"])
                or type(row.get("maxCornerPaletteResidual")) not in (int, float)
                or row["maxCornerPaletteResidual"] > 2
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not all(hash_ok(row.get(key)) for key in
                           ("nativePngSha256", "nativeSvgSha256", "candidateMetadataSha256"))):
            return False
    return True


class ComponentError(ValueError):
    def __init__(self, code, component_id, message):
        self.code, self.component_id = code, component_id
        super().__init__(message)


class ComponentRegistry:
    def __init__(self, data, evidence=None, *, allow_test_fixtures=False):
        version = data.get("registryVersion") if isinstance(data, dict) else None
        schema_name = (f"component-registry-{version}.schema.json" if version in ("0.2.0", "0.2.1", "0.2.2")
                       else "component-registry.schema.json")
        schema = json.loads((Path(__file__).resolve().parents[2] / "schemas" / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
        self._data = deepcopy(data)
        self._hash = digest(data)
        if evidence is not None and not isinstance(evidence, dict):
            raise ComponentError("invalid_fidelity_evidence", "", "Evidence must map report IDs to report objects")
        self._evidence = deepcopy(evidence if evidence is not None else {})
        if data["scope"] == "test-fixture" and not allow_test_fixtures:
            raise ComponentError("test_fixture_forbidden", "", "Test catalogs are not production registries")
        for logical_id, entry in data["components"].items():
            if entry["defaultVariant"] not in entry["variants"]:
                raise ComponentError("invalid_component_variant", logical_id, "Default variant must be declared")
            if entry["status"] == "active":
                proof = entry["fidelity"]
                report = self._evidence.get(proof["reportId"])
                if report is None:
                    raise ComponentError("missing_fidelity_evidence", logical_id, "Active components require a loaded fidelity report")
                if not isinstance(report, dict):
                    raise ComponentError("invalid_fidelity_evidence", logical_id, "A fidelity report must be an object")
                if digest(report) != proof["reportSha256"]:
                    raise ComponentError("fidelity_evidence_mismatch", logical_id, "Fidelity report digest does not match")
                if report.get("status") != "PASS" or report.get("logicalComponentId") != logical_id or report.get("componentIrSha256") != proof["componentIrSha256"]:
                    raise ComponentError("fidelity_not_passed", logical_id, "Report must PASS for this exact logical component and Component IR")
                variants = report.get("variants")
                if report.get("componentType") != entry["componentType"] or not isinstance(variants, list) or not all(isinstance(item, str) for item in variants) or sorted(variants) != sorted(entry["variants"]):
                    raise ComponentError("fidelity_variant_mismatch", logical_id, "Evidence must cover the declared component type and all variants")
                if report.get("scope") != data["scope"] or report.get("sourceVersion") != data["sourceVersion"] or data["sourceVersion"] == "unresolved":
                    raise ComponentError("fidelity_source_mismatch", logical_id, "Evidence scope/source must match the registry")
                allowed_gates = {"0.2.0": ("0.2.2",), "0.2.1": ("0.2.2", "0.2.3"),
                                 "0.2.2": ("0.2.2", "0.2.3", "0.2.4")}
                if version in allowed_gates and report.get("gateVersion") not in allowed_gates[version]:
                    raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 active components require the scoped default-font gate")
                if data["scope"] == "production":
                    if report.get("gateVersion") == "0.2.2":
                        expected_scope = {"kind": "fixed-native-content", "text": "查询", "width": 60, "height": 32}
                        if (version not in ("0.2.0", "0.2.1", "0.2.2") or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Button" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Button requires its exact validated content and geometry scope")
                        if not valid_default_font_button_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Button proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.3":
                        expected_scope = {"kind": "fixed-native-content", "placeholder": "请输入姓名",
                                          "value": "", "width": 240, "height": 32}
                        if (version not in ("0.2.1", "0.2.2") or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Input" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Input requires its exact validated placeholder and geometry scope")
                        if not valid_default_font_input_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Input proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.4":
                        expected_scope = {"kind": "fixed-native-content", "modelValue": "enabled",
                                          "selectedText": "启用", "width": 240, "height": 32}
                        if (version != "0.2.2" or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Select" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Select requires its exact selected value and geometry scope")
                        if not valid_default_font_select_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Select proof is incomplete")
                        continue
                    checks = report.get("checks", {})
                    capture = report.get("capture", {})
                    hashes = ("candidateSha256", "referenceScreenshotSha256", "candidateScreenshotSha256")
                    valid_hashes = all(isinstance(report.get(k), str) and len(report[k]) == 64 and
                                       all(c in "0123456789abcdef" for c in report[k]) for k in hashes)
                    screenshot=checks.get('screenshot',{}) if isinstance(checks,dict) else {}
                    policy_pass=report.get('gateVersion')=='0.1.0' and isinstance(screenshot,dict) and screenshot.get('changedPixels')==0
                    if report.get('gateVersion')=='0.2.0' and isinstance(checks,dict) and isinstance(screenshot,dict) and isinstance(capture,dict):
                        required=('geometryAndStyle','content','fontBinding','glyphGeometry','baselines','renderState','sourceReproduction','vectorBinding')
                        proofs=checks.get('normalizationProofs',{})
                        retention=checks.get('glyphRetention',[])
                        proof_hash=capture.get('proofBundleSha256','')
                        vector_hash=screenshot.get('vectorRasterSha256','')
                        policy_pass=(screenshot.get('policy')=='evidence-bound-edges-0.2.0' and
                            type(screenshot.get('changedPixelsOutsideEdgeBand')) is int and screenshot['changedPixelsOutsideEdgeBand']==0 and
                            type(screenshot.get('changedPixelsOutsidePermittedRegions')) is int and screenshot['changedPixelsOutsidePermittedRegions']==0 and
                            type(screenshot.get('changedPixels')) is int and screenshot['changedPixels']>=0 and
                            isinstance(proofs,dict) and all(proofs.get(k)=='PASS' for k in required) and
                            isinstance(retention,list) and bool(retention) and all(isinstance(row,dict) and row.get('status')=='PASS' and type(row.get('retentionRatio')) in (int,float) and .5<=row['retentionRatio']<=2 for row in retention) and
                            all(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value) for value in (proof_hash,vector_hash)))
                    if (not policy_pass or report.get("admissionEligible") is not True or
                        report.get("candidateEvidenceKind") != "native-design-capture" or report.get("issues") != [] or
                        not isinstance(checks, dict) or checks.get("geometryAndStyle") != "PASS" or
                        not isinstance(checks.get("screenshot"), dict) or
                        not isinstance(capture, dict) or not all(capture.get(k) for k in ("captureId", "exporterVersion", "nativeEvidenceSha256")) or not valid_hashes):
                        raise ComponentError("invalid_fidelity_gate_report", logical_id, "Production admission requires complete native-capture gate evidence")

    @property
    def snapshot(self):
        return deepcopy(self._data)

    @property
    def fingerprint(self):
        return self._hash

    @property
    def library_version(self):
        return self._data["libraryVersion"]

    @property
    def source_version(self):
        return self._data["sourceVersion"]

    @property
    def scope(self):
        return self._data["scope"]

    def inspect(self, logical_id):
        if logical_id not in self._data["components"]:
            raise ComponentError("missing_component", logical_id, "Logical component is not registered")
        return deepcopy(self._data["components"][logical_id])

    def fidelity_report(self, logical_id):
        entry = self.inspect(logical_id)
        if entry["status"] != "active":
            raise ComponentError("component_not_ready", logical_id, "Component is not admitted")
        return deepcopy(self._evidence[entry["fidelity"]["reportId"]])

    def resolve(self, logical_id, variant=None):
        entry = self.inspect(logical_id)
        if entry["status"] != "active":
            raise ComponentError("component_not_ready" if entry["status"] == "planned" else "deprecated_component", logical_id, "Component is not admitted for new instances")
        variant = entry["defaultVariant"] if variant is None else variant
        if variant not in entry["variants"]:
            raise ComponentError("invalid_component_variant", logical_id, f"Undeclared variant: {variant}")
        return {"logicalId": logical_id, "variant": variant, "descriptor": entry}
