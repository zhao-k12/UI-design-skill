# TASK-013 acceptance — 2026-10-08

Implemented frozen Page Tree → standard Layout Pattern → deterministic engine
and layout QA. Source, semantic review and structure are rechecked before layout.
AI-supplied region assignments are explicit; the program applies project rules
without free coordinates, component selection or invented content.

Saved two kinds of actual execution evidence:

- `examples/prototype-semantic/layout/`: the existing unresolved prototype remains
  Review, layout_tree.json is null, and downstream mapping remains closed.
- `examples/layout-builder-contract/`: explicitly synthetic review/measurements
  produce a complete layout and PASS geometry QA. All 9 semantic items and four
  Sections retain source references. There is no pagination source, so no empty
  pagination Section is emitted. TestFixture true and readyForMapping false prevent
  this fixture becoming a production resource. The review is not human approval.

Tests exercise all five standard pattern families, deterministic output, unchanged
inputs, item provenance, field span 6, absent-region removal, fresh structure gate,
default rejection of fixture measurements, stale tree/token hashes, missing or
ambiguous mappings, nonfinite measurements, free-coordinate rejection and wide
button overflow. Existing engine tests cover invalid spans, padding, minimum
field width, wrapping, overflow, alignment and nesting.

Current constraints: one Section per selected pattern region; runtime measurement
reference accuracy still requires external evidence. Multiple-section regions or
other patterns return explicit failure rather than substitution. TASK-014 is not
implemented here. Full test result is recorded in DEVELOPMENT_STATE.md.
