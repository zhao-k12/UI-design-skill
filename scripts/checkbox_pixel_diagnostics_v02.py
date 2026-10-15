"""Measure native Checkbox candidates against the locked browser screenshot."""
from PIL import Image

from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-058/checkbox-source/form.checkbox.default.enabled.png"


def on_white(path):
    with Image.open(path) as image:
        image = image.convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    white.alpha_composite(image)
    return white.convert("RGB")


def compare(reference, candidate):
    original, native = on_white(reference), on_white(candidate)
    if original.size != native.size:
        return {"sizeMismatch": [original.size, native.size]}
    rows = []
    for y in range(21):
        changed = []
        largest = 0
        for x in range(16):
            a, b = original.getpixel((x, y)), native.getpixel((x, y))
            delta = max(abs(u - v) for u, v in zip(a, b))
            if delta:
                changed.append(x)
                largest = max(largest, delta)
        if changed:
            rows.append({"y": y, "changed": changed, "maximumChannelDelta": largest})
    def mark(image):
        return {(x, y) for y in range(5, 15) for x in range(3, 14)
                if min(image.getpixel((x, y))) >= 220}
    source_mark, native_mark = mark(original), mark(native)
    return {"boxChangedPixels": sum(len(row["changed"]) for row in rows), "boxRows": rows,
            "tickMask": {"source": len(source_mark), "native": len(native_mark),
                         "intersection": len(source_mark & native_mark),
                         "union": len(source_mark | native_mark),
                         "iou": round(len(source_mark & native_mark) / len(source_mark | native_mark), 4)}}


if __name__ == "__main__":
    import json
    for platform, task in (("figma", 59), ("penpot", 60)):
        candidate = ROOT / f"artifacts/task-{task:03d}/{platform}/component-native.png"
        print(json.dumps({"platform": platform, **compare(SOURCE, candidate)}))
    for platform in ("figma", "penpot"):
        candidate = ROOT / f"artifacts/task-061/{platform}/native.png"
        print(json.dumps({"platform": platform, "revision": 2, **compare(SOURCE, candidate)}))
    for name, path in (("source", SOURCE),
                       ("figma", ROOT / "artifacts/task-059/figma/component-native.png"),
                       ("penpot", ROOT / "artifacts/task-060/penpot/component-native.png"),
                       ("figma-r2", ROOT / "artifacts/task-061/figma/native.png"),
                       ("penpot-r2", ROOT / "artifacts/task-061/penpot/native.png")):
        image = on_white(path)
        print(name, {y: image.getpixel((8, y)) for y in (2, 3, 17, 18)})
        for y in range(21):
            line = ""
            for x in range(16):
                r, g, b = image.getpixel((x, y))
                line += "W" if min(r, g, b) >= 220 else ("+" if min(r, g, b) >= 150 else ("B" if b > r + 80 else "#"))
            print(line)
