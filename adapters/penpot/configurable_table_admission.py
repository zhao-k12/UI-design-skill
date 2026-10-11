"""Validate a Penpot-specific gate receipt without changing the logical registry."""
from copy import deepcopy
from importlib import import_module
import base64
import hashlib
from io import BytesIO
from PIL import Image

registry_module = import_module("core.component-resolver.registry")


def validate_receipt(proof, expected, registry, descriptor):
    if not isinstance(proof, dict) or any(proof.get(k) != v for k, v in expected.items()):
        raise ValueError("Missing exact Penpot fidelity receipt")
    native = proof.get("nativeEvidence", {})
    report = proof.get("gateReport", {})
    if not isinstance(native, dict) or not isinstance(report, dict):
        raise ValueError("Missing complete native capture and gate report")
    if (native.get("platform") != "penpot" or native.get("status") != "CAPTURED" or native.get("evidenceKind") != "native-platform-export" or
        native.get("scope") != "production" or native.get("fileReference") != expected["fileReference"] or
        native.get("componentReference") != expected["componentReference"] or
        registry_module.digest(native) != proof.get("nativeEvidenceSha256") or
        registry_module.digest(report) != proof.get("verifiedReportSha256") or
        report.get("capture", {}).get("nativeEvidenceSha256") != proof.get("nativeEvidenceSha256") or
        not str(report.get("capture", {}).get("exporterVersion", "")).startswith("penpot-") or
        report.get("candidateScreenshotSha256") != proof.get("comparisonPngSha256",proof.get("nativePngSha256"))):
        raise ValueError("Penpot capture/report provenance does not match")
    bundle=proof.get('proofBundle')
    if (not isinstance(bundle,dict) or registry_module.digest(bundle)!=proof.get('proofBundleSha256') or
        proof.get('proofBundleSha256')!=report.get('capture',{}).get('proofBundleSha256') or
        bundle.get('nativeEvidenceSha256')!=proof.get('nativeEvidenceSha256')):
        raise ValueError('Penpot full proof bundle does not match the verified report')
    try:
        original=base64.b64decode(native['nativePngBase64'],validate=True)
        if hashlib.sha256(original).hexdigest()!=proof['nativePngSha256']:
            raise ValueError('Native PNG bytes do not match')
        if 'comparisonPngSha256' in proof:
            with Image.open(BytesIO(original)) as image:
                white=Image.new('RGBA',image.size,'white');white.alpha_composite(image.convert('RGBA'))
                encoded=BytesIO();white.save(encoded,format='PNG')
            if hashlib.sha256(encoded.getvalue()).hexdigest()!=proof['comparisonPngSha256']:
                raise ValueError('Comparison PNG is not the declared white composite')
    except (KeyError,TypeError,ValueError,OSError) as exc:
        raise ValueError('Penpot native/comparison PNG binding failed') from exc
    entry = deepcopy(descriptor)
    entry["fidelity"]["reportSha256"] = proof["verifiedReportSha256"]
    catalog = registry.snapshot
    catalog["components"] = {expected["logicalId"]: entry}
    # Reuse the complete versioned gate contract, not a loose status/hash summary.
    type(registry)(catalog, {entry["fidelity"]["reportId"]: report})
