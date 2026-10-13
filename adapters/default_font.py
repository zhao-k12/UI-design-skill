"""Resolve V0.2 semantic page typography against an observed target-file default."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = {"figma": "0.2.0", "penpot": "0.2.1"}


def binding_for(typography, supplied, *, platform, file_reference):
    family = typography["fontFamily"]
    weight = typography["fontWeight"]
    key = f"{family}:{weight}"
    if family != "platform-default":
        return supplied.get(key)
    if (not isinstance(supplied, dict) or supplied.get("kind") != "platform-default-font-binding"
            or supplied.get("version") != "0.2.0" or supplied.get("platform") != platform
            or supplied.get("fileReference") != file_reference or platform not in TARGET):
        return None
    path = ROOT / f"adapters/{platform}/metadata/default-font-target-{TARGET[platform]}.json"
    if supplied.get("targetMetadataSha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        return None
    target = json.loads(path.read_text(encoding="utf-8"))
    if target.get("fileReference") != file_reference:
        return None
    binding = supplied.get("bindings", {}).get(key)
    if not isinstance(binding, dict):
        return None
    observed = target.get("defaultFont", {})
    if weight == 400:
        if platform == "figma":
            expected = {"family": observed.get("family"), "style": observed.get("style")}
        else:
            expected = {"fontId": observed.get("fontId"), "fontVariantId": observed.get("fontVariantId"),
                        "family": observed.get("family"), "weight": observed.get("weight"),
                        "style": observed.get("style")}
        return binding if binding == expected else None
    return None
