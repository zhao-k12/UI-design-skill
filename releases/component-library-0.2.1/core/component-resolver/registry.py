"""Logical component catalog. Platform references never enter this module."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


class ComponentError(ValueError):
    def __init__(self, code, component_id, message):
        self.code, self.component_id = code, component_id
        super().__init__(message)


class ComponentRegistry:
    def __init__(self, data, evidence=None, *, allow_test_fixtures=False):
        if data.get("libraryVersion") != "0.2.1":
            raise ComponentError("library_version_mismatch", "", "Explicit component library 0.2.1 required")
        schema = json.loads((Path(__file__).resolve().parents[2] / "schemas/component-registry.schema.json").read_text(encoding="utf-8"))
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
                if data["scope"] == "production":
                    checks = report.get("checks", {})
                    capture = report.get("capture", {})
                    hashes = ("candidateSha256", "referenceScreenshotSha256", "candidateScreenshotSha256")
                    valid_hashes = all(isinstance(report.get(k), str) and len(report[k]) == 64 and
                                       all(c in "0123456789abcdef" for c in report[k]) for k in hashes)
                    screenshot=checks.get('screenshot',{}) if isinstance(checks,dict) else {}
                    policy_pass=report.get('gateVersion')=='0.1.0' and isinstance(screenshot,dict) and screenshot.get('changedPixels')==0
                    if report.get('gateVersion') in ('0.2.0','0.2.1') and isinstance(checks,dict) and isinstance(screenshot,dict) and isinstance(capture,dict):
                        required=('geometryAndStyle','content','fontBinding','glyphGeometry','baselines','renderState','sourceReproduction','vectorBinding')
                        proofs=checks.get('normalizationProofs',{})
                        retention=checks.get('glyphRetention',[])
                        proof_hash=capture.get('proofBundleSha256','')
                        vector_hash=screenshot.get('vectorRasterSha256','')
                        policy_pass=(screenshot.get('policy')=='evidence-bound-edges-'+report['gateVersion'] and
                            type(screenshot.get('changedPixelsOutsideEdgeBand')) is int and screenshot['changedPixelsOutsideEdgeBand']==0 and
                            type(screenshot.get('changedPixelsOutsidePermittedRegions')) is int and screenshot['changedPixelsOutsidePermittedRegions']==0 and
                            type(screenshot.get('changedPixels')) is int and screenshot['changedPixels']>=0 and
                            isinstance(proofs,dict) and all(proofs.get(k)=='PASS' for k in required) and
                            isinstance(retention,list) and bool(retention) and all(isinstance(row,dict) and row.get('status')=='PASS' and type(row.get('retentionRatio')) in (int,float) and .5<=row['retentionRatio']<=2 for row in retention) and
                            all(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value) for value in (proof_hash,vector_hash)))
                    if report.get('gateVersion')=='0.2.1':
                        policy_pass=policy_pass and entry['componentType']=='Table' and logical_id in ('data.table.config.4fe0393d9091c298f4469e4e95f43824af5373fe0552434be0ed2887e3857a72', 'data.table.config.b3eb343b6ad2c8cd567a53f7d65703db6627cb9e7e1bfaedfb3098baf7af8122') and report.get('pixelRegionPolicy')=='positive-area-intersection'
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

    def resolve(self, logical_id, variant=None):
        entry = self.inspect(logical_id)
        if entry["status"] != "active":
            raise ComponentError("component_not_ready" if entry["status"] == "planned" else "deprecated_component", logical_id, "Component is not admitted for new instances")
        variant = entry["defaultVariant"] if variant is None else variant
        if variant not in entry["variants"]:
            raise ComponentError("invalid_component_variant", logical_id, f"Undeclared variant: {variant}")
        return {"logicalId": logical_id, "variant": variant, "descriptor": entry}
