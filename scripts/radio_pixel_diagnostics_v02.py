"""Measure native Radio candidates against the locked browser screenshot."""
import json

from scripts.checkbox_pixel_diagnostics_v02 import on_white
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-063/radio-source/form.radio.default.enabled.png"


def compare(reference, candidate):
    original, native = on_white(reference), on_white(candidate)
    if original.size == (48, 22) and native.size == (48, 21):
        original = original.crop((0, 1, 48, 22))
    if original.size != native.size:
        return {"sizeMismatch": [original.size, native.size]}
    rows = []
    for y in range(21):
        changed = []
        maximum = 0
        for x in range(16):
            a, b = original.getpixel((x, y)), native.getpixel((x, y))
            delta = max(abs(u - v) for u, v in zip(a, b))
            if delta:
                changed.append(x)
                maximum = max(maximum, delta)
        if changed:
            rows.append({"y": y, "changed": changed, "maximumChannelDelta": maximum})
    return {"controlChangedPixels": sum(len(row["changed"]) for row in rows), "rows": rows}


if __name__ == "__main__":
    for name, path in (("figma", ROOT / "artifacts/task-064/figma/native.png"),
                       ("penpot", ROOT / "artifacts/task-064/penpot/native.png")):
        print(json.dumps({"platform": name, **compare(SOURCE, path)}))
    for name, path in (("source", SOURCE),
                       ("figma", ROOT / "artifacts/task-064/figma/native.png"),
                       ("penpot", ROOT / "artifacts/task-064/penpot/native.png")):
        image = on_white(path)
        print(name)
        for y in range(21):
            line = ""
            for x in range(16):
                r, g, b = image.getpixel((x, y))
                line += "B" if b > r + 80 else ("+" if b > r + 20 else "W")
            print(line)
