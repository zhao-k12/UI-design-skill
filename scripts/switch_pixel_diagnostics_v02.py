"""Compare locked browser Switch pixels with native default-font candidates."""
import json

from scripts.checkbox_pixel_diagnostics_v02 import on_white
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-067/switch-source/form.switch.default.enabled.png"


def compare(reference, candidate):
    original, native = on_white(reference), on_white(candidate)
    if original.size != (44, 23) or native.size != (44, 22):
        return {"sizeMismatch": [original.size, native.size]}
    bottom_blank = all(original.getpixel((x, 22)) == (255, 255, 255) for x in range(44))
    original = original.crop((0, 0, 44, 22))
    diffs = []
    for y in range(22):
        for x in range(44):
            if 7 <= x <= 20:
                continue
            source_pixel, native_pixel = original.getpixel((x, y)), native.getpixel((x, y))
            delta = max(abs(a - b) for a, b in zip(source_pixel, native_pixel))
            if delta:
                diffs.append({"x": x, "y": y, "delta": delta,
                              "source": source_pixel, "native": native_pixel})
    return {"sourceBottomBlankRow": bottom_blank, "outsideTextDifferent": len(diffs),
            "outsideTextMaximumChannelDelta": max((d["delta"] for d in diffs), default=0),
            "largeDifferences": [d for d in diffs if d["delta"] > 40]}


if __name__ == "__main__":
    for name in ("figma", "penpot"):
        path = ROOT / f"artifacts/task-068/{name}/native.png"
        print(json.dumps({"platform": name, **compare(SOURCE, path)}, ensure_ascii=False))
