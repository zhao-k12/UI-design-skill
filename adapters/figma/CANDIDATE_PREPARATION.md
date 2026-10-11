# Official candidate input preparation

Run from the project root:

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.candidate_preflight --reference artifacts/task-006 --font-evidence adapters/figma/metadata/official-runtime-font-evidence.json --discovery adapters/figma/metadata/official-font-discovery.json --file-reference 0vGWSRoLxBiVPXiZ8xJAX9 --output-dir artifacts/task-009/official-candidate-preflight
```

Optional `--logical-id action.button.primary.medium` restricts preparation to one component. Repeat it for multiple components. Optional `--bindings` accepts explicit source-family to native font-name mappings; it must use the same family and an actually discovered style. This does not load fonts.

The tool verifies the extracted reference artifacts, font evidence's raw Component IR hash, component inventory, environment and source provenance, and the target Figma file. It filters observed font requirements to the selected components. Invalid source evidence is FAIL; missing source fonts or unresolved styles are REVIEW. In both cases preparation is null. Output stays in separate project artifacts and replaces previous report status before reading input files.

The general preparation CLI emits no executable generation script, native component, capture measurement, registry entry or fidelity PASS. Its preparation contains reference identity and screenshot hashes only. Independent native geometry and PNG capture remain required.

`button_candidate.prepare_button` now connects this preflight to the scoped static Button builder. It only emits a host script after source/font preflight PASS. Supported source: primary/default Button, one visible text span, uniform solid border/radius, pixel lengths, RGB paints, normal font style, no visible pseudo content or icons. Unsupported source shapes fail explicitly. The script creates editable Text in horizontal Auto Layout and converts that frame to a COMPONENT. Fixed reference dimensions, padding, border and typography are translated directly from official observations; no project visual tokens are substituted.

Native font discovery/loading, file/page checks and duplicate detection precede canvas writes. A failed font-weight check returns the exact partial created-node ledger without cleanup. Successful creation returns raw properties read from the created component/text, with admissionEligible=false and fidelityGate=NOT_RUN. These observations are not yet a complete Fidelity Gate capture: native raster export, font metrics/glyph measurements, CSS-to-native comparison and independent capture provenance remain pending. The generic preparation record retains nativeBuilder=NOT_IMPLEMENTED until the Button entry point selects its implemented builder.

The actual Button entry point currently returns REVIEW for PingFang SC with script=null. No official UI component has been written to the approved Figma file. Plugin API model tests intentionally return changed native dimensions to verify that output measurements are read from the host rather than copied from source.

The actual full-source run currently returns REVIEW for PingFang SC and Ionicons. The project Noto Sans SC font bindings cannot substitute for these source fonts. Font availability in the remote Figma Host is distinct from local Windows installation.

## Scoped static Input and Select

`form_candidate.prepare_form` now connects the same verified source/font gate to native Input and Select scripts. Input currently supports the empty default text input and its captured placeholder; it uses the placeholder's source color and preserves CSS normal line height as native AUTO, pending actual font metrics validation. Select currently supports the closed default single-select with one matching selected option. It preserves the built-in arrow's captured pseudo glyph and actual source font binding. Arrow DOM bounds already include the source translation, so the script uses that absolute overlay position once; it does not draw an arrow or replace it with a Remix icon.

Visible dropdowns, unknown nodes/states, selected-value mismatch, unresolved font roles, extra pseudo content, nonuniform borders, unsupported transforms, decorative text, geometry mismatch and arrow overflow are rejected. Hidden DOM paths are recorded as excluded from this default static candidate. Native outputs contain actual component/field/text properties and an exact created-node ledger; they remain unadmitted and are not complete Fidelity Capture data.

The common script-preparation CLI is:

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.candidates --reference artifacts/task-006 --font-evidence adapters/figma/metadata/official-runtime-font-evidence.json --discovery adapters/figma/metadata/official-font-discovery.json --file-reference 0vGWSRoLxBiVPXiZ8xJAX9 --page-reference 0:1 --output-dir artifacts/task-009/static-candidates
```

Use `--logical-id` and `--bindings` as above. All requested candidates must pass preparation before scripts are emitted. The CLI never executes Figma. It verifies ownership hashes before invalidating previous generated scripts, preserves modified/unowned files, and stores candidate_build_report.json plus candidate_scripts.json. The actual three-component run currently reports REVIEW for all three and emits no scripts. No native UI components were created.

## Native PNG and evidence capture

