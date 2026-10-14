"""Validate two native typography readbacks and their platform-neutral envelope."""

from copy import deepcopy
import json
from pathlib import Path

from build_text_envelope import FIGMA, PENPOT, OUTPUT, _sha, build


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "adapters/figma/metadata/list-independent-readback.json"


def main() -> None:
    capture = json.loads(FIGMA.read_text(encoding="utf-8"))
    penpot = json.loads(PENPOT.read_text(encoding="utf-8"))
    envelope = json.loads(OUTPUT.read_text(encoding="utf-8"))
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
    assert envelope == build(capture, penpot, _sha(FIGMA), _sha(PENPOT))
    penpot_count = next(row for row in penpot["rows"] if row["uiIrId"] == "list.count")
    assert penpot_count["width"] == 69
    envelope_count = next(row for row in envelope["rows"] if row["uiIrId"] == "list.count")
    assert envelope_count["width"] == 73
    mismatched = deepcopy(penpot)
    mismatched["rows"][0]["characters"] = "wrong"
    try:
        build(capture, mismatched, _sha(FIGMA), _sha(PENPOT))
    except ValueError as exc:
        assert "Text mismatch" in str(exc)
    else:
        raise AssertionError("Mismatched platform text was accepted")
    print("TASK-050 two-platform text envelope PASS; composed cells and V0.2 input remain pending")


if __name__ == "__main__":
    main()
