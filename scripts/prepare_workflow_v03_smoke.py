"""Prepare a new source-bound prototype using only admitted fixed components."""
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.prototype.parser import parse
from core.layout.builder import generate
from validators.structure.gate import builder, check
from validators.ui_ir import load_json

SOURCE = ROOT / "examples/user-management-compact-search-v027-figma"
TARGET = ROOT / "examples/workflow-v03-smoke-figma"
DRAFT = ROOT / "artifacts/task-122/semantic-draft"
SECTIONS = ("用户管理｜组件流程验证页",
            "页头左侧是", "查询区分两行：", "列表区先显示", "这是一张只展示")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def draft():
    text = (TARGET / "prototype.txt").read_text(encoding="utf-8")
    paragraphs = [paragraph for paragraph in text.strip().split("\n\n") if paragraph]
    if len(paragraphs) != len(SECTIONS) or any(not paragraph.startswith(prefix)
                                              for paragraph, prefix in zip(paragraphs, SECTIONS)):
        raise ValueError("Prototype paragraphs changed; rebuild evidence deliberately")
    for item in SOURCE.iterdir():
        if item.is_file() and item.name not in ("prototype.txt", "review.json", "input-manifest.json"):
            dest = TARGET / item.name
            if not dest.exists():
                shutil.copyfile(item, dest)
    observations = load_json(TARGET / "observations.json")
    observations["documentId"] = "workflow-v03-user-management-smoke"
    observations["sources"][0]["sha256"] = digest(TARGET / "prototype.txt")
    for row, paragraph in zip(observations["evidence"], paragraphs):
        start = text.index(paragraph)
        row.update(quote=paragraph, start=start, end=start + len(paragraph))
    save(TARGET / "observations.json", observations)
    analysis = parse(observations, TARGET)
    tree = builder.build(analysis)
    save(DRAFT / "prototype_analysis.json", analysis)
    save(DRAFT / "page_tree.json", tree)
    return {"status": "AWAITING_SEMANTIC_REVIEW", "documentId": observations["documentId"],
            "analysisSha256": builder.fingerprint(analysis),
            "pageTreeSha256": builder.fingerprint(tree),
            "sourceSha256": digest(TARGET / "prototype.txt")}


def finalize(review):
    observations = load_json(TARGET / "observations.json")
    analysis = parse(observations, TARGET)
    tree = builder.build(analysis)
    if check(analysis, tree, TARGET, review)["status"] != "PASS":
        raise ValueError("Semantic review does not approve this exact new prototype")
    layout_plan = load_json(TARGET / "layout-plan.json")
    layout_plan["pageTreeSha256"] = builder.fingerprint(tree)
    save(TARGET / "layout-plan.json", layout_plan)
    resolver = import_module("core.component-resolver.resolver")
    tokens = resolver.tokens.TokenRegistry(load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
    components = resolver.registry_module.ComponentRegistry(
        load_json(ROOT / "registries/components/v0.2.7/catalog.json"),
        load_json(ROOT / "registries/components/v0.2.7/fidelity-reports.json"))
    layout_tree, report = generate(analysis, tree, TARGET, review, layout_plan, tokens)
    if report["status"] != "PASS":
        raise ValueError("New layout failed: " + str(report.get("issues")))
    decisions = load_json(TARGET / "decisions.json")
    decisions["layoutTreeSha256"] = builder.fingerprint(layout_tree)
    save(TARGET / "decisions.json", decisions)
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, tree, TARGET, review, layout_plan, decisions, components, tokens,
        allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError("New component mapping failed: " + str(mapping["issues"]))
    content = load_json(TARGET / "content.json")
    content["mappingSha256"] = builder.fingerprint(mapping)
    save(TARGET / "content.json", content)
    save(TARGET / "review.json", review)
    files = sorted(path.name for path in TARGET.iterdir()
                   if path.is_file() and path.name != "input-manifest.json")
    save(TARGET / "input-manifest.json", {"kind": "workflow-v03-independent-smoke",
         "status": "READY_FOR_PREFLIGHT", "sourcePackage": TARGET.relative_to(ROOT).as_posix(),
         "policy": "new-prototype/same-admitted-component-configurations",
         "files": {name: digest(TARGET / name) for name in files}})
    return {"status": "PASS", "itemCount": len(mapping["rows"]),
            "contentMappingSha256": content["mappingSha256"]}


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "draft":
        print(json.dumps(draft(), ensure_ascii=False))
    elif len(sys.argv) == 3 and sys.argv[1] == "finalize":
        print(json.dumps(finalize(load_json(Path(sys.argv[2]))), ensure_ascii=False))
    else:
        raise SystemExit("Use draft or finalize <review.json>")
