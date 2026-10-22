"""Logical component catalog. Platform references never enter this module."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def valid_figma_batch_report(report, entry):
    """Validate the new immutable Figma-only fixed-snapshot admission contract."""
    scope = entry.get("contentScope", {})
    row = report.get("platforms", {}).get("figma", {})
    hashes = report.get("evidenceSha256", {})
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    return (report.get("gateVersion") == "0.2.8-figma-batch"
            and report.get("admissionEligible") is True
            and report.get("issues") == []
            and set(report.get("platforms", {})) == {"figma"}
            and row.get("status") == "PASS"
            and isinstance(row.get("fileReference"), str) and bool(row["fileReference"])
            and isinstance(row.get("componentId"), str) and bool(row["componentId"])
            and scope.get("kind") == "fixed-native-snapshot"
            and report.get("contentScopeProposal") == scope
            and scope.get("width", 0) > 0 and scope.get("height", 0) > 0
            and isinstance(scope.get("props"), dict)
            and isinstance(scope.get("visibleText"), list)
            and all(isinstance(text, str) and text for text in scope["visibleText"])
            and all(hash_ok(hashes.get(key)) for key in
                    ("sourceComponentIr", "sourceScreenshot", "figmaQa", "nativeRead", "nativePng", "nativeSvg"))
            and ("sourceBundleSha256" not in hashes or hash_ok(hashes["sourceBundleSha256"]))
            and report.get("componentIrSha256") == hashes.get("sourceComponentIr"))


ADAPTIVE_TABLE = "data.table.headed.b334d80b864ecaf53198737bffec5c2bc8d59d337667effacb16ea74dcd024b4"


@lru_cache(maxsize=1)
def _adaptive_baseline():
    folder = Path(__file__).resolve().parents[2] / "registries/components/v0.2.8"
    return (json.loads((folder / "catalog.json").read_text(encoding="utf-8")),
            json.loads((folder / "fidelity-reports.json").read_text(encoding="utf-8")))


def valid_adaptive_size_report(report, entry, logical_id):
    """Versioned content admission without treating sample dimensions as identity."""
    baseline_catalog, baseline_reports = _adaptive_baseline()
    baseline = baseline_reports.get(entry["fidelity"]["reportId"])
    if not isinstance(baseline, dict):
        return False
    original_sha = digest(baseline)
    baseline_entry = baseline_catalog["components"].get(logical_id)
    if not isinstance(baseline_entry, dict):
        return False
    scope = deepcopy(baseline_entry["contentScope"])
    scope.pop("width", None)
    scope.pop("height", None)
    for columns in (scope.get("columns"), scope.get("props", {}).get("columns")):
        if columns:
            for column in columns:
                column.pop("width", None)
    policy = {"width": "fill-cell" if logical_id == ADAPTIVE_TABLE else "intrinsic",
              "height": "intrinsic"}
    if entry.get("contentScope") != scope or entry.get("sizingPolicy") != policy:
        return False
    expected = deepcopy(baseline)
    expected["contentScopeProposal"] = scope
    expected["gateVersion"] = "0.2.9-figma-size-policy"
    expected["sizingMigration"] = {"baseReportSha256": original_sha,
                                   "baseGateVersion": baseline["gateVersion"],
                                   "policy": policy}
    if logical_id == ADAPTIVE_TABLE:
        expected["platforms"]["figma"]["componentId"] = "299:3"
        evidence_path = Path(__file__).resolve().parents[2] / ".dev/TASK-127_ADAPTIVE_TABLE_READBACK.json"
        evidence_dir = evidence_path.parent / "task-127-evidence"
        names = ("table-source-1840-native.png", "table-adaptive-1840-native.png",
                 "table-1660-native.png")
        if not evidence_path.is_file() or any(not (evidence_dir / name).is_file() for name in names):
            return False
        expected["sizingMigration"]["nativeResponsiveEvidenceSha256"] = hashlib.sha256(
            evidence_path.read_bytes()).hexdigest()
        expected["sizingMigration"]["nativePngSha256"] = {
            name: hashlib.sha256((evidence_dir / name).read_bytes()).hexdigest() for name in names}
        expected["sizingMigration"]["sourceSizeComparison"] = {
            "changedPixels": 1926, "changedXBuckets100px": [6, 12],
            "unchangedOutsideShiftedColumnText": True}
        expected["sizingMigration"]["nativeResponsiveEvidence"] = {
            "fileReference": "0vGWSRoLxBiVPXiZ8xJAX9", "masterId": "299:3",
            "instanceId": "299:36", "testedWidth": 1660, "height": 182.875,
            "rows": 4, "columns": 3, "rowWidths": [1660] * 4,
            "borderWidths": [1660] * 4}
    return report == expected


TABLE_SCOPE = {
    "kind": "fixed-native-content", "showHeader": False, "border": False, "stripe": False,
    "columns": [{"title": title, "key": key, "width": 464} for title, key in
                (("姓名", "name"), ("状态", "status"), ("角色", "role"))],
    "data": [
        {"name": "张三", "status": "启用", "role": "管理员"},
        {"name": "李四", "status": "启用", "role": "编辑"},
        {"name": "王五", "status": "停用", "role": "访客"},
    ],
    "width": 1392, "height": 144,
}

TAG_SCOPE = {"kind": "fixed-native-content", "text": "启用", "size": "default",
             "color": "default", "closable": False, "checkable": False,
             "checked": True, "width": 42, "height": 22}

CHECKBOX_SCOPE = {"kind": "fixed-native-content", "text": "启用", "modelValue": True,
                  "trueValue": True, "falseValue": False, "disabled": False,
                  "indeterminate": False, "size": "default", "border": False,
                  "width": 52, "height": 21}


RADIO_SCOPE = {"kind": "fixed-native-content", "text": "启用", "modelValue": True,
               "trueValue": True, "falseValue": False, "disabled": False,
               "size": "default", "border": False, "width": 48, "height": 21}


def valid_default_font_radio_report(report):
    """Validate the fixed selected Radio and both independent native proofs."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (report.get("gateVersion") != "0.2.7" or report.get("scope") != "production"
            or report.get("status") != "PASS" or report.get("logicalComponentId") != "form.radio.default.enabled"
            or report.get("componentType") != "Radio" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != RADIO_SCOPE
            or report.get("admissionEligible") is not True or report.get("issues") != []
            or report.get("registryAdmission") != "NOT_RUN"
            or report.get("readyForPageGeneration") is not False or report.get("releaseReady") is not False
            or report.get("effectiveCjkFontIdentity") != "UNVERIFIED"):
        return False
    evidence = report.get("evidenceSha256", {})
    if not isinstance(evidence, dict) or not all(hash_ok(evidence.get(key)) for key in
            ("sourceScreenshot", "visualReview", "policy")):
        return False
    rows = report.get("platforms", {})
    if not isinstance(rows, dict) or set(rows) != {"figma", "penpot"}:
        return False
    for row in rows.values():
        checks = row.get("checks", {})
        pixels = row.get("pixelDiagnostics", {})
        glyphs = row.get("glyphDiagnostics", {})
        native = row.get("evidenceSha256", {})
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 7
                or not all(value is True for value in checks.values())
                or pixels.get("pass") is not True or pixels.get("sourceTopBlankRowCropped") is not True
                or type(pixels.get("maximumControlChannelDelta")) is not int
                or pixels["maximumControlChannelDelta"] > 40
                or pixels.get("exactBlueCenter") is not True
                or type(pixels.get("sourceBluePixels")) is not int or pixels["sourceBluePixels"] != 140
                or type(pixels.get("nativeBluePixels")) is not int or pixels["nativeBluePixels"] < 126
                or type(pixels.get("blueIntersectionOverUnion")) not in (float, int)
                or pixels["blueIntersectionOverUnion"] < .9
                or glyphs.get("pass") is not True or glyphs.get("textOuterEdgeInkPixels") != 0
                or len(glyphs.get("perCharacterDarkPixels", [])) != 2
                or not all(type(n) is int and n >= 20 for n in glyphs["perCharacterDarkPixels"])
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not isinstance(row.get("instanceId"), str) or not row["instanceId"]
                or not isinstance(native, dict) or not all(hash_ok(native.get(key)) for key in
                       ("native-read.json", "native.png", "native-repeat.png", "native.svg"))
                or not hash_ok(row.get("candidateMetadataSha256"))):
            return False
    return True


