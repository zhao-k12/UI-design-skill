"""Validate recorded Figma native typography evidence without implying Penpot acceptance."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = Path(__file__).with_name("figma-native-read.json")
OLD = ROOT / "adapters/figma/metadata/list-independent-readback.json"


def main() -> None:
    capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
    old = json.loads(OLD.read_text(encoding="utf-8"))
    old_text = {row["uiIrId"]: row for row in old["evidence"] if row.get("characters")}
    rows = capture["rows"]
    assert capture["status"] == "PASS"
    assert capture["platform"] == "figma"
    assert capture["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
    assert capture["pageId"] == "169:2"
    assert capture["font"] == {"family": "Inter", "style": "Regular", "weight": 400}
    assert len(rows) == len(old_text) == 12
    assert {row["uiIrId"] for row in rows} == set(old_text)
    assert len({row["nodeId"] for row in rows}) == 12
    for row in rows:
        assert row["characters"] == old_text[row["uiIrId"]]["characters"]
        assert row["width"] > 0 and row["height"] > 0
        expected_size, expected_line = (20, 28) if row["uiIrId"] == "title" else (14, 22)
        assert (row["fontSize"], row["lineHeight"]) == (expected_size, expected_line)
    count = next(row for row in rows if row["uiIrId"] == "list.count")
    assert count["width"] == 73 and old_text["list.count"]["width"] == 71
    print("TASK-050 Figma evidence PASS; Penpot and V0.2 input remain BLOCKED")


if __name__ == "__main__":
    main()
