# Actual DOM baseline instrumentation

```powershell
node component-builder/runtime-renderer/baseline-probe.mjs --output artifacts/task-009/dom-baseline-probe-complete --reference artifacts/task-006
```

The probe temporarily appends an empty zero-size inline-block marker to the
actual supported Button/Select text container. Its baseline is the bottom margin
edge under the [CSS inline-block baseline rule](https://www.w3.org/TR/CSS22/visudet.html#propdef-vertical-align).
The marker uses zero border, padding and margin. The probe checks component,
container and text-range geometry before and during instrumentation, removes the
marker in finally, and verifies exact markup/geometry restoration. Only then are
the original official components extracted and compared with locked screenshots.
This is temporary DOM instrumentation, not a read-only snapshot operation.

Unknown text structures fail. The probe now resolves the actual user-agent
placeholder DOM owner through CDP and instruments the actual Select arrow owner
containing its before pseudo glyph. It compares every rendered inline text box
before/during/after and checks original owner markup/bounds after removal. Source
characters are read from the actual owner or computed pseudo content. These
measurements cover the locked default fixtures; canvas/font metrics do not replace
their direct baseline measurement.
Diagnostic PASS requires screenshot and environment reproduction and never grants
component admission or alters existing reference files.

`adapters.figma.baseline_alignment.compare_baseline_alignment` compares this
source evidence against freshly exported native outlines and actual identity
linear transforms. It derives the font baseline offset from the SVG/source font
ink extent translation, checks text content and ink dimensions, and reports
position separately from contour/pixel fidelity. All four current native text
roles are aligned after the Button revision; the report remains REVIEW because
exact pixels and other independent evidence still require validation.