def valid_default_font_checkbox_report(report):
    """Validate the fixed checked Checkbox and both independent native proofs."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (report.get("gateVersion") != "0.2.6" or report.get("scope") != "production"
            or report.get("status") != "PASS" or report.get("logicalComponentId") != "form.checkbox.default.enabled"
            or report.get("componentType") != "Checkbox" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != CHECKBOX_SCOPE
            or report.get("admissionEligible") is not True or report.get("issues") != []
            or report.get("registryAdmission") != "NOT_RUN"
            or report.get("readyForPageGeneration") is not False or report.get("releaseReady") is not False
            or report.get("effectiveCjkFontIdentity") != "UNVERIFIED"):
        return False
    evidence = report.get("evidenceSha256", {})
    if not isinstance(evidence, dict) or not all(hash_ok(evidence.get(key)) for key in
            ("sourceScreenshot", "visualReview", "policy")):
        return False
    rows = report.get("platforms", {})
    if not isinstance(rows, dict) or set(rows) != {"figma", "penpot"}:
        return False
    for row in rows.values():
        checks, pixels, glyphs = (row.get(key, {}) for key in ("checks", "pixelDiagnostics", "glyphDiagnostics"))
        native = row.get("evidenceSha256", {})
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 7
                or not all(value is True for value in checks.values())
                or pixels.get("pass") is not True or pixels.get("nonMarkChangesOutsideCorners") != []
                or type(pixels.get("cornerMaximumChannelDelta")) is not int
                or pixels["cornerMaximumChannelDelta"] > 40
                or pixels.get("sourceMarkPixels") != 14 or pixels.get("nativeMarkPixels") != 16
                or pixels.get("missingSourceMarkPixels") != []
                or len(pixels.get("extraNativeMarkPixels", [])) > 2
                or pixels.get("markIntersectionOverUnion", 0) < .875
                or glyphs.get("pass") is not True or glyphs.get("textOuterEdgeInkPixels") != 0
                or len(glyphs.get("perCharacterDarkPixels", [])) != 2
                or not all(type(n) is int and n >= 20 for n in glyphs["perCharacterDarkPixels"])
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not isinstance(row.get("instanceId"), str) or not row["instanceId"]
                or not isinstance(native, dict) or not all(hash_ok(native.get(key)) for key in
                       ("native-read.json", "native.png", "native-repeat.png", "native.svg"))
                or not hash_ok(row.get("candidateMetadataSha256"))):
            return False
    return True


def valid_default_font_tag_report(report):
    """Validate the fixed enabled Tag and both independent native proofs."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (report.get("gateVersion") != "0.2.5" or report.get("status") != "PASS"
            or report.get("logicalComponentId") != "data.tag.default.enabled"
            or report.get("componentType") != "Tag" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != TAG_SCOPE
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
        checks, pixels, glyphs = row.get("checks", {}), row.get("pixelDiagnostics", {}), row.get("glyphDiagnostics", {})
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 8
                or not all(value is True for value in checks.values())
                or pixels.get("sourceSize") != [42, 22] or pixels.get("nativeSize") != [42, 22]
                or pixels.get("nonTextChangesOutsideFourCorners") != 0
                or type(pixels.get("nonTextMaximumChannelDelta")) is not int
                or pixels["nonTextMaximumChannelDelta"] > 3
                or len(glyphs.get("perCharacter", [])) != 2
                or not all(type(n) is int and n > 10 for n in glyphs["perCharacter"])
                or glyphs.get("outerEdgeInkPixels") != 0
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not all(hash_ok(row.get(key)) for key in
                           ("nativePngSha256", "nativeSvgSha256", "nativeReadSha256", "candidateMetadataSha256"))):
            return False
    return True


