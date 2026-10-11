# Native text outline geometry

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.outline_geometry adapters/figma/metadata/native-text-outline-capture.json --output artifacts/task-009/outline-geometry/report.json
```

The bounded reader inspects existing native SVG exports without creating or
replacing Figma nodes. It accepts absolute M/L/H/V/C/Z paths, computes cubic
Bezier extrema analytically and unions actual path extents. It rejects relative
or unsupported commands, transforms, strokes, scripts, declarations, nonfinite
coordinates and oversized input instead of approximating them. Each exported
SVG is hashed. Curve extrema are mathematical bounds of the exported SVG path,
with normal floating-point arithmetic; no visual tolerance is introduced.

PASS means the supported exported path data was inspected. It does not prove
original font-curve identity, SVG export precision, correct platform coordinate
transforms, browser DOM baseline or cross-platform glyph equivalence. The
existing Fidelity Gate and Registry admission rules remain unchanged.

## Font-file dimension comparison

Install the optional pinned diagnostic dependency with
`.venv/Scripts/python.exe -m pip install -r requirements-diagnostics.txt`.
It leaves npm package and official source locks unchanged.

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.font_outline_comparison --capture adapters/figma/metadata/native-text-outline-capture.json --font-identity adapters/figma/metadata/font-file-identity.json --output artifacts/task-009/font-file-outline-comparison/report.json
```

The diagnostic verifies exact font-file hashes, resolves cmap glyphs and reads
actual bounds through fontTools BoundsPen, with explicit hmtx advances. Only the
current CJK/private Ionicons sample range is supported; variable fonts, missing
glyphs, unsupported text and invalid sizes are rejected. It records fontTools
version and font units. Bounds are scaled with decimal arithmetic, without a
visual tolerance or baseline adjustment.

The actual four native exports have exactly matching width/height with these
unshaped font-file glyph bounds. The report remains REVIEW: equality of aggregate
dimensions does not establish full contours, shaping, DOM baseline, browser font
cache identity or TTF/WOFF2 equivalence. See the primary
[fontTools glyph interface documentation](https://fonttools.readthedocs.io/en/stable/ttLib/ttFont.html).

## Complete ordered and unoriented path comparison

The same diagnostic now reads decomposed actual glyph drawing commands and
parses the captured SVG commands. It retains an ordered comparison, then separately
compares complete closed contour geometry after translation, cyclic start,
contour order and traversal-direction normalization. Cubic reversal reverses
control points as well as endpoints. Only an explicit line back to the start or
a zero-length line is removed; curve coordinates are not rounded or sampled.
Minimal cyclic starts use a linear-time rotation algorithm to avoid quadratic
allocation on long contours. Comparison normalization never moves canvas nodes.

All three Chinese samples have exactly matching normalized contour coordinates
and structure. The Ionicons contour structure matches, but its SVG coordinates
have a maximum difference of 0.000028125px from the TTF glyph. That difference
is retained; no export-rounding exception or tolerance is applied. Ordered
traversal differs, and fill winding, shaping, browser-loaded file identity,
baseline and pixel fidelity remain independently unverified. Overall status is
still REVIEW, with no Registry admission.
