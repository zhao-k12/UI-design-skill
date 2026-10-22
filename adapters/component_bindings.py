"""Adapter-owned lookup only; does not generate or verify native design objects."""
from copy import deepcopy
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator


class BindingError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def validate_instance_scope(node, descriptor, width, height):
    """Reject any override of a fixed-content native master before adapter writes."""
    scope = descriptor.get("contentScope")
    if not scope:
        return
    dimensions_valid = (width.get("mode") == "fixed" and height.get("mode") == "fixed"
                        and all(type(axis.get("value")) in (int, float) and
                                math.isfinite(axis["value"]) and axis["value"] > 0
                                for axis in (width, height)))
    if "width" in scope:
        dimensions_valid = (width == {"mode": "fixed", "value": scope["width"]}
                            and height == {"mode": "fixed", "value": scope["height"]})
    if (node.get("props") or node.get("slots") or node.get("style") or not dimensions_valid):
        raise BindingError("unsupported_component", "Instance exceeds the admitted native text/size/style scope")


class ComponentBindings:
    def __init__(self, data, registry, *, platform, allow_test_fixtures=False):
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/component-bindings.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
        if data["platform"] != platform:
            raise BindingError("platform_mismatch", "Binding file belongs to another platform")
        if data["scope"] != registry.scope or (data["scope"] == "test-fixture" and not allow_test_fixtures):
            raise BindingError("binding_scope_mismatch", "Binding scope cannot be mixed or promoted")
        if data["registrySha256"] != registry.fingerprint or data["libraryVersion"] != registry.library_version or data["sourceVersion"] != registry.source_version:
            raise BindingError("binding_version_mismatch", "Bindings must target this exact registry snapshot and source version")
        self._data = deepcopy(data)
        self._registry = registry
        for logical_id, binding in self._data["bindings"].items():
            for variant, reference in binding["variants"].items():
                descriptor = registry.resolve(logical_id, variant)["descriptor"]
                if reference["fidelityReportSha256"] != descriptor["fidelity"]["reportSha256"]:
                    raise BindingError("binding_fidelity_mismatch", "Binding must match the admitted fidelity report")
                if "contentScope" in descriptor:
                    row = registry.fidelity_report(logical_id)["platforms"].get(platform, {})
                    if (reference["fileReference"] != row.get("fileReference") or
                            reference["componentReference"] != row.get("componentId")):
                        raise BindingError("binding_native_mismatch", "V0.2 binding must point to the audited native component")

    def resolve(self, logical_id, variant=None):
        choice = self._registry.resolve(logical_id, variant)
        binding = self._data["bindings"].get(logical_id)
        if binding is None or choice["variant"] not in binding["variants"]:
            raise BindingError("missing_component_reference", "No platform component reference for this logical component variant")
        return deepcopy(binding["variants"][choice["variant"]])
