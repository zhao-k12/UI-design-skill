# TASK-015 progress — 2026-10-08

Logical implementation and one native content-patch subtask are completed. Native
component replacement/full-slot acceptance remains pending. TASK-015 is IN_PROGRESS,
not PASS, and TASK-016 has not started.

Implemented source-bound content contract, current mapping revalidation, exact
item coverage, static properties, six declared slot roles, nested registered
instances, official icon references, UI-IR payload validation, preserved existing
Cell IDs/boxes and Section-local replacement operations/checkpoint checks.

Actual saved contract execution: examples/component-assembly-contract/assembly.json
contains seven logical instances, with no native execution. Changing the toolbar
button text to the existing source substring 新增 generates only toolbar operations
in updated-assembly.json; filter/result Sections and original positions stay the
same. This example deliberately removes static items from its synthetic contract
to test registered-only assembly; it is not the full user prototype or approval.

The full earlier example still has missing Text entries and unresolved semantic
questions. Recomputed upstream gates continue to block production assembly. No
registry resource, native design or source evidence was changed to make it pass.

Tests cover valid instance payloads, button label/placeholder/table headers,
changed mapping affecting only filters, changed content affecting only toolbar,
unchanged checkpoint producing no operations, altered checkpoint, absent review,
stale content, invented text, unsupported property/slot and complete item coverage.
All six roles are tested with explicitly synthetic component descriptors plus
the real official icon registry; missing icons block operations. Synthetic slot
descriptors never enter the production catalog or a platform.

Remaining acceptance: execute a valid production Section replacement against an
existing native design, read back genuine component instances and populated
content, compare unchanged Sections/positions, and confirm no full-page rebuild.
The Core artifact itself does not execute native operations. The Penpot native
content executor is now independently implemented and accepted for linked Button
text updates; see TASK-015_NATIVE_CONTENT_ACCEPTANCE.md. It is not a component-type
replacement executor. Source-sized placement, remaining native slots/table headers
and the corresponding other-platform path are still required.

2026-10-08 source placement increment: Core now consumes caller-supplied Component
IR without adapter imports. Schema validation and per-component admission hashes
bind source dimensions; a 240x32 Input is placed inside a 336x32 Cell without
stretching. Existing Cell box and origin remain intact. Insufficient space,
unavailable variants, duplicate/tampered IR and nonfinite envelopes are rejected.
Assembly optionally accepts this geometry via --component-ir and binds it to the
checkpoint. Without geometry, diagnostic results cannot become adapter-ready.
Nested slots require explicit envelopes and remain blocked on this path. This is
not full layout-to-native acceptance or native type replacement acceptance.

Validation: 338 Python tests passed (109.285s); subsequently added incomplete-geometry assembly regression passed with all 4 placement tests. Existing 6 assembly tests passed. Core architecture and whitespace checks passed. Native evidence source files were not modified.

2026-10-08 component swap increment: a separate Penpot public-SDK executor now
preflights an independent full-root snapshot, revision, owned linked-copy target,
declared Section, expected old reference and exact source dimensions before one
component swap. It checks root identity/world geometry, new linkage, unchanged
source master and unrelated nodes, and reports changed descendant IDs explicitly.
Post-mutation failures return PARTIAL with a recovery ledger, never fictitious
rollback. Content overrides and dimension changes remain unsupported. Six API
double tests cover success and negative guards; native execution/readback/PNG
acceptance remains NOT_RUN. Frozen Task010 and native-content proof files remain
unchanged. See adapters/penpot/SECTION_SWAP.md.

Validation: full Node suite 98/98 passed (13.996s), followed by the two added source-master/SDK-interruption checks in the 6/6 swap suite; focused Python assembly/placement suite 10/10 passed. Architecture and whitespace checks passed. Native swap acceptance remains NOT_RUN.