The generated Button/Input/Select scripts now call `finishCandidateCapture` after successful creation. The capture helper loads actual text font segments, reads the native tree and properties, and exports PNG at scale 1 with absolute bounds. It reuses the selected page so the combined script never switches pages twice. Capture failure keeps the builder's created-node ledger and returns FAIL. Font-blocked builders never reach export.

Standalone `captureNativeComponent` also supports read-only export of an explicitly identified existing main component. Its result includes nativeEvidence, raster bytes, identity and scope; it creates and mutates no nodes. Mixed properties remain explicitly nativeMixed, and no per-glyph metrics or CSS observation values are inferred.

Import the standalone capture result or the complete successful combined builder result. The importer also binds combined results to the component in their creation ledger:

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.native_capture artifacts/task-009/native-export-smoke/tool-result.json --file-reference 0vGWSRoLxBiVPXiZ8xJAX9 --component-reference 3:4 --logical-id remix.search-line --output-dir artifacts/task-009/native-export-smoke/validated
```

Choose a new output directory for each import. The importer checks scope, identity, read-only success, native tree/bounds, PNG bytes/size and memory limits before publishing an immutable manifest. It preserves the original native PNG and separately alpha-composites it onto white, without resizing/cropping. `verify_saved_capture` verifies all recorded file hashes and reproduces normalization. Test fixtures cannot be imported as production. Metadata and hashes do not authenticate a platform call by themselves.

The actual search-icon main component 3:4 was read and exported successfully in the approved file: two native nodes, 402-byte PNG, 24×24, no created/mutated nodes. Its immutable snapshot and passing integrity report are in metadata/native-export-smoke. This validates transport for an existing native icon. It does not establish Button/Input/Select fidelity: complete CSS-to-native comparison, glyph metrics and actual source-font support remain pending; admissionEligible stays false and fidelityGate stays NOT_RUN.

## Native comparison diagnostics

`candidate_diagnostic` verifies official reference artifacts and the associated font evidence, then verifies each immutable native snapshot. Store each captured candidate at `<candidate-directory>/<logical-id>/`. File/logical identity, production scope, inventory and role/parent relationships are checked before comparison. The diagnostic reads source CSS directly, independently from the generators, and checks known dimensions, solid paints, borders, padding, radius, text, actual source font family/optional approved binding, pixel line height, and Select arrow bounds/glyph/positioning.

Only exact double/float32 representations of source RGB channels are accepted as storage encodings; this is not a color tolerance. PNG comparison records exact changed-pixel counts without rescaling or anti-aliasing relaxation. Mismatches are FAIL; missing/mixed properties and missing native candidates remain REVIEW. Even all known properties and pixels passing still yields REVIEW: full glyph metrics, CSS-normalized visible-node observations and CSS normal line-height equivalence remain unverified. This diagnostic never emits a production Fidelity Gate PASS or changes the existing gate/admission policy.

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma.candidate_diagnostic --reference artifacts/task-006 --font-evidence adapters/figma/metadata/official-runtime-font-evidence.json --file-reference 0vGWSRoLxBiVPXiZ8xJAX9 --candidates artifacts/task-009/captured-candidates --output-dir artifacts/task-009/native-comparison
```

The actual current run reports missing independent native Button/Input/Select candidates. The existing icon transport snapshot cannot stand in for these UI components. Diagnostic contract tests explicitly use test-fixture snapshots; production comparison rejects fixture scope.

Contract tests explicitly mock artifact verification with fixtures. The actual run uses the real TASK-006 artifacts; it is evidence validation, not a native component acceptance test.

## Exact source fonts and account upload preparation

The bounded source-reader font metadata tool identifies exact Regular styles for
the local PingFang SC OTF and official release Ionicons TTF. See
`component-builder/source-reader/FONT_IDENTITY.md`. `font_load_probe.js` checks
both actual font listing and awaited `loadFontAsync`, without changing nodes.
The actual approved-file probe lists 8927 entries but neither exact font; both
load calls fail because their families do not exist in this remote Host. The
raw evidence is in metadata/source-font-load-probe.json. Suggested substitute
families are not selected.

