# TASK-015 — Logical assembly and content injection

The current implementation creates UI-IR ComponentInstance payloads and Section
replacement operations on the existing computed Skeleton. It does not rebuild
the page or execute a platform write. `nativeInstancesCreated` remains false.
TASK-015 native component replacement/full-slot acceptance is still pending;
the separate Penpot linked-copy text patch subtask has now passed native readback.
Do not claim the logical artifact is an editable platform design.

The assembly entry point re-runs component resolution (and upstream gates), not
trusting a saved mapping status. Missing/Review inputs produce no replacement
operations. Explicit fixture mode can generate diagnostic logical payloads from
a fully resolved contract fixture, but readyForAdapter stays false.

Content follows `schemas/component-content.schema.json`, bound to the exact
mapping hash. Every source item has exactly one entry. Each injected text must
cite the item evidence and occur literally in the original evidence quote; no
placeholder, header, label or static copy is invented. Supported properties:
Input/Select placeholder or value, Table headers, Text text. Button text uses its
declared label slot. The property vocabulary is intentionally static and small,
not runtime business logic. Labels on field wrappers require an admitted wrapper
with a label slot; an Input cannot silently acquire undeclared FormItem slots.

Six slot roles are recognized: leading-icon/trailing-icon accept official logical
icons; label accepts source text; control/actions accept registered instances;
content accepts source text or registered instances. Every used slot must also
be declared by the selected component descriptor. Nested instances are checked
through the registry and the UI-IR validator, with maximum slot depth 12. Icon
source resolution uses the existing official registry; actual platform icon
admission remains the adapter's responsibility. Missing registry/icons report
missing_icon; no glyph or temporary icon is drawn.

Replacement operations preserve the original Cell ID, source, box and fixed
width/height envelope. With `--component-ir`, each instance instead receives its
exact admitted source width/height and a separate `instanceBox` at the Cell origin;
the Cell box stays unchanged. The source bundle is schema-validated, bound to the
registry fingerprint, and each component digest must equal its fidelity admission.
Overflow, missing geometry and nested instances without explicit slot envelopes
block operations. Changing the geometry bundle requires a new baseline. Without
this bundle, legacy diagnostic payloads remain available but `readyForAdapter`
and `sourcePlacementVerified` are false. They carry native-neutral instance payloads, not private platform
IDs or calls. With a previous PASS checkpoint for the same page/Skeleton and
registry baseline, the program compares per-Section payloads and emits only
changed Sections. Unchanged Section arrays remain byte-equivalent under canonical
JSON. No changes emit no operations. Modified checkpoints, changed layout or
registry migrations reject reuse. This hash integrity check is not a signature.

```powershell
.venv/Scripts/python.exe -m core.component-resolver.assembly examples/component-assembly-contract/prototype_analysis.json examples/component-assembly-contract/page_tree.json examples/component-assembly-contract/layout-plan.json examples/component-assembly-contract/decisions.json examples/component-assembly-contract/content.json --source-root examples/prototype-semantic --review examples/component-assembly-contract/synthetic-review.json --output artifacts/task-015/assembly.json --allow-test-fixtures
```

The command exits 1 for a diagnostic fixture even when logical QA passes. It
always writes the current report, so no prior successful operations survive a
blocked current run. `--previous` adds a local checkpoint, never authorization
for platform writes. Formal native replacement must first pass upstream gates,
then the adapter must apply operations against an existing page and independently
read back real instances/content/positions before completing TASK-015.

Explicit `cellSlots` add role frames around the primary mapped node inside the
existing Cell. The primary control/actions/content role is retained automatically;
companions cannot replace it. Children require fixed measured sizes, current
registries, source text and known style tokens. Icon SVG bytes and viewBox must
match the registered source. `cellDirection` (horizontal/vertical) requires
`cellSlots`; overflow rejects the whole operation. These layout frames remain
separate from an admitted widget's internal declared slots.

`materialize` validates the current source-sized assembly and exact Layout Tree
before producing UI-IR. Static Text is opt-in with `--allow-text-primitives`, high
source confidence and explicit typography/color tokens; it creates no registry
component and cannot replace a missing interactive widget. Native proof scope and
unsupported cases are recorded in `.dev/TASK-015_ACCEPTANCE.md`.
