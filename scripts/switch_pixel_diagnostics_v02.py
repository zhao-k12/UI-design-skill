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
    blue_core = [(x, y) for y in range(8, 14) for x in list(range(3, 7)) + list(range(21, 24))]
    knob_core = [(x, y) for y in range(8, 15) for x in range(30, 37)]
    exact_blue = all(original.getpixel(p) == native.getpixel(p) == (45, 140, 240) for p in blue_core)
    exact_knob = all(original.getpixel(p) == native.getpixel(p) == (255, 255, 255) for p in knob_core)
    def blue_mask(image):
        return {(x, y) for y in range(22) for x in range(44) if not 7 <= x <= 20
                and image.getpixel((x, y))[2] - image.getpixel((x, y))[0] >= 80}
    blue_source, blue_native = blue_mask(original), blue_mask(native)
    iou = len(blue_source & blue_native) / len(blue_source | blue_native)
    def text_ink(image):
        return {(x, y) for y in range(1, 21) for x in range(8, 20)
                if image.getpixel((x, y))[0] >= 180}
    source_ink, native_ink = text_ink(original), text_ink(native)
    large = [d for d in diffs if d["delta"] > 40]
    source_edge_only = all(tuple(d["source"]) not in ((45, 140, 240), (255, 255, 255)) for d in large)
    return {"sourceBottomBlankRow": bottom_blank, "outsideTextDifferent": len(diffs),
            "outsideTextMaximumChannelDelta": max((d["delta"] for d in diffs), default=0),
            "exactBlueCore": exact_blue, "exactWhiteKnobCore": exact_knob,
            "blueMaskIntersectionOverUnion": round(iou, 4),
            "sourceTextInkPixels": len(source_ink), "nativeTextInkPixels": len(native_ink),
            "textOuterEdgeInk": sorted([list(p) for p in native_ink if p[0] in (8, 19) or p[1] in (1, 20)]),
            "largeDifferencesOnSourceAntialias": source_edge_only,
            "largeDifferences": large}


if __name__ == "__main__":
    for name in ("figma", "penpot"):
        path = ROOT / f"artifacts/task-068/{name}/native.png"
        print(json.dumps({"platform": name, **compare(SOURCE, path)}, ensure_ascii=False))
