# TASK-015 — native content patch (partial capability)

Native execution and independent readback now pass for an in-place text update on
a genuine linked Button copy in an existing Section. The original page, copy ID,
component link, size, position and all unrelated nodes remain intact. This does
not yet complete TASK-015 component replacement/complex-slot assembly.

Compiler content plans use explicit `0.1.1-content`; content-free plans keep the
existing `0.1.0` path. New content execution lives in content_runtime.js. The
hash-bound TASK-010 runtime and host remain unchanged and their full gate was
recomputed PASS after this development. Historical TASK-015 execution code is
retained in the acceptance folder as served-plugin.js, not reconstructed later.

Supported native mappings are derived from admitted master readback, requiring a
unique declared name and exact font/style evidence: Button one plain Text label;
Input placeholder; Select value (static displayed caption). The admitted Select
is a selected state, so an empty placeholder is unsupported. Input value is also
unsupported because the admitted source is an empty placeholder state. Table
headers, nested control/actions and icon-slot insertion are not yet mapped; they
remain explicit compiler failures. Native text getters alone do not prove every
glyph is visible: independent PNG and bound visual review remain required.

The helper checks linked-copy identity, source text/style and finite-sized
placement, changes only characters, checks copy geometry/link and text containment,
and restores the original text when validation fails. It never detaches, edits a
master, stretches a verified component or creates a temporary one. The Section
patch checks file/page/root ownership, exact ledger/source hashes, current revision,
all requested copies and text checkpoints before mutation. Unrelated-node changes
or topology changes fail. Explicit top-level Frame region declarations support
the legacy admitted page; arbitrary nested Frames do not become Sections.

The independent QA compares execution snapshots with separate before/after
captures, current source content bindings and genuine copy/link/geometry/font
identity. Native PNG must be complete and changes outside the exact copy rectangle
are rejected. A later capture revision can advance as Penpot persists the change,
but the full captured node snapshot must still exactly match the execution result.
Manual visual review is bound to the original PNG hash. No export failure or
unreviewed capture can produce a native PASS.

```powershell
.venv/Scripts/python.exe -m adapters.penpot.host.section_server --target-file 91396aad-60c8-808b-8008-c0885ca79899 --output-dir artifacts/task-015/new-native-host --port 57831 --candidate-readback adapters/penpot/metadata/section-content-acceptance/execution.json
```

Reuse the already installed project plugin at its loopback endpoint, retaining
the same permissions. The new host is separate from the immutable TASK-010 host.
The validation fixture derives from its admitted UI-IR, creates one independent
page, captures a baseline, changes only query-button text to the existing source
literal 导出, and independently captures after. It is an adapter contract test,
not approval of a new user prototype or a bypass of Core fixture/semantic gates.
Reusing the ledger prevents duplicate pages. The whole UI-IR is compiled, but the
patch never calls the whole-page creation executor.

Remaining work: genuine native component-type replacement, declared mappings for
remaining slots/table content, source-sized placement from Core Cell allocations,
the corresponding other-platform path and complete TASK-015 acceptance. Current
Core diagnostic artifacts remain ineligible for platform execution.
