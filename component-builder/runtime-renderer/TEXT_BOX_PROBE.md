# Actual browser text layout evidence

```powershell
node component-builder/runtime-renderer/text-box-probe.mjs --output artifacts/task-009/text-box-probe-complete --reference artifacts/task-006
```

The probe observes the locked official runtime without modifying the DOM or CSS.
It uses CDP DOMSnapshot.captureSnapshot for post-layout text rectangles and the
separate deprecated DOMSnapshot.getSnapshot with includeUserAgentShadowTree for
the input placeholder omitted by the former API. It preserves both raw snapshots
and reports measured document/component rectangles, UTF-16 slices and ancestry.
All reconstructed screenshots and environments must match the original reference
for diagnostic PASS; no reference files are overwritten.

The [official CDP DOMSnapshot reference](https://chromedevtools.github.io/devtools-protocol/tot/DOMSnapshot/)
defines these as post-layout text boxes; they are not glyph ink outlines. The
observed backend identities are supplemental browser evidence and never enter
Core/Component IR or represent native Figma measurements. Missing placeholder
or pseudo text is never reconstructed from CSS, canvas metrics or guessed bounds.
This diagnostic grants no component admission and does not relax pixel fidelity.
