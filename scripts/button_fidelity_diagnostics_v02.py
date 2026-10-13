"""Measure native Button edge and text differences without granting admission."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "artifacts/task-023/replay-final/first"
NATIVE = {"figma": ROOT / "artifacts/task-027/figma/component-native.png",
          "penpot": ROOT / "artifacts/task-028/penpot/component-native.png"}
BLUE = (45, 140, 240)
WHITE = (255, 255, 255)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def palette_residual(rgb):
    # Rounded-edge antialiasing must be a blend of the locked blue and white.
    amount = (WHITE[0] - rgb[0]) / (WHITE[0] - BLUE[0])
    expected = tuple(WHITE[channel] * (1 - amount) + BLUE[channel] * amount for channel in range(3))
    return max(abs(rgb[channel] - expected[channel]) for channel in range(3))


def inspect(native, source, span):
    if native.size != source.size:
        raise ValueError("native_size_changed")
    white = Image.new("RGBA", native.size, (*WHITE, 255))
    white.alpha_composite(native.convert("RGBA"))
    native = white.convert("RGB")
    source = source.convert("RGB")
    x0, y0 = int(span["x"] - 2), int(span["y"] - 2)
    x1, y1 = int(span["x"] + span["width"] + 2), int(span["y"] + span["height"] + 2)
    result = {"textZone": {"different": 0, "brightInkPixelsByHalf": [0, 0], "inkBoundsByHalf": []},
              "cornerEdge": {"different": 0, "maxPaletteResidual": 0, "maxChannelDelta": 0,
                             "outOfPalettePixels": 0},
              "nonTextInterior": {"different": 0}}
    ink = [[], []]
    midpoint = native.width // 2
    for y in range(native.height):
        for x in range(native.width):
            a, b = source.getpixel((x, y)), native.getpixel((x, y))
            if x0 <= x < x1 and y0 <= y < y1:
                half = 0 if x < midpoint else 1
                # The glyph is white over locked blue. Count sufficiently bright antialias pixels.
                if b[0] >= 180 and b[1] >= 200 and b[2] >= 240:
                    result["textZone"]["brightInkPixelsByHalf"][half] += 1
                    ink[half].append((x, y))
                if a != b:
                    result["textZone"]["different"] += 1
            elif x < 5 or x >= native.width-5 or y < 5 or y >= native.height-5:
                if a != b:
                    edge = result["cornerEdge"]
                    edge["different"] += 1
                    residual = max(palette_residual(a), palette_residual(b))
                    edge["maxPaletteResidual"] = max(edge["maxPaletteResidual"], round(residual, 3))
                    edge["maxChannelDelta"] = max(edge["maxChannelDelta"],
                                                  max(abs(a[k] - b[k]) for k in range(3)))
                    edge["outOfPalettePixels"] += residual > 2
            elif a != b:
                result["nonTextInterior"]["different"] += 1
    for pixels in ink:
        result["textZone"]["inkBoundsByHalf"].append(
            {"x": min(x for x, _ in pixels), "y": min(y for _, y in pixels),
             "width": max(x for x, _ in pixels) - min(x for x, _ in pixels) + 1,
             "height": max(y for _, y in pixels) - min(y for _, y in pixels) + 1} if pixels else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status":"FAIL","nativeAdmission":"NOT_RUN"}\n', encoding="utf-8")
    source_ir = json.loads((SOURCE_ROOT / "component_ir.json").read_bytes())
    button = next(item for item in source_ir["components"] if item["componentType"] == "Button")
    span = next(node for node in button["nodes"] if node["path"] == "0.0")["bounds"]
    source_path = SOURCE_ROOT / "action.button.primary.medium.png"
    if sha(source_path) != button["screenshot"]["sha256"]:
        raise ValueError("source_screenshot_changed")
    source = Image.open(source_path).convert("RGBA")
    for platform, native_path in NATIVE.items():
        candidate = json.loads((ROOT / f"adapters/{platform}/metadata/button-default-font-candidate-0.2.0.json").read_bytes())
        if candidate["evidenceSha256"]["component-native.png"] != sha(native_path):
            raise ValueError("native_candidate_png_changed:" + platform)
    platforms = {name: inspect(Image.open(path), source, span) for name, path in NATIVE.items()}
    result = {"scope": "v02-button-native-fidelity-diagnostics", "status": "REVIEW_REQUIRED",
              "platforms": platforms, "method": "White-composite pixel partition plus blue/white edge palette check",
              "effectiveCjkFontIdentity": "UNVERIFIED", "nativeAdmission": "NOT_RUN", "releaseReady": False}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "platforms": platforms,
                      "nativeAdmission": "NOT_RUN"}))


if __name__ == "__main__":
    main()