def valid_default_font_table_report(report):
    """Validate the exact fixed 3x3 Table native gate."""
    hash_ok = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (report.get("gateVersion") != "0.2.5" or report.get("status") != "PASS"
            or report.get("logicalComponentId") != "data.table.default"
            or report.get("componentType") != "Table" or report.get("variants") != ["default"]
            or report.get("contentScopeProposal") != TABLE_SCOPE
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
        ink = row.get("visibleInkByCharacter", [])
        if (row.get("status") != "PASS" or not isinstance(checks, dict) or len(checks) != 9
                or not all(value is True for value in checks.values())
                or not isinstance(pixels, dict) or pixels.get("nonTextDifferences") != 0
                or len(ink) != 19 or not all(type(n) is int and n > 10 for n in ink)
                or not isinstance(row.get("fileReference"), str) or not row["fileReference"]
                or not isinstance(row.get("componentId"), str) or not row["componentId"]
                or not all(hash_ok(row.get(key)) for key in
                           ("nativePngSha256", "nativeSvgSha256", "candidateMetadataSha256"))):
            return False
    return True


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
        schema_name = (f"component-registry-{version}.schema.json" if version in ("0.2.0", "0.2.1", "0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8", "0.2.9")
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
                                 "0.2.2": ("0.2.2", "0.2.3", "0.2.4"),
                                 "0.2.3": ("0.2.2", "0.2.3", "0.2.4", "0.2.5"),
                                 "0.2.4": ("0.2.2", "0.2.3", "0.2.4", "0.2.5"),
                                 "0.2.5": ("0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6"),
                                 "0.2.6": ("0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7"),
                                 "0.2.7": ("0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8-figma-batch"),
                                  "0.2.8": ("0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8-figma-batch"),
                                  "0.2.9": ("0.2.9-figma-size-policy",)}
                if version in allowed_gates and report.get("gateVersion") not in allowed_gates[version]:
                    raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 active components require the scoped default-font gate")
                if data["scope"] == "production":
                    if report.get("gateVersion") == "0.2.9-figma-size-policy":
                        if (version != "0.2.9" or not valid_adaptive_size_report(report, entry, logical_id)
                                or (logical_id == ADAPTIVE_TABLE and entry["slots"])):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id,
                                                 "Adaptive size migration must preserve source content and native proof")
                        continue
                    if report.get("gateVersion") == "0.2.8-figma-batch":
                        if (version not in ("0.2.7", "0.2.8") or not valid_figma_batch_report(report, entry)
                                or entry["slots"]):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id,
                                                 "Figma batch proof or fixed scope is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.2":
                        expected_scope = {"kind": "fixed-native-content", "text": "查询", "width": 60, "height": 32}
                        if (version not in ("0.2.0", "0.2.1", "0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Button" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Button requires its exact validated content and geometry scope")
                        if not valid_default_font_button_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Button proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.3":
                        expected_scope = {"kind": "fixed-native-content", "placeholder": "请输入姓名",
                                          "value": "", "width": 240, "height": 32}
                        if (version not in ("0.2.1", "0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Input" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Input requires its exact validated placeholder and geometry scope")
                        if not valid_default_font_input_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Input proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.4":
                        expected_scope = {"kind": "fixed-native-content", "modelValue": "enabled",
                                          "selectedText": "启用", "width": 240, "height": 32}
                        if (version not in ("0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry.get("contentScope") != expected_scope
                                or entry["componentType"] != "Select" or entry["variants"] != ["default"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Select requires its exact selected value and geometry scope")
                        if not valid_default_font_select_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Select proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.5":
                        if entry["componentType"] == "Table":
                            if (version not in ("0.2.3", "0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry.get("contentScope") != TABLE_SCOPE
                                    or entry["variants"] != ["default"] or entry["slots"]):
                                raise ComponentError("invalid_content_scope", logical_id, "V0.2 Table requires its exact fixed rows, columns and geometry")
                            if not valid_default_font_table_report(report):
                                raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Table proof is incomplete")
                        elif entry["componentType"] == "Tag":
                            if (version not in ("0.2.4", "0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry.get("contentScope") != TAG_SCOPE
                                    or entry["variants"] != ["default"] or entry["slots"] != ["label"]):
                                raise ComponentError("invalid_content_scope", logical_id, "V0.2 Tag requires its exact fixed text, props and geometry")
                            if not valid_default_font_tag_report(report):
                                raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Tag proof is incomplete")
                        else:
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "Unknown 0.2.5 gate component type")
                        continue
                    if report.get("gateVersion") == "0.2.6":
                        if (version not in ("0.2.5", "0.2.6", "0.2.7", "0.2.8") or entry["componentType"] != "Checkbox"
                                or entry.get("contentScope") != CHECKBOX_SCOPE
                                or entry["variants"] != ["default"] or entry["slots"] != ["label"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Checkbox requires its exact fixed text, props and geometry")
                        if not valid_default_font_checkbox_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Checkbox proof is incomplete")
                        continue
                    if report.get("gateVersion") == "0.2.7":
                        if (version not in ("0.2.6", "0.2.7", "0.2.8") or entry["componentType"] != "Radio"
                                or entry.get("contentScope") != RADIO_SCOPE
                                or entry["variants"] != ["default"] or entry["slots"] != ["label"]):
                            raise ComponentError("invalid_content_scope", logical_id, "V0.2 Radio requires its exact fixed text, props and geometry")
                        if not valid_default_font_radio_report(report):
                            raise ComponentError("invalid_fidelity_gate_report", logical_id, "V0.2 default-font Radio proof is incomplete")
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
