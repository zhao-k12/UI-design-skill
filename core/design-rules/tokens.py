"""Platform-independent, versioned design token registry and reference checks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


def pointer(parts: tuple) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


class TokenError(ValueError):
    def __init__(self, code: str, token: str, message: str):
        self.code = code
        self.token = token
        super().__init__(message)


class RegistryError(ValueError):
    def __init__(self, issues: list[dict]):
        self.issues = sorted(issues, key=lambda item: (item["path"], item["code"], item["message"]))
        super().__init__("Invalid token registry")


class TokenRegistry:
    def __init__(self, data: dict, *, expected_version: str | None = None):
        # Snapshot input so callers cannot alter this registry during a task.
        try:
            serialized = json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
            self._data = deepcopy(data)
            schema_path = Path(__file__).resolve().parents[2] / "schemas" / "token-registry.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            issues = [{"code": "invalid_token_registry", "path": pointer(tuple(error.absolute_path)), "message": error.message}
                      for error in Draft202012Validator(schema).iter_errors(self._data)]
        except (TypeError, ValueError) as exc:
            raise RegistryError([{"code": "invalid_token_registry", "path": "/", "message": str(exc)}]) from exc
        if issues:
            raise RegistryError(issues)
        self._version = self._data["registryVersion"]
        self._fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if expected_version is not None and self.version != expected_version:
            raise RegistryError([{"code": "token_version_mismatch", "path": "/registryVersion", "message": f"Expected {expected_version}, got {self.version}"}])
        for token_id, entry in self._data["tokens"].items():
            if token_id.split(".", 1)[0] != entry["type"]:
                issues.append({"code": "token_type_mismatch", "path": pointer(("tokens", token_id, "type")), "message": "Token ID prefix must equal its registered type"})
        if issues:
            raise RegistryError(issues)
        # Invalid aliases or composites must fail even if no page uses them yet.
        for token_id in sorted(self._data["tokens"]):
            try:
                self.resolve(token_id)
            except TokenError as exc:
                issues.append({"code": exc.code, "path": pointer(("tokens", token_id, "value")), "token": exc.token, "message": str(exc)})
        if issues:
            raise RegistryError(issues)

    @property
    def snapshot(self) -> dict:
        return deepcopy(self._data)

    @property
    def version(self) -> str:
        return self._version

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def token_type(self, token_id: str) -> str:
        if token_id not in self._data["tokens"]:
            raise TokenError("missing_token", token_id, f"Token not registered: {token_id}")
        return self._data["tokens"][token_id]["type"]

    def resolve(self, token_id: str):
        def resolve_id(current: str, stack: tuple[str, ...]):
            self.token_type(current)
            if current in stack:
                raise TokenError("token_cycle", current, "Cyclic token reference: " + " -> ".join((*stack, current)))
            return resolve_value(self._data["tokens"][current]["value"], (*stack, current))

        def resolve_value(value, stack: tuple[str, ...]):
            if isinstance(value, dict):
                if set(value) == {"token"}:
                    return resolve_id(value["token"], stack)
                return {key: resolve_value(child, stack) for key, child in value.items()}
            if isinstance(value, list):
                return [resolve_value(child, stack) for child in value]
            return value

        return deepcopy(resolve_id(token_id, ()))


def check_references(document: dict, registry: TokenRegistry) -> list[dict]:
    """Check a contract-valid UI-IR without changing it or interpreting business props."""
    issues = []
    # Explicit raw values outside registered instances must come from the same
    # approved palette/scale. Fixed geometry is checked separately by layout QA.
    allowed = {}
    for token_id, entry in registry.snapshot["tokens"].items():
        allowed.setdefault(entry["type"], []).append(registry.resolve(token_id))

    def check(value, expected: set[str], path: tuple, positive: bool = False, enforce_literal: bool = False):
        if not isinstance(value, dict) or set(value) != {"token"}:
            if value is not None and enforce_literal:
                normalize = lambda item: item.lower() if isinstance(item, str) and "color" in expected else item
                if not any(normalize(value) == normalize(candidate) for category in expected for candidate in allowed.get(category, [])):
                    issues.append({"code": "unregistered_visual_value", "path": pointer(path), "message": "Use a registered token or a value from its declared scale"})
            return
        token_id = value["token"]
        try:
            actual = registry.token_type(token_id)
            if actual not in expected:
                raise TokenError("token_type_mismatch", token_id, f"Expected {', '.join(sorted(expected))}, got {actual}")
            resolved = registry.resolve(token_id)
            if positive and (type(resolved) not in (int, float) or resolved <= 0):
                raise TokenError("invalid_token_value", token_id, "Fixed dimension must resolve to a positive number")
        except TokenError as exc:
            issues.append({"code": exc.code, "path": pointer(path), "token": exc.token, "message": str(exc)})

    def visit(node: dict, path: tuple):
        enforce_literal = node["type"] not in ("ComponentInstance", "IconInstance")
        layout = node.get("layout", {})
        for axis in ("width", "height"):
            dimension = layout.get(axis, {})
            if dimension.get("mode") == "fixed":
                check(dimension.get("value"), {"size", "spacing", "radius"}, (*path, "layout", axis, "value"), positive=True)
        check(layout.get("gap"), {"spacing"}, (*path, "layout", "gap"), enforce_literal=enforce_literal)
        for edge, value in layout.get("padding", {}).items():
            check(value, {"spacing"}, (*path, "layout", "padding", edge), enforce_literal=enforce_literal)
        style = node.get("style", {})
        for field, category in (("fill", "color"), ("radius", "radius"), ("typographyToken", "typography"), ("colorToken", "color"), ("spacingToken", "spacing"), ("shadowToken", "shadow")):
            check(style.get(field), {category}, (*path, "style", field), enforce_literal=enforce_literal)
        stroke = style.get("stroke", {})
        if "token" in stroke:
            check(stroke, {"border"}, (*path, "style", "stroke"))
        else:
            check(stroke.get("color"), {"color"}, (*path, "style", "stroke", "color"), enforce_literal=enforce_literal)
            check(stroke.get("width"), {"spacing"}, (*path, "style", "stroke", "width"), enforce_literal=enforce_literal)
        for index, child in enumerate(node.get("children", [])):
            visit(child, (*path, "children", index))
        for slot, children in node.get("slots", {}).items():
            for index, child in enumerate(children):
                visit(child, (*path, "slots", slot, index))

    for index, page in enumerate(document["pages"]):
        visit(page, ("pages", index))
    return sorted(issues, key=lambda item: (item["path"], item["code"], item["message"]))