[Figma's official guide](https://help.figma.com/hc/en-us/articles/360039956894-Add-a-font-to-Figma)
provides account font uploads for MCP and Figma agent. The authenticated account
the authorized target account has Settings > Account > Your uploaded fonts with no uploaded
fonts. metadata/font-upload-preparation.json records the two exact paths/hashes
and pending authorization. No font bytes have been uploaded or installed.

Before uploading, obtain the user's confirmation of upload rights and Figma
storage/use authorization. Recheck the exact file hashes immediately before
upload. After upload, repeat actual Host discovery and load checks before
preparing explicit bindings or executing native candidates. Upload success alone
does not establish font equivalence, glyph metrics, fidelity or admission. Keep
the locked browser reference and final gate unchanged.

## Actual post-upload acceptance

The user uploaded both Regular fonts. Actual approved-file discovery now reports
8929 entries and exact matching styles; both awaited font loads succeed. Preserve
the earlier missing-font evidence and use the separate after-upload discovery,
probe and official-source-font-bindings metadata for new preparation.

Actual Button, Input and Select candidates were built and captured on Page 0:1
as components 12:4, 12:8 and 12:15. Their creation ledger is in
metadata/official-native-candidate-execution.json; immutable captures and the
independent comparison report are in metadata/official-native-candidates.
All covered property checks pass, but exact PNG comparison finds respectively
336, 675 and 311 changed pixels. The visual comparison sheet was inspected.
No cause is inferred from pixel location, no raster tolerance was relaxed and
no candidate was admitted. Full glyph metrics and normalized observations
remain pending; TASK-009 is still incomplete.

Raster diagnostics now retain exact difference bounds, maximum RGBA-channel
delta, counts at delta <=16 and pixel-center containment in actual reference
text-run rectangles. Overlapping rectangles are counted once for the union.
Missing text bounds are recorded as unresolved; placeholder/pseudo text is
never assigned guessed rectangles. Region membership does not establish glyph
shape, antialiasing, nontext outside the rectangles, or an acceptable tolerance.
The new location fields do not change the FAIL/REVIEW or admission policy.

Use `--text-box-evidence` to attach a saved actual browser text-box probe to the
comparison. It verifies the original IR hash, reproduced screenshot inventory,
environment, and source provenance before using any supplemental rectangles.
Renderer hashes may differ for an observer run; other source fields must match.
Unknown logical identities/surfaces and invalid geometry are rejected. Original
reference text regions remain separate from supplemental shadow/pseudo regions.
Neither changes source IR, native captures or exact raster failure decisions.

The text-box probe also saves actual computed font synthesis, kerning, feature
and variation settings, text-rendering, and smoothing values per element/pseudo.
Empty browser values remain empty; support/effect and a Figma equivalent are
not inferred. These observations diagnose the source environment and do not
authorize visual adjustments to reproduce raster differences.

With supplemental text evidence, `surfacePartition` provides disjoint counts
for observed text, source-derived uniform-radius corner rectangles, and remaining
unclassified changes. It validates supported source radius expressions and
counts exact RGBA differences at pixel centers. Text has priority where regions
overlap; no pixel is counted twice. Corner rectangles identify location only,
not a curve mask or proof of a rasterizer cause. The actual three candidates have
zero unclassified changed pixels; all differences lie in observed text or the
four 4px corner regions. Exact comparisons still FAIL and no tolerance changes.

`text_outline.js` reads explicitly identified existing Text nodes on one page,
loads their actual styled font segments and exports SVG_STRING with
svgOutlineText=true and useAbsoluteBounds=true. It records actual render bounds,
layout bounds and font properties; it creates no nodes and never flattens live
text. Cross-file/page selections and invalid exports fail explicitly. Mixed
properties remain nativeMixed. Native SVG evidence is stored for diagnosis,
not inserted as replacement UI assets or used to grant fidelity admission.

The browser text-box probe additionally records unattached Canvas measureText
samples for visible source elements, placeholders and pseudo content. Requested
and accepted canvas font strings remain explicit. These separate measurements
do not establish the DOM baseline or actual font-file identity, and are not
silently equated with Figma render bounds or SVG contours. Locked source
screenshots are still reproduced before diagnostic PASS.

## Measured Button baseline revision

`baseline_revision.js` performs a scoped revision of an explicitly identified
existing Button candidate. The request retains hashes of source baseline/font
evidence, source span bounds and the calibrated native font-outline baseline.
The script verifies current identity, inventory, font/geometry and unscaled
transforms before writing, loads current font segments, then introduces an
editable transparent source/0.0 span container. Its bounds preserve the official
span, and the existing editable Text receives the measured offset inside it.
Partial failure returns all created/mutated IDs; retry cannot duplicate a span.

Actual revision: created span 16:2 inside component 12:4 and moved Text 12:3 into
it with y=-1. Span geometry remains (16,5.5,28,21), calibrated baseline becomes
20.5, and the independent PNG capture succeeds. Exact changed pixels fall from
336 to 317; comparison still FAIL. The revised capture is separately immutable
in metadata/button-baseline-revised-capture, with request and execution ledgers.
The independent diagnostic checks the source span mapping and keeps full glyph
baseline/fidelity evidence separate. Old snapshots and formal Registry are intact.
