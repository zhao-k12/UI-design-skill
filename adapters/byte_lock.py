"""Versioned, raw-byte Adapter preflight lock for new V0.2 tasks."""
from hashlib import sha256
import json
from pathlib import Path

from validators.ui_ir import ROOT


VERSION = "0.2.0"
COMMON_FILES = (
    "adapters/byte_lock.py",
    "scripts/run_pipeline.py",
    "scripts/finalize_pipeline.py",
    "scripts/prepare_adapter_execution.py",
)


def digest(data):
    return sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def source_files(platform, root=ROOT):
    if platform not in ("figma", "penpot"):
        raise ValueError("Unknown Adapter platform")
    root = Path(root)
    base = root / "adapters" / platform
    paths = [root / name for name in COMMON_FILES]
    paths.extend((root / "adapters").glob("*.py"))
    paths.extend(path for path in base.rglob("*") if path.is_file()
                 and path.suffix in (".py", ".js")
                 and "metadata" not in path.relative_to(base).parts
                 and "__pycache__" not in path.relative_to(base).parts)
    return sorted(set(paths))


def script_for_page(platform, plan, index, page_reference=None):
    if platform == "figma":
        from adapters.figma.compiler import script_for_page as compile_script
    elif platform == "penpot":
        from adapters.penpot.compiler import script_for_page as compile_script
    else:
        raise ValueError("Unknown Adapter platform")
    return compile_script(plan, index, page_reference=page_reference)


def build(plans, root=ROOT):
    if set(plans) != {"figma", "penpot"}:
        raise ValueError("Both Adapter plans are required")
    root = Path(root).resolve()
    platforms = {}
    for platform in ("figma", "penpot"):
        plan = plans[platform]
        if not isinstance(plan, dict) or not plan.get("pages") or not plan.get("fileReference"):
            raise ValueError("Complete Adapter plan required: " + platform)
        files = {}
        for path in source_files(platform, root):
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("Adapter source missing or escaped root")
            files[path.relative_to(root).as_posix()] = digest(path.read_bytes())
        platforms[platform] = {
            "adapterVersion": plan["adapterVersion"],
            "fileReference": plan["fileReference"],
            "uiIrSha256": plan["uiIrSha256"],
            "sourceFiles": files,
            "planSha256": digest(canonical(plan)),
            "createScriptSha256": [digest(script_for_page(platform, plan, index).encode("utf-8"))
                                   for index in range(len(plan["pages"]))],
        }
    if platforms["figma"]["uiIrSha256"] != platforms["penpot"]["uiIrSha256"]:
        raise ValueError("Adapter plans do not share one UI-IR")
    return {"lockSchemaVersion": VERSION, "scope": "v02-adapter-preflight-byte-lock",
            "nativeExecution": "NOT_RUN", "releaseReady": False, "platforms": platforms}


def verify(lock, plans, root=ROOT):
    if lock != build(plans, root):
        raise ValueError("Adapter byte lock changed; new task migration required")
    return True


def verify_execution_script(lock, plans, platform, script, page_index=0,
                            page_reference=None, root=ROOT):
    verify(lock, plans, root)
    if platform not in lock["platforms"]:
        raise ValueError("Unknown Adapter platform")
    expected = script_for_page(platform, plans[platform], page_index,
                               page_reference=page_reference)
    if script != expected:
        raise ValueError("Execution script differs from locked Adapter source and plan")
    return {"platform": platform, "pageIndex": page_index,
            "pageReference": page_reference, "executionScriptSha256": digest(script.encode("utf-8")),
            "planSha256": lock["platforms"][platform]["planSha256"]}
