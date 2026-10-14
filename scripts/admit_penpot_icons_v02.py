"""Write a separate binding for the replacement Penpot file after native master gate PASS."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.penpot.icon_admission_v02 import BASE, FILE, REPORT, MASTER_IDS, build_gate, sha


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    gate = build_gate()
    old = json.loads((ROOT / "adapters/penpot/metadata/icon-bindings.json").read_text(encoding="utf-8"))
    bindings = {icon_id: {**old["bindings"][icon_id],
                           "fileReference": FILE,
                           "componentReference": MASTER_IDS[icon_id][0],
                           "fidelityReportPath": REPORT.relative_to(ROOT).as_posix()}
                for icon_id in MASTER_IDS}
    result = {**old, "bindings": bindings}
    return gate, result


def main():
    gate, binding = build()
    write(REPORT, gate)
    for item in binding["bindings"].values():
        item["fidelityReportSha256"] = sha(REPORT)
    target = ROOT / "adapters/penpot/metadata/icon-bindings-0.2.0.json"
    write(target, binding)
    print(json.dumps({"status": gate["status"], "fileReference": FILE, "components": list(MASTER_IDS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
