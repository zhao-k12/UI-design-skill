"""TASK-001: static Python/JSON Core boundary checks; not a design QA gate."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

PLATFORM_MODULES = frozenset({"figma", "penpot", "figma_api", "penpot_api", "figma_sdk", "penpot_sdk"})
PLATFORM_FIELDS = frozenset({"figmaNodeId", "penpotShapeId", "figma_node_id", "penpot_shape_id"})
SOURCE_SUFFIXES = frozenset({".py", ".json"})


def forbidden_module(name: str) -> bool:
    parts = set(name.replace("-", "_").split("."))
    return bool(parts & (PLATFORM_MODULES | {"adapters"}))


def json_platform_fields(value: object) -> set[str]:
    if isinstance(value, dict):
        found = set(value) & PLATFORM_FIELDS
        for child in value.values():
            found.update(json_platform_fields(child))
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found.update(json_platform_fields(child))
        return found
    return set()


def check_core(root: Path) -> list[str]:
    """Reject platform imports/IDs and uninspected executable formats in Core.

    Static checks are not a security sandbox: runtime indirection requires review.
    Adapter metadata is deliberately outside this scanner's scope.
    """
    core = root / "core"
    if not core.is_dir():
        return ["missing core directory"]
    issues: list[str] = []
    for path in sorted(core.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if path.name == ".gitkeep" or path.suffix == ".md":
            continue
        if path.suffix not in SOURCE_SUFFIXES:
            issues.append(f"{relative}: unsupported Core format; extend boundary validator before use")
            continue
        try:
            source = path.read_text(encoding="utf-8-sig")
            if path.suffix == ".json":
                for field in sorted(json_platform_fields(json.loads(source))):
                    issues.append(f"{relative}: platform field {field}")
                continue
            tree = ast.parse(source, filename=relative)
            for node in ast.walk(tree):
                imports: list[str] = []
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""] + [alias.name for alias in node.names]
                elif isinstance(node, ast.Call):
                    func = node.func
                    dynamic = (isinstance(func, ast.Name) and func.id == "__import__") or (
                        isinstance(func, ast.Attribute) and func.attr == "import_module"
                    )
                    if dynamic:
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            imports = [node.args[0].value]
                        else:
                            issues.append(f"{relative}:{node.lineno}: dynamic import requires boundary review")
                for name in imports:
                    if forbidden_module(name):
                        issues.append(f"{relative}:{node.lineno}: forbidden dependency {name}")
                field = None
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    field = node.value
                elif isinstance(node, ast.Name):
                    field = node.id
                elif isinstance(node, ast.Attribute):
                    field = node.attr
                elif isinstance(node, ast.arg):
                    field = node.arg
                if field in PLATFORM_FIELDS:
                    issues.append(f"{relative}:{node.lineno}: platform field {field}")
        except (SyntaxError, ValueError, OSError) as exc:
            issues.append(f"{relative}: cannot validate: {exc}")
    return sorted(set(issues))


if __name__ == "__main__":
    findings = check_core(Path(__file__).resolve().parents[1])
    if findings:
        print("\n".join(findings))
        sys.exit(1)
    print("PASS: Core architecture boundary (Python/JSON static checks)")
